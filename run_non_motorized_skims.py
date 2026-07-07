"""Run bike and walk skim generation only.

This script writes both skim outputs to Model_Outputs/NonMotorizedSkims by
default. Bike and walk are run in separate Python processes so their local
network preprocessors do not conflict with each other.
"""

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("Model_Outputs") / "NonMotorizedSkims"


class PrefixScenarioMixin:
    """Map standard micromobility config names to mode-prefixed files."""

    config_prefix = ""

    def config_file_path(self, filename):
        if filename in ["network.yaml", "trips.yaml", "zone.yaml"]:
            filename = f"{self.config_prefix}_{filename}"

        return super().config_file_path(filename)


def main():
    parser = argparse.ArgumentParser(
        description="Run bike and/or walk skim generation without demand steps."
    )
    parser.add_argument(
        "--mode",
        choices=["all", "bike", "walk"],
        default="all",
        help="Which skim model to run. Default: all.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for skim files. Default: Model_Outputs/NonMotorizedSkims.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "all":
        script_path = Path(__file__).resolve()
        for mode in ["bike", "walk"]:
            subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--mode",
                    mode,
                    "--output",
                    str(output_dir),
                ],
                check=True,
            )
        return

    if args.mode == "bike":
        run_bike_skims(output_dir)
    else:
        run_walk_skims(output_dir)


def run_bike_skims(output_dir):
    from micromobility_toolset import model, network

    from Model_Additional_Scripts import bike_model_helper  # noqa: F401
    from Model_Additional_Scripts.bike_model_helper import cleanup_bike_skims

    class BikeSkimsScenario(PrefixScenarioMixin, model.Scenario):
        config_prefix = "bike"

    network.PREPROCESSORS.clear()
    network.PREPROCESSORS.append(preprocess_bike_network)

    model.config_logger()
    scenario = BikeSkimsScenario(
        name="Utah Bike Skims Scenario",
        config="Model_Configs",
        inputs="Model_Inputs",
        outputs=str(output_dir),
    )
    model.run(["skim_network", "add_bike_path_skim_attributes"], scenario)
    cleanup_bike_skims(output_dir)


def run_walk_skims(output_dir):
    from micromobility_toolset import model, network

    from Model_Additional_Scripts import walk_model_helper  # noqa: F401
    from Model_Additional_Scripts.walk_model_helper import cleanup_walk_skims

    class WalkSkimsScenario(PrefixScenarioMixin, model.Scenario):
        config_prefix = "walk"

    network.PREPROCESSORS.clear()
    network.PREPROCESSORS.append(preprocess_walk_network)

    model.config_logger()
    scenario = WalkSkimsScenario(
        name="Utah Walk Skims Scenario",
        config="Model_Configs",
        inputs="Model_Inputs",
        outputs=str(output_dir),
    )
    model.run(["skim_network", "add_walk_path_skim_attributes"], scenario)
    cleanup_walk_skims(output_dir)


