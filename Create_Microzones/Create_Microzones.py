# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 12:22:01 2020

@author: jreynolds

Creates Micro Traffic Analysis Zones (AKA Microzones or MAZs) from Utah roads network.
Also distributes attributes from REMM, TDM, AGRC
Requires data set folder
"""

import arcpy
import os
import glob
import pandas as pd
import geopandas as gpd
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

#==========================
# Args
#==========================
 
# From REMM
remm_buildings = r"E:\Micromobility\Data\Tables\run1244year2019allbuildings.csv"
remm_parcels = r"E:\Micromobility\Data\Zones\REMM_parcels_UTM12.shp"

# From TDM
taz_polygons = "E:\Micromobility\Data\Zones\TAZ_WFRC_UTM12.shp"
#taz_se_data = r"E:\Micromobility\Data\Tables\taz_se831_2015.csv"
taz_se_data = r"E:\Micromobility\Data\Tables\taz_se831_2019.csv"
#taz_se_data2 = r"E:\Micromobility\Data\Tables\LifeCycle_Households_Population_2015_831.csv"
taz_se_data2 = r"E:\Micromobility\Data\Tables\LifeCycle_Households_Population_2019_v8.3.1.csv"
#taz_se_data3 = r"E:\Micromobility\Data\Tables\Marginal_Income_2019_v831.csv"
taz_se_data3 = r"E:\Micromobility\Data\Tables\Marginal_Income_2019_v831.csv"

# From Other sources
roads = r"E:\Micromobility\Data\Multimodal_Network\Roads.shp"
trail_heads = r"E:\Micromobility\Data\Attributes\Trailheads.shp"
schools = r"E:\Micromobility\Data\Attributes\Schools.shp"
light_rail_stops = r"E:\Micromobility\Data\Attributes\LightRailStations_UTA.shp"
parks = r"E:\Micromobility\Data\Attributes\ParksLocal.shp"
commuter_rail_stops = r"E:\Micromobility\Data\Attributes\CommuterRailStations_UTA.shp"
enrollment = r"E:\Micromobility\Data\Attributes\College_Enrollment.shp"
group_quarters = r"E:\Micromobility\Data\Attributes\Group_Quarters_BlockGroup_2014_2018.shp"

# Other
temp_dir = os.path.join(os.getcwd(), 'Output')
delete_intermediate_layers = True

#====================
# FUNCTIONS
#====================

# returns colnames of a pandas dataframe and their index like R does when you call colnames
def colnames(dataframe):
    values = (list(enumerate(list(dataframe.columns.values), 0)))
    for value in values:
        print(value)
        
# Check fields (works with any ArcGIS compatible table)
def checkFields(dataset):
    fields = arcpy.ListFields(dataset)
    for field in fields:
        print("{0} is a type of {1} with a length of {2}"
              .format(field.name, field.type, field.length))

# Check if a column in a datafram is unique
def isUnique(dataframe, column_name):
    boolean = dataframe[column_name].is_unique
    if boolean == True:
        print("Column: {} is unique")
    else:
        print("Column: {} is NOT unique")


# sets the field map aggregation rule for a provided field/fieldmapping
# example merge rules: sum, mean, first, min, join, count, etc...
def modFieldMapping(fieldMappingsObject, field, mergeRule):
    fieldindex = fieldMappingsObject.findFieldMapIndex(field)
    fieldmap = fieldmappings.getFieldMap(fieldindex)
    fieldmap.mergeRule = mergeRule
    fieldMappingsObject.replaceFieldMap(fieldindex, fieldmap)

# add leading zeroes to TAZ values so that they may be properly used to create the COTAZID
def addLeadingZeroesTAZ(integer):
    if integer < 10:
        return "000{}".format(str(integer))
    if integer >= 10 and integer < 100:
        return "00{}".format(str(integer))
    if integer >= 100 and integer < 1000:
        return "0{}".format(str(integer))
    else:
        return integer

#==========================
# Create Preliminary Zones
#========================== 

"""
Dissolve WFRC/MAG model area TAZ polygons into single model area polygon

