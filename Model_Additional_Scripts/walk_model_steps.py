"""Walk-specific model steps.

These are local walk-mode copies of the demand generation and assignment steps
from micromobility_toolset. Keeping them in this repo lets the walk model use
walk-specific config keys and output names without editing the installed package.
"""

import os

import numpy as np
import pandas as pd

from micromobility_toolset.model import step


WALK_PATH_SKIM_OUTPUTS = {
    "walk_cost": {
        "distance": "walk_cost_distance",
        "walk_time": "walk_cost_time",
    },
}


@step()
def add_walk_path_skim_attributes(*scenarios):
    """Append path-consistent distance and time columns to walk_skims.parquet."""

    for scenario in scenarios:
        skim_file = scenario.network_settings.get("skim_file")
        skim_path = scenario.data_file_path(skim_file)

        if not os.path.exists(skim_path):
            scenario.logger.info(f"{skim_file} not found; creating base skims first...")
            scenario.skims

        scenario.logger.info(f"reading {skim_file} to append walk path attributes...")
        skim_df = pd.read_parquet(skim_path)
        _ensure_skim_index(skim_df, scenario)

        missing_outputs = [
            output_col
            for outputs in WALK_PATH_SKIM_OUTPUTS.values()
            for output_col in outputs.values()
            if output_col not in skim_df.columns
        ]

        if not missing_outputs:
            scenario.logger.info(f"{skim_file} already contains walk path attributes")
            continue

        for cost_attr, output_cols in WALK_PATH_SKIM_OUTPUTS.items():
            needed = {
                attr: col
                for attr, col in output_cols.items()
                if col not in skim_df.columns
            }

            if not needed:
                continue

            scenario.logger.info(
                f"calculating path attributes along shortest {cost_attr} paths..."
            )
            results = _skim_path_attributes(scenario, skim_df, cost_attr, needed)

            for attr, output_col in needed.items():
                skim_df[output_col] = results[attr]

        scenario.logger.info(f"saving appended skims to {skim_path}...")
        skim_df.to_parquet(skim_path)
        scenario.logger.info("done.")


def _ensure_skim_index(skim_df, scenario):
    ozone_col = scenario.network_settings.get("skim_ozone_col")
    dzone_col = scenario.network_settings.get("skim_dzone_col")

    if isinstance(skim_df.index, pd.MultiIndex):
        skim_df.index.names = [ozone_col, dzone_col]
        return

    if ozone_col not in skim_df.columns or dzone_col not in skim_df.columns:
        raise KeyError(
            f"expected skim index or columns named {ozone_col!r} and {dzone_col!r}"
        )

    skim_df.set_index([ozone_col, dzone_col], inplace=True)


def _skim_path_attributes(scenario, skim_df, cost_attr, output_cols):
    if cost_attr not in skim_df.columns:
        raise KeyError(f"expected {cost_attr!r} in skims")

    net = scenario.network
    graph = net._graph

    cost_values = net.get_edge_values(cost_attr, dtype=np.float32)
    net.set_edge_values(cost_attr, np.nan_to_num(cost_values))

    edge_values = {
        attr: net.get_edge_values(attr, dtype=np.float32)
        for attr in output_cols
    }
    results = {
        attr: np.zeros(len(skim_df), dtype=np.float32)
        for attr in output_cols
    }

    zone_positions = {int(zone): idx for idx, zone in enumerate(scenario.zone_list)}
    graph_nodes = _graph_node_indices(scenario)

    cost = skim_df[cost_attr].to_numpy()
    row_idxs = np.flatnonzero(cost != 0)
    if len(row_idxs) == 0:
        return results

    orig_vals = skim_df.index.get_level_values(0).to_numpy()[row_idxs]
    dest_vals = skim_df.index.get_level_values(1).to_numpy()[row_idxs]
    boundaries = np.concatenate(
        (
            np.array([0]),
            np.flatnonzero(orig_vals[1:] != orig_vals[:-1]) + 1,
            np.array([len(row_idxs)]),
        )
    )

    for start, end in zip(boundaries[:-1], boundaries[1:]):
        orig_zone = int(orig_vals[start])
        orig_pos = zone_positions[orig_zone]
        orig_node = graph_nodes[orig_pos]

        row_slice = row_idxs[start:end]
        dest_positions = np.array(
            [zone_positions[int(zone)] for zone in dest_vals[start:end]],
            dtype=np.int64,
        )
        dest_nodes = graph_nodes[dest_positions]

        paths = graph.get_shortest_paths(
            v=orig_node,
            to=dest_nodes,
            weights=cost_attr,
            output="epath",
        )

        for offset, path in enumerate(paths):
            if not path:
                continue

            edge_idxs = np.asarray(path, dtype=np.int64)
            row_idx = row_slice[offset]

            for attr, values in edge_values.items():
                results[attr][row_idx] = values[edge_idxs].sum()

    return results


