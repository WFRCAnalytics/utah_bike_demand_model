"""Run the Utah bike demand model example

This script runs the models in the micromobility_toolset on
a 25-zone example data set.

It utilizes the ActivitySim framework to register 'configs',
'base', and 'build' directories that contain all the necessary
instructions and data to run the models.

  - 'configs' contains a master settings file 'settings.yaml' that
  specifies the default model sequence to run in the absence of any
  command-line arguments. It lists information that is globally shared
  accross the models, such as TAZ data. 'configs' also contains other
  .yaml files that specify the behavior of the node network, the
  inputs/outputs, and model coefficients.

  - 'base' contains the initial data before any models are run. It
  contains initial trip tables, link/node data for the network, and
  TAZ data. Data may be stored in CSV or SQLITE formats.

  - 'build' is an empty directory that collects results from the model
  runs. It allows the models to pick up where the last one left off,
  and to compare the modified data to the base data.

This script can be either run with no arguments, which will run the model
list found in settings.yaml:

    python utah_bike_demand_model.py

Or with the --name argument to run a named model:

    python utah_bike_demand_model.py --name incremental_demand

The models will generally attempt to load data found in the 'build'
directory and continue where the last step left off. Otherwise they will
load data from the 'base' directory.

"""


import argparse

from activitysim.core import inject
from activitysim.core.config import setting

from micromobility_toolset import models


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest='name', action='store', choices=models.NAMES)
    args = parser.parse_args()

    inject.add_injectable('configs_dir', 'example_data/configs')
    inject.add_injectable('data_dir', 'example_data/base')
    inject.add_injectable('output_dir', 'example_data/build')

    if args.name:
        models.run(args.name)
    else:
        models.run(setting('models'))


if __name__ == '__main__':
    main()