Feature to line with model area outline polygon to create model area polyline (outline)

Select all roads in Utah, SL, Davis, Weber, and Box Elder counties that are not 'negative direction" of divided highways and not ramps or part of ramp systems
(not (DOT_RTNAME like '%N' or char_length(DOT_RTNAME >5)) and (County_L = '49003' or County_L = '49011' or County_L = '49035' or County_L = '49049' or County_L = '49057')

Append selected roads into feature class with model area polyline created in step #2

Features to polygons with appended set of roads + outline to create 'preliminary blocks'

Add a part count and Use Calculate Geometry to set values = to # of parts

Eliminate contained parts from 'preliminary blocks'

Create a 'filled blocks' section layer where part count (set earlier) was set to a number > 1

Select by location the 'preliminary blocks' (target) that intersect with 'filled blocks' (might have to use have centroid within)

Delete the selected preliminary blocks and then append the filled blocks layer 

add TAZ ID to microzone using centroid probably
"""


print("Creating preliminary zones...")

# Dissolve TAZ features into one polygon
taz_dissolved = arcpy.Dissolve_management(taz_polygons, os.path.join(temp_dir, 'taz_dissolved.shp'))

# Get TAZ outline
taz_outline = arcpy.FeatureToLine_management(taz_dissolved, os.path.join(temp_dir, 'taz_outline.shp')) 

# Select roads that are (in either Salt Lake, Utah, Davis, Weber, or Box Elder County), not highway ramps, and limit double lane highway features to one line
roads_layer = arcpy.MakeFeatureLayer_management(roads, 'roads')
query = """CHAR_LENGTH( "DOT_RTNAME") <= 5  AND NOT "DOT_RTNAME" LIKE '%N' AND ("COUNTY_L" = '49003' OR "COUNTY_L"  = '49011' OR "COUNTY_L" = '49035'  OR "COUNTY_L" = '49049' OR "COUNTY_L" =  '49057')"""
arcpy.SelectLayerByAttribute_management(roads_layer, "NEW_SELECTION", query)

# Clip roads by taz boundary
roads_clipped = arcpy.Clip_analysis(roads_layer, taz_dissolved, os.path.join(temp_dir, 'roads_clipped.shp'))

# Merge roads with taz outline 
merged_roads = arcpy.Merge_management([roads_clipped, taz_outline], os.path.join(temp_dir, 'roads_plus_taz_outline.shp'))

# Create zones using feature to polygon tool
prelim_zones = arcpy.FeatureToPolygon_management(merged_roads, os.path.join(temp_dir,"prelim_zones.shp"))

#========================================
# Eliminate Small Zones using two passes
#========================================

print('Eliminating small zones (1st pass)...')
arcpy.AddField_management(prelim_zones, 'area_sqm', 'FLOAT')
arcpy.CalculateGeometryAttributes_management(prelim_zones, [['area_sqm','AREA']], '', 'SQUARE_METERS')
zones_layer = arcpy.MakeFeatureLayer_management(prelim_zones, 'zones')
query = """"area_sqm" < 5000"""
arcpy.SelectLayerByAttribute_management(zones_layer, "NEW_SELECTION", query)
zones_eliminated = arcpy.Eliminate_management(zones_layer, os.path.join(temp_dir, 'zones_eliminated_again.shp'), 'LENGTH')

print('Eliminating small zones (2nd pass)...')
arcpy.CalculateGeometryAttributes_management(zones_eliminated, [['area_sqm','AREA']], '', 'SQUARE_METERS')
zones_layer2 = arcpy.MakeFeatureLayer_management(zones_eliminated, 'zones')
#query = """"area_sqm" < 10000"""
query = """"area_sqm" < 15000"""
arcpy.SelectLayerByAttribute_management(zones_layer2, "NEW_SELECTION", query)
zones_eliminated2 = arcpy.Eliminate_management(zones_layer2, os.path.join(temp_dir, 'zones_eliminated_again2.shp'), 'LENGTH')

#==========================
# Eliminate Zone Rings 
#==========================  

print("Eliminating zone inner rings ...")

# Add parts and rings fields
arcpy.AddField_management(zones_eliminated2, 'parts', 'LONG')
arcpy.AddField_management(zones_eliminated2, 'rings', 'LONG')

# Use cursor to populate parts and rings
fields = ["FID", "shape@", "parts", "rings"]
with arcpy.da.UpdateCursor(zones_eliminated2, fields) as cursor:
    for row in cursor:
        shape = row[1]
        parts = shape.partCount
        rings = shape.boundary().partCount
        
        row[2] = parts
        row[3] = rings
        
        cursor.updateRow(row)

# Eliminate polygon part
microzones_no_rings = arcpy.EliminatePolygonPart_management(zones_eliminated2, os.path.join(temp_dir, 'microzones_no_rings.shp'), 'PERCENT',"", 50)

# Get filled zones
filled_zones = arcpy.MakeFeatureLayer_management(microzones_no_rings, 'zones')
query = """"rings" > 1"""
arcpy.SelectLayerByAttribute_management(filled_zones, "NEW_SELECTION", query)

# Erase zones with rings
microzones_rings_erased = arcpy.Erase_analysis(zones_eliminated2, filled_zones, os.path.join(temp_dir, 'zones_erased.shp'))

# add missing zones back
merged_zones = arcpy.Merge_management([microzones_rings_erased, filled_zones], os.path.join(temp_dir, 'merged_zones.shp'))


# add persistent unique ID field
arcpy.CalculateField_management(merged_zones,"zone_id",'!{}!'.format('FID'))

# perform spatial join to get TAZ ID - may need more robust method for zones that cross multiple Tazs
print('Getting TAZ ids...')
microzones = arcpy.SpatialJoin_analysis(merged_zones, taz_polygons, os.path.join(temp_dir, 'microzones.shp'),'JOIN_ONE_TO_ONE', '', '', 'HAVE_THEIR_CENTER_IN')

# Delete extra fields
fields = ["Join_Count", 'TARGET_FID', 'Id', 'ORIG_FID', 'OBJECTID', 'rings', 'parts']
for field in fields:
    try:
        arcpy.DeleteField_management(microzones, field)
    except:
        print('Unable to delete field: {}'.format(field))


# Clip microzones using determined (good) tazs
print('Clipping out bad TAZ areas...')
taz_layer = arcpy.MakeFeatureLayer_management(taz_polygons, 'tazs')
query = """not "tazid" in(688, 689,1339, 1340, 2870, 2871, 2872, 1789, 1913, 1914, 1915, 1916, 2854)"""
arcpy.SelectLayerByAttribute_management(taz_layer, "NEW_SELECTION", query)
microzones_geom =  os.path.join(temp_dir, "maz_clipped.shp")
maz_clipped = arcpy.Clip_analysis(microzones, taz_layer, microzones_geom)


# Delete intermediate files (optional)
if delete_intermediate_layers == True:
    print('Doing some clean-up...')
    trash = [filled_zones, zones_layer, zones_layer2, merged_roads, merged_zones, microzones_no_rings, microzones_rings_erased, prelim_zones, roads_clipped, taz_dissolved, taz_outline, zones_eliminated, zones_eliminated2, microzones]
    print("Deleting intermediate files...")
    for dataset in trash:
        try:
            arcpy.Delete_management(dataset)
            del(dataset)
        except:
            print('A file was unable to be deleted')


#============================================
#============================================
# Attribution
#============================================
#============================================


#================================
# Aggregate REMM Buildings data
#================================ 

"""
from buildings:
    residential_units
    households
    population
    jobs1 (accomodation, food services)
    jobs2 (construction)
    jobs3 (government/education)
    jobs4 (healthcare)
    jobs5 (manufacturing)
    jobs6 (office)
    jobs7 (other)
    jobs8 (mining)
    jobs9 (retail trade)
    jobs10 (wholesale, transport)
    jobs11 (agriculture)
    jobs12 (home-based job)
    
add back in missing jobs and total jobs

"""

# load csvs as pandas dataframes
buildings = pd.read_csv(remm_buildings)

# filter columns
buildings_filtered = buildings[['parcel_id', 'parcel_acres','residential_units', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']].copy()

# aggregate buildings by parcel id and sum the other columns
buildings_grouped = buildings_filtered.groupby('parcel_id', as_index=False).sum()

# export to csv
# buildings_grouped.to_csv(os.path.join(temp, "buildings_sum_parcelID.csv"), index=False)

# read in parcel features
parcels = gpd.read_file(remm_parcels)
parcels = parcels[['parcel_id', 'geometry']]

#  join to aggregated buildings
parcels_join = parcels.merge(buildings_grouped, left_on = 'parcel_id', right_on = 'parcel_id' , how = 'inner')

# export to shape
parcels_join.to_file(os.path.join(temp_dir, "parcels_with_aggd_buildings_data.shp"))

# convert parcels to points centroids
print('Converting parcels to points...')
arcpy.FeatureToPoint_management(os.path.join(temp_dir, "parcels_with_aggd_buildings_data.shp"), os.path.join(temp_dir, "pts_with_aggd_buildings_data.shp"), "INSIDE")

# spatial join here
target_features = os.path.join(temp_dir, "maz_clipped.shp")
join_features = os.path.join(temp_dir, "pts_with_aggd_buildings_data.shp")
output_features = os.path.join(temp_dir, "maz_parcels_spatial_join.shp")

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(target_features)
fieldmappings.addTable(join_features)

# Set field aggregation rule using loop
fields_list = ['residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']

for field in fields_list:
    modFieldMapping(fieldmappings, field, 'Sum')

# run spatial join
print('Joining parcel data to microzones...')
arcpy.SpatialJoin_analysis(target_features, join_features, output_features, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "CONTAINS")

# Select fields
maz_remm_data = gpd.read_file(output_features)
maz_remm_data = maz_remm_data[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10', 'geometry']]

# export to shape
maz_output = os.path.join(temp_dir, "microzones_with_remm_data.shp")
maz_remm_data.to_file(maz_output)

# Free up memory
print('doing some clean-up...')
trash = [buildings, buildings_filtered, buildings_grouped, parcels, parcels_join]
for dataset in trash:
    try:
        del dataset
    except:
        print('A file was unable to be deleted')



#==================================
# Disaggregate TAZ level SE data
#================================== 

"""
Age Groups:
AG1) Children - 0 to 17
AG2) Adults - 18 to 64
AG3) Seniors - 65 +

