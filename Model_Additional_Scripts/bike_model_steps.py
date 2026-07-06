"""Bike-specific output steps.

These steps extend the local Utah bike model without editing the installed
micromobility_toolset package.
"""

import os

import numpy as np
import pandas as pd
import yaml

from micromobility_toolset.model import step


PATH_SKIM_OUTPUTS = {
    "bike_commute": {
        "distance": "bike_commute_distance",
        "bike_time": "bike_commute_time",
    },
    "bike_non_commute": {
        "distance": "bike_non_commute_distance",
        "bike_time": "bike_non_commute_time",
    },
}


@step()
def add_bike_path_skim_attributes(*scenarios):
    """Append path-consistent distance and time columns to skims.parquet."""

    for scenario in scenarios:
        skim_file = scenario.network_settings.get("skim_file")
        skim_path = scenario.data_file_path(skim_file)

        if not os.path.exists(skim_path):
            scenario.logger.info(f"{skim_file} not found; creating base skims first...")
            scenario.skims

        scenario.logger.info(f"reading {skim_file} to append bike path attributes...")
        skim_df = pd.read_parquet(skim_path)
        _ensure_skim_index(skim_df, scenario)

        missing_outputs = [
            output_col
            for outputs in PATH_SKIM_OUTPUTS.values()
            for output_col in outputs.values()
            if output_col not in skim_df.columns
        ]

        if not missing_outputs:
            scenario.logger.info(f"{skim_file} already contains bike path attributes")
            continue

        _ensure_bike_time_attribute(scenario)

        for cost_attr, output_cols in PATH_SKIM_OUTPUTS.items():
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


def _ensure_bike_time_attribute(scenario):
    settings = _read_network_settings(scenario)
    net = scenario.network

    if "bike_time" in net._graph.edge_attributes():
        return

    scenario.logger.info("adding bike_time to existing network graph from links.csv...")
    attr_map = settings["link_attributes_by_direction"]

    if "bike_time" not in attr_map:
        raise KeyError("expected 'bike_time' in link_attributes_by_direction")

    link_file = scenario.data_file_path(settings["link_file"])
    link_name = settings["link_name"]
    from_name = settings["from_name"]
    to_name = settings["to_name"]
    ab_time_col, ba_time_col = attr_map["bike_time"]

    usecols = list(
        dict.fromkeys([link_name, from_name, to_name, ab_time_col, ba_time_col])
    )
    link_df = pd.read_csv(link_file, usecols=usecols)

    by_link = link_df.set_index(link_name)[ab_time_col].to_dict()
    by_direction = {}
    for row in link_df.itertuples(index=False):
        row_data = dict(zip(link_df.columns, row))
        link_id = row_data[link_name]
        from_node = row_data[from_name]
        to_node = row_data[to_name]
        by_direction[(link_id, from_node, to_node)] = row_data[ab_time_col]
        by_direction[(link_id, to_node, from_node)] = row_data[ba_time_col]

    link_ids = _edge_attr_or_none(net, link_name)
    from_nodes = _edge_attr_or_none(net, from_name)
    to_nodes = _edge_attr_or_none(net, to_name)

    bike_time = np.zeros(net._graph.ecount(), dtype=np.float32)
    for edge_idx, link_id in enumerate(link_ids):
        if _is_missing(link_id):
            continue

        time = None
        if not _is_missing(from_nodes[edge_idx]) and not _is_missing(to_nodes[edge_idx]):
            time = by_direction.get((link_id, from_nodes[edge_idx], to_nodes[edge_idx]))

        if time is None:
            time = by_link.get(link_id, 0)

        bike_time[edge_idx] = 0 if _is_missing(time) else time

    net.set_edge_values("bike_time", bike_time)


def _read_network_settings(scenario):
    with open(scenario.config_file_path("network.yaml")) as settings_file:
        return yaml.safe_load(settings_file)


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


def _edge_attr_or_none(net, attr):
    if attr not in net._graph.edge_attributes():
        return [None] * net._graph.ecount()

    return net._graph.es[attr]


def _is_missing(value):
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except TypeError:
        return False
