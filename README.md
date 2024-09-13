# Utah Bike Demand Model

## Dependencies
  - At least 32 gb of RAM
  - Python 3.x
  - [micromobility_toolset](https://github.com/RSGInc/micromobility_toolset)

## Quick start

  - download/clone repository
  - open a Windows command line in this folder
  - `pip install git+https://github.com/rsginc/micromobility_toolset` to install the [micromobility_toolset](https://github.com/RSGInc/micromobility_toolset) package
  - run `python Create_Microzones.py` to create the microzone data if needed
  - run `python Convert_MM_Network.py` to create the network data if needed
  - run `python utah_bike_demand_model.py` to run the utah bike demand model
    - add `--name generate_demand` or `--name assign_demand` to run the steps independently
    - add `--sample 100` to sample only the first 100 microzones
## Documentation

  - [Meeting Notes](https://github.com/RSGInc/utah_bike_demand_model/wiki)
  - [Model Design](Model_Design/wfrc model spec 01-28-21.pdf)
  - [Bike Model Coefficents Tracker](https://docs.google.com/spreadsheets/d/1lWqqHUEF0IOpqIgNil0gEWuN29oVjzCsLly4eeluqpA/edit?usp=sharing)  
  - Model outputs are saved in 'logs' folder
  
  
## Toolsets

1. Convert Network
2. Create Microzones
3. Utah Bike Demand Model
    - Trip Generation
    - Trip Distribution
    - Trip Assignment
4. Post-Process Bike Model Outputs