Life Cycles:
LC1) households with no children and seniors
LC2) households with children and no seniors
LC3) households with seniors and may have children

Income Groups Count (Need to divide this by population)
1) $0 to 34,999
2) $35,000 to 49,999
3) $50,000 to 99,999
4) $100,000+

    
"""

print('Creating TAZ level Socioeconomic data layer...')

# Read in taz level se data
taz_se_data = pd.read_csv(taz_se_data)
taz_se_data['CO_TAZID'] = taz_se_data['CO_TAZID'].astype(str)

# Read in taz level life cycle/age data and recreate COTAZID field
taz_se_data2 = pd.read_csv(taz_se_data2)
taz_se_data2['TAZID'] = taz_se_data2['Z'].map(addLeadingZeroesTAZ) 
taz_se_data2['CO_TAZID'] = taz_se_data2['CO_FIPS'].astype(str) + taz_se_data2['TAZID'].astype(str)

# Read in taz level income distribution data and recreate COTAZID field
taz_se_data3 = pd.read_csv(taz_se_data3)
taz_se_data3['CO_TAZID'] = taz_se_data3['CO_TAZID'].astype(str)

# read in taz polygons
taz_geometry = gpd.read_file(taz_polygons)
taz_geometry['CO_TAZID'] = taz_geometry['CO_TAZID'].astype(str)

# join se data to taz polygons 
taz_join = taz_geometry.merge(taz_se_data, how = 'inner', left_on = 'CO_TAZID', right_on = 'CO_TAZID')
taz_join2 = taz_join.merge(taz_se_data2, left_on = 'CO_TAZID', right_on = 'CO_TAZID' , how = 'inner')
taz_join3 = taz_join2.merge(taz_se_data3, left_on = 'CO_TAZID', right_on = 'CO_TAZID' , how = 'inner')


# filter to desired columns
taz_join_filt = taz_join3[['CO_TAZID', 'TAZID_x' , 'geometry', 'AVGINCOME','ENROL_ELEM', 'ENROL_MIDL','ENROL_HIGH', 'POP_LC1', 'POP_LC2', 'POP_LC3', 'HHSIZE_LC1', 'HHSIZE_LC2', 'HHSIZE_LC3', 'PCT_POPLC1', 'PCT_POPLC2', 'PCT_POPLC3', 'PCT_AG1', 'PCT_AG2', 'PCT_AG3', 'INC1', 'INC2', 'INC3', 'INC4']]

# export taz data to shape
out_taz_data = os.path.join(temp_dir, "taz_with_se_data.shp")
taz_join_filt.to_file(out_taz_data)

# Distribute attributes larger TAZ attributes to MAZ, using rasters and zonal stats
taz_fields = ['AVGINCOME','ENROL_ELEM', 'ENROL_MIDL','ENROL_HIGH', 'HHSIZE_LC1', 'HHSIZE_LC2', 'HHSIZE_LC3', 'PCT_POPLC1', 'PCT_POPLC2', 'PCT_POPLC3', 'PCT_AG1', 'PCT_AG2', 'PCT_AG3', 'INC1', 'INC2', 'INC3', 'INC4']

for field in taz_fields:
    
    print("Disaggregating {} to maz level...".format(field))
    
    # convert taz se data to raster resolution 20 sq meters 
    out_p2r = os.path.join(temp_dir,"taz_{}.tif".format(field))
    arcpy.FeatureToRaster_conversion(out_taz_data, field, out_p2r, cell_size=20)
 
    # use zonal stats (mean) to get table of values for each microzone
    out_table = os.path.join(temp_dir,"taz_{}.dbf".format(field))
    arcpy.sa.ZonalStatisticsAsTable(maz_output, 'zone_id', out_p2r, out_table, 'DATA', 'MEAN')
    out_table_csv = os.path.join(temp_dir,"taz_{}.csv".format(field))
    arcpy.TableToTable_conversion(out_table, os.path.dirname(out_table_csv), os.path.basename(out_table_csv))

    # merge table back with Microzones        
    zonal_table = pd.read_csv(out_table_csv)
    zonal_table =  zonal_table[['zone_id', 'MEAN']]
    zonal_table.columns = ['zone_id', field]
    zonal_table['zone_id'] = zonal_table['zone_id'].astype(str)
    maz_remm_data = maz_remm_data.merge(zonal_table, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')
    
    # delete the raster
    if delete_intermediate_layers == True:
        arcpy.Delete_management(out_table)
        arcpy.Delete_management(out_table_csv)
        arcpy.Delete_management(out_p2r)
    

# normalize school enrollment data
maz_remm_data['ENROL_ELEM'] = maz_remm_data['ENROL_ELEM']/maz_remm_data['population']
maz_remm_data['ENROL_MIDL'] = maz_remm_data['ENROL_MIDL']/maz_remm_data['population']
maz_remm_data['ENROL_HIGH'] = maz_remm_data['ENROL_HIGH']/maz_remm_data['population']

# normalize income group data
totalpop = maz_remm_data['INC1'] + maz_remm_data['INC2'] + maz_remm_data['INC3'] + maz_remm_data['INC4']
maz_remm_data['INC1'] = maz_remm_data['INC1']/totalpop
maz_remm_data['INC2'] = maz_remm_data['INC2']/totalpop
maz_remm_data['INC3'] = maz_remm_data['INC3']/totalpop
maz_remm_data['INC4'] = maz_remm_data['INC4']/totalpop

# Free up memory
print('Doing some clean-up...')
trash = [taz_se_data, taz_se_data2, zonal_table]
for dataset in trash:
    try:
        del dataset
    except:
        print('A file was unable to be deleted')


#===================
# Other datasets
#===================

print("Computing attraction attributes...")


#-------------------
# Parks
#-------------------
"""
1:  Acreage > 10
2:  5 < Acreage < 10
3:  Acreage < 5
"""

print("Working on parks...")
parks_lyr =  arcpy.MakeFeatureLayer_management(parks, 'parks')
  
# add empty park score field if it doesn't exist
if not "PARK_SCORE" in arcpy.ListFields(parks_lyr):  
    arcpy.AddField_management(parks_lyr, field_name="PARK_SCORE", field_type='LONG')
    
# calculate park score
query = """"ACRES" > 10"""
arcpy.SelectLayerByAttribute_management(parks_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(parks_lyr, "PARK_SCORE", '3')

query = """"ACRES" > 5 AND "ACRES" < 10"""
arcpy.SelectLayerByAttribute_management(parks_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(parks_lyr, "PARK_SCORE", '2')

query = """"ACRES" < 5"""
arcpy.SelectLayerByAttribute_management(parks_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(parks_lyr, "PARK_SCORE", '1')

arcpy.SelectLayerByAttribute_management(parks_lyr, "CLEAR_SELECTION")

# use spatial join to get park score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(parks_lyr)
modFieldMapping(fieldmappings, 'PARK_SCORE', 'max')

maz_park_join = os.path.join(temp_dir, "maz_park_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, parks_lyr, maz_park_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_park_join_df = gpd.read_file(maz_park_join)
maz_park_join_df =  maz_park_join_df[['zone_id', "PARK_SCORE"]]
maz_remm_data = maz_remm_data.merge(maz_park_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#-------------------
# Schools
#-------------------
"""
Online/Higher Education (1): NOT ("EDTYPE" = 'Regular Education' AND "GRADEHIGH" = '12' AND "G_Low" > 0)  AND ("SCHOOLTYPE" = 'Online Charter School' OR "SCHOOLTYPE" = 'Online School' OR "SCHOOLTYPE" = 'Residential Campus' OR "EDTYPE" = 'Residential Treatment' OR "EDTYPE" = 'Alternative' OR "EDTYPE" = 'Adult High')

