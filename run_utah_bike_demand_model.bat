
##### run utah bike demand model

## batch out inputs from ArcGIS
python Shp_To_Node_Link.py

## create bike demand matrices 
# from wfrc taz level matrices and land use data

## configure inputs and settings to micromobility_toolset

## run micromobility_toolset tool
# need to run just for the project area of influence

python utah_bike_demand_model.py

## put results back into ArcGIS 
