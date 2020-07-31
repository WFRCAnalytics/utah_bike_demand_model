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

from micromobility_toolset import model
from micromobility_toolset.network import preprocessor


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest='name', action='store', choices=model.list_steps())
    args = parser.parse_args()

    utah_base = model.Scenario(
        name='Utah Base Scenario',
        config='Model_Configs',
        data='Model_Inputs')

    # only use first 100 microzones for testing. remove to run full dataset.
    # this method can also be used to compare two scenarios.
    model.filter_impact_area(utah_base, zone_ids=list(range(0, 100)))

    if args.name:
        model.run(args.name, utah_base)

    else:
        model.run('generate_demand', utah_base)
        model.run('assign_demand', utah_base)


@preprocessor()
def preprocess_network(net):
    """add network attributes that are combinations of existing attributes"""

    # add new link attribute columns
    link_attrs = [
        'bike_blvd_dist', # OSM: cycleway="shared" OR LADOT: bikeway=("Route" OR "Shared Route",
        # 'bike_path', # OSM: highway="cycleway" OR (highway="path" & bicycle="dedicated", OR LADOT: bikeway="Path"
        'prop_link_slope_2_4', # 2-4% upslope in forward direction, downslope in backward direction
        'prop_link_slope_4_6', # 4-6% upslope in forward direction, downslope in backward direction
        'prop_link_slope_6_plus', # 6+% upslope in forward direction, downslope in backward direction
        'no_bike_lane_light', # 10-20k AADT; no bike lane
        'no_bike_lane_med', # 20-30k AADT; no bike lane
        'no_bike_lane_heavy', # 30k+ AADT; no bike lane
    ]

    for attr in link_attrs:
        net.add_link_attribute(attr)

    # loop over links and calculate derived values
    for a in net.adjacency:
        for b in net.adjacency[a]:
            distance = net.get_link_attribute_value((a,b),'distance')
            slope = net.get_link_attribute_value((a,b), 'slope')
            bike_blvd = net.get_link_attribute_value((a,b), 'bike_boulevard')

            aadt = net.get_link_attribute_value((a,b), 'AADT')
            light = 10e3 < aadt < 20e3
            med = 20e3 <= aadt < 30e3
            heavy = 30e3 <= aadt

            # TODO: add these attributes to link file
            slope = 0  # net.get_link_attribute_value((a,b),'slope')
            bike_path = 0  # identifiers not in road_class
            no_bike_lane = 0  # identifiers not in road_class

            net.set_link_attribute_value( (a,b), 'bike_blvd_dist', distance * bike_blvd )
            # net.set_link_attribute_value( (a,b), 'bike_path', distance * bike_path )
            net.set_link_attribute_value( (a,b), 'prop_link_slope_2_4', distance * ( 2.0 < slope < 4.0 ) )
            net.set_link_attribute_value( (a,b), 'prop_link_slope_4_6', distance * ( 4.0 <= slope < 6.0 ) )
            net.set_link_attribute_value( (a,b), 'prop_link_slope_6_plus', distance * ( 6.0 <= slope ) )
            net.set_link_attribute_value( (a,b), 'no_bike_lane_light', distance * ( no_bike_lane and light ) )
            net.set_link_attribute_value( (a,b), 'no_bike_lane_med', distance * ( no_bike_lane and med ) )
            net.set_link_attribute_value( (a,b), 'no_bike_lane_heavy', distance * ( no_bike_lane and heavy ) )

    # add new dual (link-to-link) attribute columns
    net.add_dual_attribute('turn') # presence of a turn
    net.add_dual_attribute('stop_sign') # presence of a stop sighn
    net.add_dual_attribute('traffic_signal') # presence of a traffic signal
    net.add_dual_attribute('cross_traffic_ls_light') # left turn or straight across light traffic; 5-10k AADT
    net.add_dual_attribute('cross_traffic_ls_med') # left turn or straight across medium traffic; 10-20k AADT
    net.add_dual_attribute('cross_traffic_ls_heavy') # left turn or straight across heavy traffic; 20k+ AADT
    net.add_dual_attribute('cross_traffic_r') # right turn into medium to heavy traffic; 10k+ AADT
    net.add_dual_attribute('parallel_traffic_l_med') # left turn parallel to medium traffic; 10-20k AADT
    net.add_dual_attribute('parallel_traffic_l_heavy') # left turn parallel to heavy traffic; 20k+ AADT

    # loop over pairs of links and set attribute values
    for link1 in net.dual:
        for link2 in net.dual[link1]:

            traversal_type = net.traversal_type(link1,link2)
            l_turn = traversal_type in [5,7,10,13]
            r_turn = traversal_type in [4,6,9,11]
            straight = traversal_type in [8,12,14]

            cross_aadt = net.get_link_attribute_value(link2, 'AADT')
            parallel_aadt = net.get_link_attribute_value(link1, 'AADT')

            cross_light = 5e3 < cross_aadt < 10e3
            cross_med = 10e3 <= cross_aadt < 20e3
            cross_heavy = 20e3 <= cross_aadt
            parallel_med = 10e3 <= parallel_aadt < 20e3
            parallel_heavy = 20e3 <= parallel_aadt
            
            # TODO: confirm these traversal types
            cross = traversal_type in [6,7,13]
            parallel = traversal_type in [9,10]

            net.set_dual_attribute_value(link1,link2,'turn', 1 * (traversal_type in [3,4,5,6,7,9,10,11,13]) )

            # TODO: add stop sign and traffic signal columns to input data
            net.set_dual_attribute_value(link1,link2,'stop_sign',0)
            net.set_dual_attribute_value(link1,link2,'traffic_signal',0)

            net.set_dual_attribute_value(link1,link2,'cross_traffic_ls_light', 1 * (cross_light and (l_turn or straight)) )
            net.set_dual_attribute_value(link1,link2,'cross_traffic_ls_med', 1 * (cross_med and (l_turn or straight)) )
            net.set_dual_attribute_value(link1,link2,'cross_traffic_ls_heavy', 1 * (cross_heavy and (l_turn or straight)) )
            net.set_dual_attribute_value(link1,link2,'cross_traffic_r', 1 * (r_turn and (cross_med or cross_heavy)) )
            net.set_dual_attribute_value(link1,link2,'parallel_traffic_l_med', 1 * (parallel_med and l_turn) )
            net.set_dual_attribute_value(link1,link2,'parallel_traffic_l_heavy', 1 * (parallel_heavy and l_turn) )


if __name__ == '__main__':
    main()
