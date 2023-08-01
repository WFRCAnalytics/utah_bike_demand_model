"""Run the Utah bike model

This script runs the Utah Bike Demand models on a given set of inputs.

It instantiates a driver class called 'Scenario' that keeps track of the 'config',
'input', 'output' directories for model run. These directories
contain all the necessary instructions and data to run the model.

  - 'configs' contains settings files for each of the core elements of the
  model. These are .yaml files that provide constants and configuration
  options for the network, skims, landuse data, and trip data.

  - 'inputs' contains the initial data before any models are run. It
  contains land use data and link/node network data.

The models will generally attempt to load trip/skim data found in the 'input'
directory to perform their calculations. If the required data
cannot be found, the model will create the necessary files with the data it
is provided and save the results to the 'output' directory. These files can be moved
to the 'input' folder and reused for subsequent runs.
"""


import argparse

from micromobility_toolset import model
from micromobility_toolset.network import preprocessor


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step", "--name", dest="step", action="store", choices=model.list_steps()
    )
    parser.add_argument("--sample", dest="sample", action="store", type=int)
    args = parser.parse_args()

    model.config_logger()
    utah_scenario = model.Scenario(
        name="Utah Scenario",
        config="Model_Configs",
        inputs="Model_Inputs",
        outputs="Model_Outputs",
    )

    if args.step:
        model.run(args.step, utah_scenario)

    else:
        model.run("skim_network", utah_scenario)
        model.run("generate_demand", utah_scenario)
        model.run("assign_demand", utah_scenario)


@preprocessor()
def preprocess_network(net, settings):
    """
    Add 'bike_commute' and 'bike_non_commute' network edge costs as a combination of
    existing attributes, including turns.
    """

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
    light_cross = (aadt_cross["light"] < cross_aadt) & (cross_aadt < aadt_cross["medium"])
    med_cross = (aadt_cross["medium"] <= cross_aadt) & (cross_aadt < aadt_cross["heavy"])
    heavy_cross = aadt_cross["heavy"] <= cross_aadt

    aadt_parallel = settings.get("aadt_parallel")
    med_parallel = (aadt_parallel["medium"] <= parallel_aadt) & (parallel_aadt < aadt_parallel["heavy"])
    heavy_parallel = aadt_parallel["heavy"] <= parallel_aadt

    # distance coefficients
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
        + (bike_lane * med * network_coef.get("bike_non_commute")["bike_lane_medium_aadt"])
        + (bike_lane * heavy * network_coef.get("bike_non_commute")["bike_lane_heavy_aadt"])
        + (~bike_lane * light * network_coef.get("bike_non_commute")["light_aadt"])
        + (~bike_lane * med * network_coef.get("bike_non_commute")["medium_aadt"])
        + (~bike_lane * heavy * network_coef.get("bike_non_commute")["heavy_aadt"])
    )

    # fixed-cost penalties
    fixed_costs = settings.get("fixed_costs")
    bike_commute += (
        (turn * fixed_costs.get("bike_commute")["turn"])
        + (signal * fixed_costs.get("bike_commute")["signal"])
        + (left_or_straight * light_cross * fixed_costs.get("bike_commute")["left_or_straight_light_cross"])
        + (left_or_straight * med_cross * fixed_costs.get("bike_commute")["left_or_straight_med_cross"])
        + (left_or_straight * heavy_cross * fixed_costs.get("bike_commute")["left_or_straight_heavy_cross"])
        + (right * heavy_cross * fixed_costs.get("bike_commute")["right_heavy_cross"])
        + (left * med_parallel * fixed_costs.get("bike_commute")["left_med_parallel"])
        + (left * heavy_parallel * fixed_costs.get("bike_commute")["left_heavy_parallel"])
    )

    bike_non_commute += (
        (turn * fixed_costs.get("bike_non_commute")["turn"])
        + (signal * fixed_costs.get("bike_non_commute")["signal"])
        + (left_or_straight * light_cross * fixed_costs.get("bike_non_commute")["left_or_straight_light_cross"])
        + (left_or_straight * med_cross * fixed_costs.get("bike_non_commute")["left_or_straight_med_cross"])
        + (left_or_straight * heavy_cross * fixed_costs.get("bike_non_commute")["left_or_straight_heavy_cross"])
        + (right * heavy_cross * fixed_costs.get("bike_non_commute")["right_heavy_cross"])
        + (left * med_parallel * fixed_costs.get("bike_non_commute")["left_med_parallel"])
        + (left * heavy_parallel * fixed_costs.get("bike_non_commute")["left_heavy_parallel"])
    )

    net.set_edge_values("bike_commute", bike_commute)
    net.set_edge_values("bike_non_commute", bike_non_commute)


if __name__ == "__main__":
    main()
