# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import pandas as pd
import os
import geopandas as gpd

#====================
# FUNCTIONS
#====================

# returns colnames of a pandas dataframe and their index like R does when you call colnames
def colnames(dataframe):
    values = (list(enumerate(list(dataframe.columns.values), 0)))
    for value in values:
        print(value)
        
# # Check fields (works with any ArcGIS compatible table)
# def checkFields(dataset):
#     fields = arcpy.ListFields(dataset)
#     for field in fields:
#         print("{0} is a type of {1} with a length of {2}"
#               .format(field.name, field.type, field.length))

# Check if a column in a datafram is unique
def isUnique(dataframe, column_name):
    boolean = dataframe[column_name].is_unique
    if boolean == True:
        print("Column: {} is unique")
    else:
        print("Column: {} is NOT unique")

#====================
# MAIN
#====================


"""
from buildings:
    residential_units
    households
    population
    jobs1 (accomodation, food services)
    jobs3 (construction)
    jobs4 (government/education)
    jobs5 (manufacturing)
    jobs6 (office)
    jobs7 (other)
    jobs9 (retail trade)
    jobs10 (wholesale, transport)
    
from parcels

"""

temp = r'E:\Micromobility\Aggregation'

remm_buildings = r"E:\Micromobility\Aggregation\run1244year2019allbuildings.csv"
# remm_parcels = r"E:\Micromobility\Aggregation\run1244year2019Parcels.csv"

parcels_geom = r"E:\Micromobility\Data\REMM_parcels.shp"
microzones_geom = r"E:\Projects\Misc\Create_Microzones\Output\microzones.shp"

# load csvs as pandas dataframes
buildings = pd.read_csv(remm_buildings)
# parcels = pd.read_csv(remm_parcels)


# filter columns
buildings_filtered = buildings[['parcel_id', 'parcel_acres','residential_units', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']].copy()

# aggregate buildings by parcel id and sum the other columns
buildings_grouped = buildings_filtered.groupby('parcel_id', as_index=False).sum()

# export to csv
# buildings_grouped.to_csv(os.path.join(temp, "buildings_sum_parcelID.csv"), index=False)

# read in parcel features
parcels = gpd.read_file(parcels_geom)
parcels = parcels[['parcel_id_', 'geometry']]

#  join to aggregated buildings
parcels_join = parcels.merge(buildings_grouped, left_on = 'parcel_id_', right_on = 'parcel_id' , how = 'inner')

# export to shape
parcels_join.to_file(os.path.join(temp, "parcels_buildings.shp"))


# spatial join here


# but i cheated and used arc first
parcels_with_zone_id = r"E:\Micromobility\Aggregation\parcels_households_sj.shp"
parcels_with_zone_id = gpd.read_file(parcels_with_zone_id)

parcels_with_zone_id_filt = parcels_with_zone_id[['zone_id', 'residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']]

# aggregate parcels by zone id and sum other columns
parcels_grouped = parcels_with_zone_id_filt.groupby('zone_id', as_index=False).sum()

# load microzones
microzones = gpd.read_file(microzones_geom)
microzones = microzones[['zone_id', 'geometry']]

#  join to aggregated parcels
microzones_join = microzones.merge(parcels_grouped, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

# export to shape
microzones_join.to_file(os.path.join(temp, "microzones_with_se_data.shp"))



# TAZ DATa prep
taz_geometry = r"E:\Data\TAZ_geometry2.shp"
taz_se_data = r"E:\Micromobility\Aggregation\TAZ_Data\taz_se831_2015.csv"


taz_geometry = gpd.read_file(taz_geometry)
taz_se_data = pd.read_csv(taz_se_data)
taz_join = taz_geometry.merge(taz_se_data, left_on = 'CO_TAZID', right_on = 'CO_TAZID' , how = 'inner')
taz_join_filt = taz_join[['CO_TAZID', 'TAZID' , 'geometry', 'AVGINCOME','ENROL_ELEM', 'ENROL_MIDL','ENROL_HIGH']]

taz_join_filt.to_file(os.path.join(temp, "taz_with_se_data.shp"))


'''
Some notes about the microzone atribution process:
    
    not all microzones have attributes, these are the missing polygons you see from viewing the dataset
    this is because I used "have center in" to perform the joining. Need to add those zones back in somehow with zeroes in the attributes fields
    
    nead to evaluate merge field technique when performing spatial join between microzones and taz se data. This occurs because
    some microzones span multiple TAZs. I used mean but that might not be the best method.
    
    need to factor in clipping of revised taz polygons. We got rid of the following because some of the mzs are too large
    Bert's bad taz's were filtered out using this query:
        
        not [tazid] in(688, 689,1339, 1340, 2870, 2871, 2872, 1789, 1913, 1914, 1915, 1916, 2854)
        
    Some microzone boundaries still don't make sense. Many mzs could be merged
    

'''













