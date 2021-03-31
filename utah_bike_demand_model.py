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
def preprocess_network(net):
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

    light = (10e3 < aadt) & (aadt < 20e3)
    med = (20e3 <= aadt) & (aadt < 30e3)
    heavy = 30e3 <= aadt

    small_slope = (2.0 < slope) & (slope < 4.0)
    med_slope = (4.0 <= slope) & (slope < 6.0)
    big_slope = 6.0 < slope

    turn = net.get_edge_values("turn", dtype="bool")
    signal = net.get_edge_values("traffic_signal", dtype="bool")
    turn_type = net.get_edge_values("turn_type", dtype="str")
    parallel_aadt = net.get_edge_values("parallel_aadt", dtype="float")
    cross_aadt = net.get_edge_values("cross_aadt", dtype="float")

    left = turn_type == "left"
    left_or_straight = (turn_type == "left") | (turn_type == "straight")
    right = turn_type == "right"

    light_cross = (5e3 < cross_aadt) & (cross_aadt < 10e3)
    med_cross = (10e3 <= cross_aadt) & (cross_aadt < 20e3)
    heavy_cross = 20e3 <= cross_aadt

    med_parallel = (10e3 < parallel_aadt) & (parallel_aadt < 20e3)
    heavy_parallel = 20e3 <= parallel_aadt

    # distance coefficients
    bike_commute = distance * (
        1.0
        + (bike_blvd * -0.108)
        + (bike_path * -0.16)
        + (small_slope * 0.371)
        + (med_slope * 1.23)
        + (big_slope * 3.239)
        + (bike_lane * med * 0.25)
        + (bike_lane * heavy * 1.65)
        + (~bike_lane * light * 0.368)
        + (~bike_lane * med * 1.4)
        + (~bike_lane * heavy * 7.157)
    )

    bike_non_commute = distance * (
        1.0
        + (bike_blvd * -0.179)
        + (bike_path * -0.26)
        + (small_slope * 0.723)
        + (med_slope * 2.904)
        + (big_slope * 11.066)
        + (bike_lane * med * 0.5)
        + (bike_lane * heavy * 3.3)
        + (~bike_lane * light * 0.7)
        + (~bike_lane * med * 2.0)
        + (~bike_lane * heavy * 10.0)
    )

    # fixed-cost penalties
    bike_commute += (
        (turn * 0.034)
        + (signal * 0.017)
        + (left_or_straight * light_cross * 0.048)
        + (left_or_straight * med_cross * 0.05)
        + (left_or_straight * heavy_cross * 0.26)
        + (right * heavy_cross * 0.031)
        + (left * med_parallel * 0.073)
        + (left * heavy_parallel * 0.18)
    )

    bike_non_commute += (
        (turn * 0.074)
        + (signal * 0.033)
        + (left_or_straight * light_cross * 0.072)
        + (left_or_straight * med_cross * 0.1)
        + (left_or_straight * heavy_cross * 0.55)
        + (right * heavy_cross * 0.06)
        + (left * med_parallel * 0.15)
        + (left * heavy_parallel * 0.4)
    )

    net.set_edge_values("bike_commute", bike_commute)
    net.set_edge_values("bike_non_commute", bike_non_commute)


if __name__ == "__main__":
    main()