High Schools & Colleges (2): ("EDTYPE" = 'Regular Education' AND "GRADEHIGH" = '12' AND "G_Low" > 0) OR ("SCHOOLTYPE" = 'Regional Campus')

Elem/Middle (3): Everything else
"""
print("Working on schools...")
schools_lyr =  arcpy.MakeFeatureLayer_management(schools, 'schools')

# add school score field if it doesn't exist
if not "SCHOOL_CD" in arcpy.ListFields(schools_lyr):  
    arcpy.AddField_management(schools_lyr, field_name="SCHOOL_CD", field_type='LONG')
else:
    arcpy.DeleteField_management(schools_lyr, field_name="SCHOOL_CD")
    arcpy.AddField_management(schools_lyr, field_name="SCHOOL_CD", field_type='LONG')

# calculate school code
query = """NOT("EDTYPE" = 'Regular Education' AND "GRADEHIGH" = '12' AND "G_Low" > 0)  AND ("SCHOOLTYPE" = 'Online Charter School' OR "SCHOOLTYPE" = 'Online School' OR "SCHOOLTYPE" = 'Regional Campus' OR "SCHOOLTYPE" = 'Residential Campus' OR "EDTYPE" = 'Residential Treatment' OR "EDTYPE" = 'Alternative' OR "EDTYPE" = 'Adult High' OR "EDTYPE" = 'Vocational')"""
arcpy.SelectLayerByAttribute_management(schools_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(schools_lyr, "SCHOOL_CD", '1')

query = """"EDTYPE" = 'Regular Education' AND "GRADEHIGH" = '12' AND "G_Low" > 0"""
arcpy.SelectLayerByAttribute_management(schools_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(schools_lyr, "SCHOOL_CD", '2')

query = """"SCHOOL_CD" <> 2 AND "SCHOOL_CD" <> 1"""
arcpy.SelectLayerByAttribute_management(schools_lyr, "NEW_SELECTION", query)
arcpy.CalculateField_management(schools_lyr, "SCHOOL_CD", '3')

arcpy.SelectLayerByAttribute_management(schools_lyr, "CLEAR_SELECTION")

# use spatial join to get school code on to microzones (if multiple scores present, maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(schools_lyr)
modFieldMapping(fieldmappings, "SCHOOL_CD", 'max')

maz_school_join = os.path.join(temp_dir, "maz_schools_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, schools, maz_school_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge school score field back to full table
maz_school_join_df = gpd.read_file(maz_school_join)
maz_school_join_df =  maz_school_join_df[['zone_id', "SCHOOL_CD"]]
maz_remm_data = maz_remm_data.merge(maz_school_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#-------------------
# College Enrollment
#-------------------
"""
  Enrollment count from TDM Trip table control except LDS Business College and Westminster