def preprocess_bike_network(net, settings):
    """Add bike_commute and bike_non_commute network edge costs."""

    distance = net.get_edge_values("distance", dtype="float")
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
    light_cross = (aadt_cross["light"] < cross_aadt) & (
        cross_aadt < aadt_cross["medium"]
    )
    med_cross = (aadt_cross["medium"] <= cross_aadt) & (
        cross_aadt < aadt_cross["heavy"]
    )
    heavy_cross = aadt_cross["heavy"] <= cross_aadt

    aadt_parallel = settings.get("aadt_parallel")
    med_parallel = (aadt_parallel["medium"] <= parallel_aadt) & (
        parallel_aadt < aadt_parallel["heavy"]
    )
    heavy_parallel = aadt_parallel["heavy"] <= parallel_aadt

    network_coef = settings.get("network_coef")
    bike_commute = distance * (
        1.0
        + (bike_blvd * network_coef.get("bike_commute")["bike_blvd"])
        + (bike_path * network_coef.get("bike_commute")["bike_path"])
        + (small_slope * network_coef.get("bike_commute")["small_slope"])
        + (med_slope * network_coef.get("bike_commute")["med_slope"])
        + (big_slope * network_coef.get("bike_commute")["big_slope"])
        + (bike_lane * med * network_coef.get("bike_commute")["bike_lane_medium_aadt"])
        + (bike_lane * heavy * network_coef.get("bike_commute")["bike_lane_heavy_aadt"])
        + (~bike_lane * light * network_coef.get("bike_commute")["light_aadt"])
        + (~bike_lane * med * network_coef.get("bike_commute")["medium_aadt"])
        + (~bike_lane * heavy * network_coef.get("bike_commute")["heavy_aadt"])
    )

    bike_non_commute = distance * (
        1.0
        + (bike_blvd * network_coef.get("bike_non_commute")["bike_blvd"])
        + (bike_path * network_coef.get("bike_non_commute")["bike_path"])
        + (small_slope * network_coef.get("bike_non_commute")["small_slope"])
        + (med_slope * network_coef.get("bike_non_commute")["med_slope"])
        + (big_slope * network_coef.get("bike_non_commute")["big_slope"])
        + (
            bike_lane
            * med
            * network_coef.get("bike_non_commute")["bike_lane_medium_aadt"]
        )
        + (
            bike_lane
            * heavy
            * network_coef.get("bike_non_commute")["bike_lane_heavy_aadt"]
        )
        + (~bike_lane * light * network_coef.get("bike_non_commute")["light_aadt"])
        + (~bike_lane * med * network_coef.get("bike_non_commute")["medium_aadt"])
        + (~bike_lane * heavy * network_coef.get("bike_non_commute")["heavy_aadt"])
    )

    fixed_costs = settings.get("fixed_costs")
    bike_commute += (
        (turn * fixed_costs.get("bike_commute")["turn"])
        + (signal * fixed_costs.get("bike_commute")["signal"])
        + (
            left_or_straight
            * light_cross
            * fixed_costs.get("bike_commute")["left_or_straight_light_cross"]
        )
        + (
            left_or_straight
            * med_cross
            * fixed_costs.get("bike_commute")["left_or_straight_med_cross"]
        )
        + (
            left_or_straight
            * heavy_cross
            * fixed_costs.get("bike_commute")["left_or_straight_heavy_cross"]
        )
        + (right * heavy_cross * fixed_costs.get("bike_commute")["right_heavy_cross"])
        + (left * med_parallel * fixed_costs.get("bike_commute")["left_med_parallel"])
        + (
            left
            * heavy_parallel
            * fixed_costs.get("bike_commute")["left_heavy_parallel"]
        )
    )

    bike_non_commute += (
        (turn * fixed_costs.get("bike_non_commute")["turn"])
        + (signal * fixed_costs.get("bike_non_commute")["signal"])
        + (
            left_or_straight
            * light_cross
            * fixed_costs.get("bike_non_commute")["left_or_straight_light_cross"]
        )
        + (
            left_or_straight
            * med_cross
            * fixed_costs.get("bike_non_commute")["left_or_straight_med_cross"]
        )
        + (
            left_or_straight
            * heavy_cross
            * fixed_costs.get("bike_non_commute")["left_or_straight_heavy_cross"]
        )
        + (
            right
            * heavy_cross
            * fixed_costs.get("bike_non_commute")["right_heavy_cross"]
        )
        + (
            left
            * med_parallel
            * fixed_costs.get("bike_non_commute")["left_med_parallel"]
        )
        + (
            left
            * heavy_parallel
            * fixed_costs.get("bike_non_commute")["left_heavy_parallel"]
        )
    )

    net.set_edge_values("bike_commute", bike_commute)
    net.set_edge_values("bike_non_commute", bike_non_commute)


def preprocess_walk_network(net, settings):
    """Add walk_cost network edge cost."""

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
    light_cross = (aadt_cross["light"] < cross_aadt) & (
        cross_aadt < aadt_cross["medium"]
    )
    med_cross = (aadt_cross["medium"] <= cross_aadt) & (
        cross_aadt < aadt_cross["heavy"]
    )
    heavy_cross = aadt_cross["heavy"] <= cross_aadt

    aadt_parallel = settings.get("aadt_parallel")
    med_parallel = (aadt_parallel["medium"] <= parallel_aadt) & (
        parallel_aadt < aadt_parallel["heavy"]
    )
    heavy_parallel = aadt_parallel["heavy"] <= parallel_aadt

    coef = settings.get("network_coef").get("walk_cost")
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

    cost = settings.get("fixed_costs").get("walk_cost")
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