def _graph_node_indices(scenario):
    vertex_lookup = {}
    for idx, name in enumerate(scenario.network._graph.vs["name"]):
        if not _is_missing(name):
            vertex_lookup[int(name)] = idx

    return np.array(
        [vertex_lookup[int(node)] for node in scenario.zone_nodes],
        dtype=np.int64,
    )


def _is_missing(value):
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


@step()
def generate_walk_demand(*scenarios):
    """
    Generate production-attraction walk trip tables using network skims and
    land-use data.
    """

    np.seterr(divide="ignore", invalid="ignore")

    for scenario in scenarios:

        buffer_dist = scenario.zone_settings.get("buffer_dist")
        zone_buffer = 1 / (1 + np.exp(4 * (scenario.distance_skim - buffer_dist / 2)))
        zone_buffer[scenario.distance_skim == 0] = 0
        np.fill_diagonal(zone_buffer, 1.0)

        buffered_zones = pd.DataFrame(index=scenario.zone_list)
        trip_gen_df = pd.DataFrame(index=scenario.zone_list)
        dest_size_df = pd.DataFrame(index=scenario.zone_list)

        dup_node_idxs = scenario.duplicate_nodes()
        zone_array = np.array(scenario.zone_list)
        from_zones = zone_array[dup_node_idxs[0]]
        to_zones = zone_array[dup_node_idxs[1]]
        duplicates_df = pd.DataFrame(index=[from_zones, to_zones])

        for measure in scenario.zone_settings.get("buffer_cols"):
            zone_col = scenario.zone_df[measure].values
            buffered_zones[measure] = np.sum(zone_col * zone_buffer, axis=1)

        for segment in scenario.trip_settings.get("segments"):

            orig_trips = create_walk_trips(scenario, segment, buffered_zones)
            trip_gen_df[segment] = orig_trips

            dest_size = calc_walk_dest_size(scenario, segment, dest_size_df)
            walk_trips = distribute_walk_trips(scenario, segment, orig_trips, dest_size)

            duplicates_df[segment] = walk_trips[dup_node_idxs]
            scenario.save_trip_matrix(walk_trips, segment)

        buffered_zones.round(4).to_csv(scenario.data_file_path("buffered_zones.csv"))
        trip_gen_df.round(4).to_csv(scenario.data_file_path("zone_production_size.csv"))
        dest_size_df.round(4).to_csv(
            scenario.data_file_path("zone_attraction_size.csv")
        )
        duplicates_df.round(4).to_csv(scenario.data_file_path("non_network_trips.csv"))

        scenario.logger.info(
            f"non-network walk trip count: {int(duplicates_df.sum().sum())}"
        )


def create_walk_trips(scenario, segment, buffered_zones):
    """Calculate origin walk trips for one segment."""

    sum_factor = scenario.trip_settings.get("trip_gen_sum_factor").get(segment)
    if sum_factor:

        reference_trips = scenario.load_trip_matrix(sum_factor["segment"])
        return np.sum(reference_trips, axis=sum_factor["axis"]) * sum_factor["coef"]

    zone_hh_col = scenario.zone_settings.get("zone_hh_col")
    zone_cols = scenario.trip_settings.get("trip_gen_zone_coefs")[segment].keys()
    zone_coefs = scenario.trip_settings.get("trip_gen_zone_coefs")[segment].values()
    zone_coefs = np.array(list(zone_coefs))
    zone_vals = scenario.zone_df[zone_cols].values

    buffer_cols = scenario.trip_settings.get("trip_gen_buffer_coefs")[segment].keys()
    buffer_coefs = scenario.trip_settings.get("trip_gen_buffer_coefs")[segment].values()
    buffer_coefs = np.array(list(buffer_coefs))
    buffer_vals = buffered_zones[buffer_cols].values

    orig_trips = (
        scenario.trip_settings.get("trip_gen_consts")[segment]
        + np.sum(zone_vals * zone_coefs, axis=1)
        + np.sum(buffer_vals * buffer_coefs, axis=1)
    )

    orig_trips[orig_trips < 0] = 0
    return orig_trips * scenario.zone_df[zone_hh_col].values