"""

print("Working on college enrollment...")
enrollment_lyr =  arcpy.MakeFeatureLayer_management(enrollment, 'college_enrollment')

# use spatial join to get enrollment on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(enrollment_lyr)
modFieldMapping(fieldmappings, 'Enrollment', 'max')

maz_ce_join = os.path.join(temp_dir, "maz_ce_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, enrollment_lyr, maz_ce_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge college enrollment field back to full table
maz_ce_join_df = gpd.read_file(maz_ce_join) # Might have to fill in zeroes
maz_ce_join_df =  maz_ce_join_df[['zone_id', 'Enrollment']]
maz_remm_data = maz_remm_data.merge(maz_ce_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')




#-------------------
# trailheads 
#-------------------
"""
  3) most attractive 2) moderately attractive 1) least attractive
    
"""

print("Working on trail heads...")
trail_heads_lyr =  arcpy.MakeFeatureLayer_management(trail_heads, 'trail_heads')

# add school score field if it doesn't exist
# if not "trail_heads" in arcpy.ListFields(trail_heads_lyr):  
#     arcpy.AddField_management(trail_heads_lyr, field_name="TRAIL_HEAD", field_type='LONG')

# code for calculating trail head presence
# arcpy.CalculateField_management(trail_heads_lyr, "TRAIL_HEAD", '1')

# use spatial join to get trail head score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(trail_heads_lyr)
modFieldMapping(fieldmappings, 'TH_SCORE', 'max')

maz_th_join = os.path.join(temp_dir, "maz_th_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, trail_heads_lyr, maz_th_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_th_join_df = gpd.read_file(maz_th_join) # Might have to fill in zeroes
maz_th_join_df =  maz_th_join_df[['zone_id', 'TH_SCORE']]
maz_remm_data = maz_remm_data.merge(maz_th_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#----------------------
# Commuter Rail Stops
#----------------------

"""
  1) has commuter rail stop 0 ) none
