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


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest='name', action='store', choices=model.list_steps())
    parser.add_argument('--sample', dest='sample', action='store', type=int)
    args = parser.parse_args()

    utah_base = model.Scenario(
        name='Utah Base Scenario',
        config='Model_Configs',
        data='Model_Inputs')

    # only use first 100 microzones for testing. remove to run full dataset.
    # this method can also be used to compare two scenarios.
    if args.sample:
        model.filter_impact_area(utah_base, zone_ids=list(range(0, args.sample)))

    if args.name:
        model.run(args.name, utah_base)

    else:
        model.run('generate_demand', utah_base)
        model.run('assign_demand', utah_base)


if __name__ == '__main__':
    main()