def calc_walk_dest_size(scenario, segment, dest_size_df):
    """Calculate destination attraction size for one segment."""

    reuse = scenario.trip_settings.get("reuse_dest_size").get(segment)
    if reuse:
        return dest_size_df[reuse].values

    dest_cols = scenario.trip_settings.get("dest_choice_zone_coefs")[segment].keys()
    dest_coefs = scenario.trip_settings.get("dest_choice_zone_coefs")[segment].values()
    dest_coefs = np.array(list(dest_coefs))
    dest_vals = scenario.zone_df[dest_cols].values

    dest_size = np.sum(dest_vals * dest_coefs, axis=1)
    dest_size[dest_size < 0] = 0

    dest_size_df[segment] = dest_size
    return dest_size


def distribute_walk_trips(scenario, segment, orig_trips, dest_size):
    """Distribute origin walk trips to destinations."""

    max_dist = scenario.trip_settings.get("trip_max_dist", {}).get(segment, np.inf)
    min_dist = scenario.trip_settings.get("trip_min_dist", {}).get(segment, 0)

    dest_avail = (scenario.distance_skim > min_dist) * (
        scenario.distance_skim < max_dist
    )

    if min_dist == 0:
        np.fill_diagonal(dest_avail, True)

    cost_attr = scenario.trip_settings.get("trip_cost_attr")[segment]
    gen_cost = (
        -scenario.skims.get_core(cost_attr).astype(np.float32)
        + np.diag(
            np.full(
                scenario.num_zones,
                scenario.trip_settings.get("walk_intrazonal")[segment],
            )
        ).astype(np.float32)
        + scenario.trip_settings.get("walk_asc")[segment]
    ).astype(np.float32)

    walk_util = (np.log(dest_size) + gen_cost).astype(np.float32)
    walk_util = np.exp(walk_util - 999 * (1 - dest_avail))

    dc_frac = np.nan_to_num(
        walk_util / np.sum(walk_util, axis=1).reshape(-1, 1)
    ).astype(np.float32)

    walk_trips = (orig_trips.reshape(-1, 1) * dc_frac).astype(np.float32)
    scenario.logger.info(f"{segment} walk trips: {int(np.sum(walk_trips))}")

    return walk_trips


@step()
def assign_walk_demand(*scenarios):
    """
    Assign zone-to-zone walk trips to the network and write walk link volumes.
    """

    for scenario in scenarios:

        cost_map = scenario.trip_settings.get("trip_cost_attr")
        cost_attrs = sorted(set(cost_map.values()))

        for cost_attr in cost_attrs:

            total_demand = np.zeros((scenario.num_zones, scenario.num_zones))

            for segment in scenario.trip_settings.get("segments"):

                if cost_attr != cost_map[segment]:
                    continue

                scenario.logger.debug(f"adding {segment} demand to {cost_attr} sums")
                walk_trips = scenario.load_trip_matrix(segment)
                scenario.logger.info(f"{segment} walk trips: {round(np.sum(walk_trips), 2)}")

                total_demand = total_demand + walk_trips

            scenario.logger.info(f"{cost_attr} walk trip sum: {int(np.sum(total_demand))}")
            scenario.logger.info(f"assigning {cost_attr} walk trips to network...")

            scenario.load_network_sums(
                attributes=total_demand,
                cost_attr=cost_attr,
                load_name=f"{cost_attr}_vol",
            )

        vol_cols = [f"{attr}_vol" for attr in cost_attrs]
        link_df = scenario.network.get_link_attributes(vol_cols + ["distance"])
        link_df["walk_vol"] = link_df[vol_cols].sum(axis=1)
        link_df = link_df[link_df.walk_vol != 0]
        walk_miles = (link_df["walk_vol"] * link_df["distance"]).sum()
        scenario.logger.info(f"walk miles traveled: {int(walk_miles)}")

        scenario.logger.info("writing results to walk_vol.csv...")
        link_df.walk_vol.to_csv(scenario.data_file_path("walk_vol.csv"))
        scenario.logger.info("done.")