"""

print("Working on commuter rail stops...")
cr_lyr =  arcpy.MakeFeatureLayer_management(commuter_rail_stops, 'cr_layer')

# add school score field if it doesn't exist
if not "COMM_RAIL" in arcpy.ListFields(cr_lyr):  
    arcpy.AddField_management(cr_lyr, field_name="COMM_RAIL", field_type='LONG')

# code for calculating trail head presence
arcpy.CalculateField_management(cr_lyr, "COMM_RAIL", '1')

# use spatial join to get commuter rail presence on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(cr_lyr)
modFieldMapping(fieldmappings, 'COMM_RAIL', 'max')

maz_cr_join = os.path.join(temp_dir, "maz_cr_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, cr_lyr, maz_cr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_cr_join_df = gpd.read_file(maz_cr_join) # Might have to fill in zeroes
maz_cr_join_df =  maz_cr_join_df[['zone_id', 'COMM_RAIL']]
maz_remm_data = maz_remm_data.merge(maz_cr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')



#----------------------
# Light Rail Stops
#----------------------

"""
  1) has light rail stop 0 ) none
"""

print("Working on light rail stops...")
lr_lyr =  arcpy.MakeFeatureLayer_management(light_rail_stops, 'lr_layer')

# add school score field if it doesn't exist
if not "LIGHT_RAIL" in arcpy.ListFields(lr_lyr):  
    arcpy.AddField_management(lr_lyr, field_name="LIGHT_RAIL", field_type='LONG')

# code for calculating trail head presence
arcpy.CalculateField_management(lr_lyr, "LIGHT_RAIL", '1')

# use spatial join to get school code on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones_geom)
fieldmappings.addTable(lr_lyr)
modFieldMapping(fieldmappings, 'LIGHT_RAIL', 'max')

maz_lr_join = os.path.join(temp_dir, "maz_lr_join.shp")
arcpy.SpatialJoin_analysis(microzones_geom, lr_lyr, maz_lr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_lr_join_df = gpd.read_file(maz_lr_join) # Might have to fill in zeroes
maz_lr_join_df =  maz_lr_join_df[['zone_id', 'LIGHT_RAIL']]
maz_remm_data = maz_remm_data.merge(maz_lr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')



#----------------------
# Group quarters
#----------------------

print("Working on group quarters data...")

# distribute gqu_ratio field - group quarters (university) / population
field = 'GQU_RATIO'

# convert taz se data to raster resolution 20 sq meters 
out_p2r = os.path.join(temp_dir,"{}.tif".format(field))
arcpy.FeatureToRaster_conversion(group_quarters, field, out_p2r, cell_size=20)
 
# use zonal stats (mean) to get table of values for each microzone
out_table = os.path.join(temp_dir,"{}.dbf".format(field))
arcpy.sa.ZonalStatisticsAsTable(maz_output, 'zone_id', out_p2r, out_table, 'DATA', 'MEAN')
out_table_csv = os.path.join(temp_dir,"{}.csv".format(field))
arcpy.TableToTable_conversion(out_table, os.path.dirname(out_table_csv), os.path.basename(out_table_csv))

# merge table back with Microzones        
zonal_table = pd.read_csv(out_table_csv)
zonal_table =  zonal_table[['zone_id', 'MEAN']]
zonal_table.columns = ['zone_id', field]
zonal_table['zone_id'] = zonal_table['zone_id'].astype(str)
maz_remm_data = maz_remm_data.merge(zonal_table, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

# delete the raster
if delete_intermediate_layers == True:
    arcpy.Delete_management(out_table)
    arcpy.Delete_management(out_table_csv)
    arcpy.Delete_management(out_p2r)



#================================
# WRAP-UP
#================================ 

# final export
final_zones = os.path.join(temp_dir, "microzones.shp")
maz_remm_data.to_file(final_zones)


# add area sq meters and sq miles
print("Adding area calculations...")

arcpy.AddField_management(final_zones, field_name="area_sqm", field_type='float')
arcpy.AddField_management(final_zones, field_name="area_acres", field_type='float')

with arcpy.da.UpdateCursor(final_zones, ['area_sqm', 'area_acres', 'SHAPE@AREA']) as cursor:
    for row in cursor:
        row[0] = row[2]
        row[1] = row[2] * 0.000247105 # convert to acres
        cursor.updateRow(row)

print('Zones complete!!')

del buildings
del buildings_filtered
del buildings_grouped
del cr_lyr
del cursor
del enrollment_lyr
del fieldmappings
del filled_zones
del lr_lyr
del maz_clipped
del maz_ce_join_df
del maz_cr_join_df
del maz_lr_join_df
del maz_park_join_df
del merged_roads
del merged_zones
del microzones
del microzones_no_rings
del microzones_rings_erased
del parks_lyr
del prelim_zones
del roads_clipped
del roads_layer
del row
del schools_lyr
del shape
del taz_dissolved
del taz_join
del taz_join2
del taz_join3
del taz_join_filt
del taz_layer
del taz_outline
del taz_se_data
del taz_se_data2
del taz_se_data3
del trail_heads_lyr
del zonal_table
del zones_eliminated
del zones_eliminated2
del zones_layer
del zones_layer2






