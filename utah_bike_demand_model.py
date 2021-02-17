"""Run the Utah bike model

This script runs the models in the micromobility_toolset on
a 25-zone example data set.

It instantiates a driver class called 'Scenario' that keeps track of the 'config',
'data', 'output' directories for the base and build scenarios. These directories
contain all the necessary instructions and data to run the model.

  - 'configs' contains settings files for each of the core elements of the
  model. These are .yaml files that provide constants and configuration
  options for the network, skims, landuse data, and trip data.

  - 'data' contains the initial data before any models are run. It
  contains initial trip tables and land use (TAZ) data in either
  CSV or SQLITE format.
  
The `model.filter_impact_area(...)` utility will either precompute the differences in
network and zone data between two scenarios or filter the zones given a list of
zone IDs. Subsequent calculations will only
generate skims and trips for zones affected by the differences. Commenting out
this line will compute OD pairs for every zone in the input files.

The models will generally attempt to load trip/skim data found in the 'data'
directory to perform their calculations. If the required data
cannot be found, the model will create the necessary files with the data it
is provided.
"""


import argparse
import numpy as np

from micromobility_toolset import model
from micromobility_toolset.network import preprocessor


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest='name', action='store', choices=model.list_steps())
    parser.add_argument('--sample', dest='sample', action='store', type=int)
    args = parser.parse_args()

    utah_base = model.Scenario(
        name='Utah Base Scenario',
        config='Model_Configs',
        inputs='Model_Inputs',
        outputs='Model_Outputs')

    # only use first 100 microzones for testing. remove to run full dataset.
    # this method can also be used to compare two scenarios.
    if args.sample:
        model.filter_impact_area(utah_base, zone_ids=list(range(0, args.sample)))

    if args.name:
        model.run(args.name, utah_base)

    else:
        model.run('generate_demand', utah_base)
        model.run('assign_demand', utah_base)


@preprocessor()
def preprocess_network(net):
    """add network attributes that are combinations of existing attributes"""
    
    distance = np.array(net.graph.es['distance'], dtype='float')
    slope = np.array(net.graph.es['distance'], dtype='float')
    bike_blvd = np.array(net.graph.es['bike_boulevard'], dtype='bool')
    bike_path = np.array(net.graph.es['bike_path'], dtype='bool')
    bike_lane = np.array(net.graph.es['bike_lane'], dtype='bool')
    aadt = np.array(net.graph.es['AADT'], dtype='float')

    light = (10e3 < aadt) & (aadt < 20e3)
    med = (20e3 <= aadt) & (aadt < 30e3)
    heavy = 30e3 <= aadt

    small_slope = (2.0 < slope) & (slope < 4.0)
    med_slope = (4.0 <= slope) & (slope < 6.0)
    big_slope = 6.0 < slope

    turn = np.array(net.graph.es['turn'], dtype='bool')
    signal = np.array(net.graph.es['traffic_signal'], dtype='bool')
    turn_type = np.array(net.graph.es['turn_type'])
    parallel_aadt = np.array(net.graph.es['parallel_aadt'], dtype='float')
    cross_aadt = np.array(net.graph.es['cross_aadt'], dtype='float')

    left = turn_type == 'left'
    left_or_straight = (turn_type == 'left') | (turn_type == 'straight')
    right = turn_type == 'right'

    light_cross= (5e3 < cross_aadt) & (cross_aadt < 10e3)
    med_cross = (10e3 <= cross_aadt) & (cross_aadt < 20e3)
    heavy_cross = 20e3 <= cross_aadt

    med_parallel = (10e3 < parallel_aadt) & (parallel_aadt < 20e3)
    heavy_parallel = 20e3 <= parallel_aadt

    # distance coefficients
    bike_cost = \
        distance * (
            1.0 + \
            (bike_blvd * -0.108) + \
            (bike_path * -0.16) + \
            (small_slope * 0.371) + \
            (med_slope * 1.23) + \
            (big_slope * 3.239) + \
            (bike_lane * med * 0.25) + \
            (bike_lane * heavy * 1.65) + \
            (~bike_lane * light * 0.368) + \
            (~bike_lane * med * 1.4) + \
            (~bike_lane * heavy * 7.157))

    # fixed-cost penalties
    bike_cost += \
        (turn * 0.034) + \
        (signal * 0.017) + \
        (left_or_straight * light_cross * 0.048) + \
        (left_or_straight * med_cross * 0.05) + \
        (left_or_straight * heavy_cross * 0.26) + \
        (right * heavy_cross * 0.031) + \
        (left * med_parallel * 0.073) + \
        (left * heavy_parallel * 0.18)

    net.graph.es['bike_cost'] = np.nan_to_num(bike_cost)

if __name__ == '__main__':
    main()
