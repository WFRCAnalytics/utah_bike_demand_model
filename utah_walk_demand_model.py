"""Run the Utah walk demand model.

This is a walk-oriented companion to utah_bike_demand_model.py. It points the
Scenario at walk-prefixed config files and Model_Outputs/Walk, and imports local
walk-specific demand/assignment steps.
"""

import argparse

from micromobility_toolset import model
from micromobility_toolset.network import preprocessor

from Model_Additional_Scripts import walk_model_steps  # noqa: F401  registers local walk model steps


class WalkScenario(model.Scenario):
    """Scenario wrapper that maps standard config names to walk-prefixed files."""

    CONFIG_FILES = {
        "network.yaml": "walk_network.yaml",
        "trips.yaml": "walk_trips.yaml",
        "zone.yaml": "walk_zone.yaml",
    }

    def config_file_path(self, filename):
        return super().config_file_path(self.CONFIG_FILES.get(filename, filename))


def main():

    parser = argparse.ArgumentParser()
    walk_steps = [
        "skim_network",
        "add_walk_path_skim_attributes",
        "generate_walk_demand",
        "assign_walk_demand",
    ]
    parser.add_argument(
        "--step", "--name", dest="step", action="store", choices=walk_steps
    )
    parser.add_argument("--sample", dest="sample", action="store", type=int)
    args = parser.parse_args()

    model.config_logger()
    utah_scenario = WalkScenario(
        name="Utah Walk Scenario",
        config="Model_Configs",
        inputs="Model_Inputs",
        outputs="Model_Outputs/Walk",
    )

    if args.step == "skim_network":
        model.run(["skim_network", "add_walk_path_skim_attributes"], utah_scenario)

    elif args.step:
        model.run(args.step, utah_scenario)

    else:
        model.run("skim_network", utah_scenario)
        model.run("add_walk_path_skim_attributes", utah_scenario)
        model.run("generate_walk_demand", utah_scenario)
        model.run("assign_walk_demand", utah_scenario)


@preprocessor()
def preprocess_network(net, settings):
    """
    Add a walk_cost network edge cost.
    """

    base_attr = settings.get("walk_cost_base_attr", "distance")
    base_cost = net.get_edge_values(base_attr, dtype="float")
    slope = net.get_edge_values("slope", dtype="float")
    bike_blvd = net.get_edge_values("bike_boulevard", dtype="bool")
    bike_path = net.get_edge_values("bike_path", dtype="bool")
    bike_lane = net.get_edge_values("bike_lane", dtype="bool")
    aadt = net.get_edge_values("AADT", dtype="float")

    aadt_levels = settings.get("aadt_levels")
    light = (aadt_levels["light"] < aadt) & (aadt < aadt_levels["medium"])
    med = (aadt_levels["medium"] <= aadt) & (aadt < aadt_levels["heavy"])
    heavy = aadt_levels["heavy"] <= aadt

    slope_levels = settings.get("slope_levels")
    small_slope = (slope_levels["small"] < slope) & (slope < slope_levels["medium"])
    med_slope = (slope_levels["medium"] <= slope) & (slope < slope_levels["big"])
    big_slope = slope_levels["big"] < slope

    turn = net.get_edge_values("turn", dtype="bool")
    signal = net.get_edge_values("traffic_signal", dtype="bool")
    turn_type = net.get_edge_values("turn_type", dtype="str")
    parallel_aadt = net.get_edge_values("parallel_aadt", dtype="float")
    cross_aadt = net.get_edge_values("cross_aadt", dtype="float")

    left = turn_type == "left"
    left_or_straight = (turn_type == "left") | (turn_type == "straight")
    right = turn_type == "right"

    aadt_cross = settings.get("aadt_cross")
    light_cross = (aadt_cross["light"] < cross_aadt) & (cross_aadt < aadt_cross["medium"])
    med_cross = (aadt_cross["medium"] <= cross_aadt) & (cross_aadt < aadt_cross["heavy"])
    heavy_cross = aadt_cross["heavy"] <= cross_aadt

    aadt_parallel = settings.get("aadt_parallel")
    med_parallel = (aadt_parallel["medium"] <= parallel_aadt) & (parallel_aadt < aadt_parallel["heavy"])
    heavy_parallel = aadt_parallel["heavy"] <= parallel_aadt

    network_coef = settings.get("network_coef")

    coef = network_coef.get("walk_cost")
    walk_cost = base_cost * (
        1.0
        + (bike_blvd * coef["bike_blvd"])
        + (bike_path * coef["bike_path"])
        + (small_slope * coef["small_slope"])
        + (med_slope * coef["med_slope"])
        + (big_slope * coef["big_slope"])
        + (bike_lane * med * coef["bike_lane_medium_aadt"])
        + (bike_lane * heavy * coef["bike_lane_heavy_aadt"])
        + (~bike_lane * light * coef["light_aadt"])
        + (~bike_lane * med * coef["medium_aadt"])
        + (~bike_lane * heavy * coef["heavy_aadt"])
    )

    fixed_costs = settings.get("fixed_costs")
    cost = fixed_costs.get("walk_cost")
    walk_cost += (
        (turn * cost["turn"])
        + (signal * cost["signal"])
        + (left_or_straight * light_cross * cost["left_or_straight_light_cross"])
        + (left_or_straight * med_cross * cost["left_or_straight_med_cross"])
        + (left_or_straight * heavy_cross * cost["left_or_straight_heavy_cross"])
        + (right * heavy_cross * cost["right_heavy_cross"])
        + (left * med_parallel * cost["left_med_parallel"])
        + (left * heavy_parallel * cost["left_heavy_parallel"])
    )

    net.set_edge_values("walk_cost", walk_cost)


if __name__ == "__main__":
    main()
