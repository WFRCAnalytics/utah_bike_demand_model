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
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import numpy as np
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")


#==========================
# Args
#==========================
 
# From REMM
remm_buildings = r".\Inputs\run1244year2019allbuildings.csv"
remm_parcels = r".\Inputs\REMM_parcels_UTM12.shp"

# From TDM
taz_polygons = ".\Inputs\TAZ_WFRC_UTM12.shp"
taz_se_data = r".\Inputs\taz_se831_2019.csv"
taz_se_data2 = r".\Inputs\LifeCycle_Households_Population_2019_v8.3.1.csv"
taz_se_data3 = r".\Inputs\Marginal_Income_2019_v831.csv"

# From Other sources
roads = r".\Inputs\Roads.shp"
trail_heads = r".\Inputs\Trailheads.shp"
long_dist_rec = r".\Inputs\Long_Dist_Rec_Pts.shp"
mtn_bike_hike = r".\Inputs\Mtn_Bike_Hiking_Trailheads.shp"
schools = r".\Inputs\Schools.shp"
light_rail_stops = r".\Inputs\LightRailStations_UTA.shp"
parks = r".\Inputs\ParksLocal.shp"
commuter_rail_stops = r".\Inputs\CommuterRailStations_UTA.shp"
enrollment = r".\Inputs\College_Enrollment.shp"
group_quarters = r".\Inputs\Group_Quarters_BlockGroup_2014_2018.shp"
industrial_districts = r".\Inputs\Industrial_Districts.shp"
bike_kiosks = r".\Inputs\GREENbike_kiosk_buffer.shp"
nodes = r"..\Convert_MM_Network\Outputs\nodes.shp"
network = r"..\Convert_MM_Network\Outputs\links.shp"

# Other
temp_dir = os.path.join(os.getcwd(), 'Outputs')
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


# create outputs folder
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

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
merged_zones = (os.path.join(temp_dir, 'merged_zones.shp'))
arcpy.Merge_management([microzones_rings_erased, filled_zones], merged_zones)


# Clip microzones using determined (good) tazs
print('Clipping out bad TAZ areas...')
taz_layer = arcpy.MakeFeatureLayer_management(taz_polygons, 'tazs')
query = """not "tazid" in(688, 689,1339, 1340, 2870, 2871, 2872, 1789, 1913, 1914, 1915, 1916, 2854)"""
arcpy.SelectLayerByAttribute_management(taz_layer, "NEW_SELECTION", query)
microzones_geom =  os.path.join(temp_dir, "maz_clipped.shp")
maz_clipped = arcpy.Clip_analysis(merged_zones, taz_layer, microzones_geom)


#==========================
# Add Canyon zones
#========================== 

# Erase existing features pre drawn zones, then append those zones
print("Adding canyon zones...")
canyon_zones = r'.\Inputs\Canyon_Zones.shp'    
maz_erased = os.path.join(temp_dir, 'maz_erased.shp')
arcpy.Erase_analysis(maz_clipped, canyon_zones, maz_erased)
maz_and_canyons = os.path.join(temp_dir, 'maz_and canyons.shp')
arcpy.Merge_management([canyon_zones, maz_erased], maz_and_canyons)

#==========================
# Finishing up
#========================== 

# add persistent unique ID field
arcpy.CalculateField_management(maz_and_canyons,"zone_id",'!{}!'.format('FID'))

# perform spatial join to get TAZ ID - may need more robust method for zones that cross multiple Tazs
print('Getting TAZ ids...')
microzones = os.path.join(temp_dir, 'maz_taz.shp')
arcpy.SpatialJoin_analysis(maz_and_canyons, taz_polygons, microzones,'JOIN_ONE_TO_ONE', '', '', 'HAVE_THEIR_CENTER_IN')


# Delete extra fields
fields = ["Join_Count", 'TARGET_FID', 'Id', 'ORIG_FID', 'OBJECTID', 'rings', 'parts']
for field in fields:
    try:
        arcpy.DeleteField_management(microzones, field)
    except:
        print('Unable to delete field: {}'.format(field))

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

# read in parcel features
parcels = pd.DataFrame.spatial.from_featureclass(remm_parcels)
parcels = parcels[['parcel_id', 'SHAPE']]

#  join to aggregated buildings
parcels_join = parcels.merge(buildings_grouped, left_on = 'parcel_id', right_on = 'parcel_id' , how = 'inner')

# export to shape
parcels_aggd_buildings = os.path.join(temp_dir, "parcels_with_aggd_buildings_data.shp")
parcels_join.spatial.to_featureclass(location=parcels_aggd_buildings)

# convert parcels to points centroids
print('Converting parcels to points...')
pts_aggd_buildings = os.path.join(temp_dir, "pts_with_aggd_buildings_data.shp")
arcpy.FeatureToPoint_management(os.path.join(temp_dir, "parcels_with_aggd_buildings_data.shp"), pts_aggd_buildings, "INSIDE")

# spatial join here
target_features = microzones
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
maz_remm_data = pd.DataFrame.spatial.from_featureclass(output_features)
maz_remm_data = maz_remm_data[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10', 'SHAPE']]

# export to shape
maz_output = os.path.join(temp_dir, "microzones_with_remm_data.shp")
maz_remm_data.spatial.to_featureclass(location=maz_output)

# Free up memory
del buildings
del buildings_filtered
del buildings_grouped
del parcels
del parcels_join

#----------------------
# Total Jobs
#----------------------

print("Working on total jobs...")

# create total jobs attribute
maz_remm_data['jobs_total'] = maz_remm_data['jobs1']+ maz_remm_data['jobs3'] + maz_remm_data['jobs4'] +  maz_remm_data['jobs5'] + maz_remm_data['jobs6'] +  maz_remm_data['jobs7']

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
taz_geometry = pd.DataFrame.spatial.from_featureclass(taz_polygons)
taz_geometry['CO_TAZID'] = taz_geometry['CO_TAZID'].astype(str)

# join se data to taz polygons 
taz_join = taz_geometry.merge(taz_se_data, how = 'inner', left_on = 'CO_TAZID', right_on = 'CO_TAZID')
taz_join2 = taz_join.merge(taz_se_data2, left_on = 'CO_TAZID', right_on = 'CO_TAZID' , how = 'inner')
taz_join3 = taz_join2.merge(taz_se_data3, left_on = 'CO_TAZID', right_on = 'CO_TAZID' , how = 'inner')


# filter to desired columns
taz_join_filt = taz_join3[['CO_TAZID', 'TAZID_x' , 'SHAPE', 'AVGINCOME','ENROL_ELEM', 'ENROL_MIDL','ENROL_HIGH', 'POP_LC1', 'POP_LC2', 'POP_LC3', 'HHSIZE_LC1', 'HHSIZE_LC2', 'HHSIZE_LC3', 'PCT_POPLC1', 'PCT_POPLC2', 'PCT_POPLC3', 'PCT_AG1', 'PCT_AG2', 'PCT_AG3', 'INC1', 'INC2', 'INC3', 'INC4']].copy()

# export taz data to shape
out_taz_data = os.path.join(temp_dir, "taz_with_se_data.shp")
taz_join_filt.spatial.to_featureclass(location=out_taz_data)

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
    maz_remm_data = maz_remm_data.merge(zonal_table, left_on = 'zone_id', right_on = 'zone_id' , how = 'outer')
    
    # delete the raster
    if delete_intermediate_layers == True:
        arcpy.Delete_management(out_table)
        arcpy.Delete_management(out_table_csv)
        arcpy.Delete_management(out_p2r)
    

# normalize school enrollment data
maz_remm_data['ENROL_ELEM'] = (maz_remm_data['ENROL_ELEM']/maz_remm_data['population']).replace(np.inf, 0)
maz_remm_data['ENROL_MIDL'] = (maz_remm_data['ENROL_MIDL']/maz_remm_data['population']).replace(np.inf, 0)
maz_remm_data['ENROL_HIGH'] = (maz_remm_data['ENROL_HIGH']/maz_remm_data['population']).replace(np.inf, 0)

# normalize income group data
totalpop = maz_remm_data['INC1'] + maz_remm_data['INC2'] + maz_remm_data['INC3'] + maz_remm_data['INC4']
maz_remm_data['INC1'] = (maz_remm_data['INC1']/totalpop).replace(np.inf, 0)
maz_remm_data['INC2'] = (maz_remm_data['INC2']/totalpop).replace(np.inf, 0)
maz_remm_data['INC3'] = (maz_remm_data['INC3']/totalpop).replace(np.inf, 0)
maz_remm_data['INC4'] = (maz_remm_data['INC4']/totalpop).replace(np.inf, 0)

# Free up memory
del taz_se_data
del taz_se_data2
del zonal_table


#===================
# Other datasets
#===================

print("Computing attraction attributes...")


#-------------------
# Parks Score
#-------------------
"""
1:  Acreage > 10
2:  5 < Acreage < 10
3:  Acreage < 5
"""

print("Working on park score...")
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
fieldmappings.addTable(microzones)
fieldmappings.addTable(parks_lyr)
modFieldMapping(fieldmappings, 'PARK_SCORE', 'max')

maz_park_join = os.path.join(temp_dir, "maz_park_join.shp")
arcpy.SpatialJoin_analysis(microzones, parks_lyr, maz_park_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_park_join_df = pd.DataFrame.spatial.from_featureclass(maz_park_join)
maz_park_join_df =  maz_park_join_df[['zone_id', "PARK_SCORE"]].copy()
maz_remm_data = maz_remm_data.merge(maz_park_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')


#-------------------
# Parks Area
#-------------------

print("Working on park area...")

# identity
maz_park_identity = os.path.join(temp_dir, "maz_park_identity.shp")
parks_separated = arcpy.Identity_analysis(parks_lyr, microzones, maz_park_identity)

# calculate area of each separated park - sq. meters
arcpy.AddField_management(parks_separated, field_name="PARK_AREA", field_type='LONG')
with arcpy.da.UpdateCursor(parks_separated, ['Park_Area', 'SHAPE@AREA']) as cursor:
    for row in cursor:
        row[0] = row[1]
        cursor.updateRow(row)

park_points = os.path.join(temp_dir, "park_pts.shp")   
arcpy.FeatureToPoint_management(parks_separated,park_points)

maz_park_join2 = os.path.join(temp_dir, "maz_park_join2.shp")                                

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(park_points)
modFieldMapping(fieldmappings, "Park_Area", 'sum')

arcpy.SpatialJoin_analysis(microzones, park_points, maz_park_join2, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park area field back to full table
maz_park_join2_df = pd.DataFrame.spatial.from_featureclass(maz_park_join2)
maz_park_join2_df =  maz_park_join2_df[['zone_id', "PARK_AREA"]].copy()
maz_remm_data = maz_remm_data.merge(maz_park_join2_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')



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
fieldmappings.addTable(microzones)
fieldmappings.addTable(schools_lyr)
modFieldMapping(fieldmappings, "SCHOOL_CD", 'max')

maz_school_join = os.path.join(temp_dir, "maz_schools_join.shp")
arcpy.SpatialJoin_analysis(microzones, schools, maz_school_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge school score field back to full table
maz_school_join_df = pd.DataFrame.spatial.from_featureclass(maz_school_join)
maz_school_join_df =  maz_school_join_df[['zone_id', "SCHOOL_CD"]].copy()
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
fieldmappings.addTable(microzones)
fieldmappings.addTable(enrollment_lyr)
modFieldMapping(fieldmappings, 'Enrollment', 'max')

maz_ce_join = os.path.join(temp_dir, "maz_ce_join.shp")
arcpy.SpatialJoin_analysis(microzones, enrollment_lyr, maz_ce_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge college enrollment field back to full table
maz_ce_join_df = pd.DataFrame.spatial.from_featureclass(maz_ce_join) # Might have to fill in zeroes
maz_ce_join_df =  maz_ce_join_df[['zone_id', 'Enrollment']].copy()
maz_ce_join_df.columns = ['zone_id', 'coll_enrol']
maz_remm_data = maz_remm_data.merge(maz_ce_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#-------------------
# mountain bike and hiking trailheads
#-------------------
"""
  3) most attractive 2) moderately attractive 1) least attractive
    
"""

print("Working on mtn bike and hiking trail heads...")
mtn_bike_hike_lyr =  arcpy.MakeFeatureLayer_management(mtn_bike_hike, 'mtn_bike_hike')

# use spatial join to get trail head score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(mtn_bike_hike_lyr)
modFieldMapping(fieldmappings, 'mtbh_score', 'max')

maz_mtbh_join = os.path.join(temp_dir, "maz_mtbh_join.shp")
arcpy.SpatialJoin_analysis(microzones, mtn_bike_hike_lyr, maz_mtbh_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_mtbh_join_df = pd.DataFrame.spatial.from_featureclass(maz_mtbh_join) # Might have to fill in zeroes
maz_mtbh_join_df =  maz_mtbh_join_df[['zone_id', 'mtbh_score']].copy()
maz_remm_data = maz_remm_data.merge(maz_mtbh_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#-------------------
# long distance rec
#-------------------
"""
  3) most attractive 2) moderately attractive 1) least attractive
    
"""

print("Working on long distance rec trail heads...")
long_dist_rec_lyr =  arcpy.MakeFeatureLayer_management(long_dist_rec, 'long_dist_rec')

# use spatial join to get trail head score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(long_dist_rec_lyr)
modFieldMapping(fieldmappings, 'ldr_score', 'max')

maz_ldr_join = os.path.join(temp_dir, "maz_ldr_join.shp")
arcpy.SpatialJoin_analysis(microzones, long_dist_rec_lyr, maz_ldr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_ldr_join_df = pd.DataFrame.spatial.from_featureclass(maz_ldr_join) # Might have to fill in zeroes
maz_ldr_join_df =  maz_ldr_join_df[['zone_id', 'ldr_score']].copy()
maz_remm_data = maz_remm_data.merge(maz_ldr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')



#-------------------
# trailheads 
#-------------------
"""
  3) most attractive 2) moderately attractive 1) least attractive
    
"""

print("Working on trail heads...")
trail_heads_lyr =  arcpy.MakeFeatureLayer_management(trail_heads, 'trail_heads')

# use spatial join to get trail head score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(trail_heads_lyr)
modFieldMapping(fieldmappings, 'TH_SCORE', 'max')

maz_th_join = os.path.join(temp_dir, "maz_th_join.shp")
arcpy.SpatialJoin_analysis(microzones, trail_heads_lyr, maz_th_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_th_join_df = pd.DataFrame.spatial.from_featureclass(maz_th_join) # Might have to fill in zeroes
maz_th_join_df =  maz_th_join_df[['zone_id', 'TH_SCORE']].copy()
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
fieldmappings.addTable(microzones)
fieldmappings.addTable(cr_lyr)
modFieldMapping(fieldmappings, 'COMM_RAIL', 'max')

maz_cr_join = os.path.join(temp_dir, "maz_cr_join.shp")
arcpy.SpatialJoin_analysis(microzones, cr_lyr, maz_cr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_cr_join_df = pd.DataFrame.spatial.from_featureclass(maz_cr_join) # Might have to fill in zeroes
maz_cr_join_df =  maz_cr_join_df[['zone_id', 'COMM_RAIL']].copy()
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
fieldmappings.addTable(microzones)
fieldmappings.addTable(lr_lyr)
modFieldMapping(fieldmappings, 'LIGHT_RAIL', 'max')

maz_lr_join = os.path.join(temp_dir, "maz_lr_join.shp")
arcpy.SpatialJoin_analysis(microzones, lr_lyr, maz_lr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_lr_join_df = pd.DataFrame.spatial.from_featureclass(maz_lr_join) # Might have to fill in zeroes
maz_lr_join_df =  maz_lr_join_df[['zone_id', 'LIGHT_RAIL']].copy()
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
zonal_table =  zonal_table[['zone_id', 'MEAN']].copy()
zonal_table.columns = ['zone_id', field]
zonal_table['zone_id'] = zonal_table['zone_id'].astype(str)
maz_remm_data = maz_remm_data.merge(zonal_table, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')


#----------------------
# Mixed-Use 
#----------------------

print("Working on mixed use...")

# create mixed use attribute (fill NAs and infinites from dividing by 0, with 0)
maz_remm_data['MIXED_USE'] = ((maz_remm_data['households'] * maz_remm_data['jobs_total']) / (maz_remm_data['households'] + maz_remm_data['jobs_total'])).replace(np.inf, 0)
maz_remm_data['MIXED_USE'].fillna(0, inplace=True)

#-------------------
# Bikeshare
#-------------------

"""
general attractiveness of greenbike kiosk areas 
 1) least attractive 3) somewhat attractive 5) most attractive
    
"""

print("Working on bike share...")
bike_kiosks_lyr =  arcpy.MakeFeatureLayer_management(bike_kiosks, 'bike_kiosks')

# use spatial join to get trail head score on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(bike_kiosks_lyr)
modFieldMapping(fieldmappings, 'bike_share', 'max')

maz_bs_join = os.path.join(temp_dir, "maz_bs_join.shp")
arcpy.SpatialJoin_analysis(microzones, bike_kiosks_lyr, maz_bs_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_bs_join_df = pd.DataFrame.spatial.from_featureclass(maz_bs_join) # Might have to fill in zeroes
maz_bs_join_df =  maz_bs_join_df[['zone_id', 'bike_share']]
maz_remm_data = maz_remm_data.merge(maz_bs_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#----------------------
# Industrial Districts
#----------------------

"""
  1) zone is within industrial districts 0 ) not within industrial districts
"""

print("Working on industrial districts...")
industrial_districts_lyr =  arcpy.MakeFeatureLayer_management(industrial_districts, 'industrial_districts')

# use spatial join to get school code on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(industrial_districts_lyr)
modFieldMapping(fieldmappings, 'industrial', 'max')

maz_ind_join = os.path.join(temp_dir, "maz_ind_join.shp")
arcpy.SpatialJoin_analysis(microzones, industrial_districts_lyr, maz_ind_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park score field back to full table
maz_ind_join_df = pd.DataFrame.spatial.from_featureclass(maz_ind_join) # Might have to fill in zeroes
maz_ind_join_df =  maz_ind_join_df[['zone_id', 'industrial']]
maz_remm_data = maz_remm_data.merge(maz_ind_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#----------------------
# Centroid Node 
#----------------------

print("Working on node centroids...")

# add node ID to zones these ID will be from the node/link output
maz_centroids = os.path.join(temp_dir, "maz_centroids.shp")   
arcpy.FeatureToPoint_management(microzones, maz_centroids)

arcpy.Near_analysis(maz_centroids, nodes)

# merge centroid field back to full table
maz_centroid_join_df = pd.DataFrame.spatial.from_featureclass(maz_centroids) # Might have to fill in zeroes
maz_centroid_join_df =  maz_centroid_join_df[['zone_id', 'NEAR_FID']]
maz_centroid_join_df.columns = ['zone_id', 'NODE_ID']
maz_remm_data = maz_remm_data.merge(maz_centroid_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

#-----------------------------------
# Summarize Bike Path and Bike Lane
#-----------------------------------

# create output gdb
gdb = os.path.join(temp_dir, "bike_network_sums.gdb")
if not arcpy.Exists(gdb):
    arcpy.CreateFileGDB_management(os.path.dirname(gdb), os.path.basename(gdb))

network_lyr = arcpy.MakeFeatureLayer_management(network, 'network_lyr')
arcpy.SelectLayerByAttribute_management(network_lyr, 'CLEAR_SELECTION')

# filter network for bike lanes and paths
query1 = (""" Bike_Lane = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query1)
bike_lanes = arcpy.FeatureClassToFeatureClass_conversion(network_lyr, gdb, 'bike_lanes')
bike_lanes_lyr = arcpy.MakeFeatureLayer_management(bike_lanes, 'bike_lanes_lyr')

query2 = (""" Bike_Path = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query2)
bike_paths = arcpy.FeatureClassToFeatureClass_conversion(network_lyr, gdb, 'bike_paths')
bike_paths_lyr =  arcpy.MakeFeatureLayer_management(bike_paths, 'bike_paths_lyr')

# buffer zones out to .25 miles
buffer = arcpy.Buffer_analysis(microzones, os.path.join(gdb, 'buff_zones'), '.25 Miles')

# get length of bike paths within .25 miles of each buffered zone
print("summarizing bike lane length...")
#bike_lane_sum = os.path.join(gdb, 'bike_lane_sum')
#arcpy.SummarizeWithin_analysis(buffer, bike_lanes_lyr, bike_lane_sum, keep_all_polygons='KEEP_ALL', sum_shape='ADD_SHAPE_SUM',shape_unit='MILES')
#bike_lane_sum_df = pd.DataFrame.spatial.from_featureclass(bike_lane_sum)[['zone_id', 'sum_length_mil']]
#bike_lane_sum_df.columns = ['zone_id', 'bklane_len']

#zones = arcpy.FeatureClassToFeatureClass_conversion(microzones, gdb, 'zones')
#arcpy.AddField_management(zones, field_name="PARTS", field_type='float')
#arcpy.AddField_management(zones, field_name="RINGS", field_type='float')
#fields = ["shape@", 'PARTS', 'RINGS']
#with arcpy.da.UpdateCursor(zones, fields) as cursor:
    #for row in cursor:
        #shape = row[0]
        #parts = shape.partCount
        #rings = shape.boundary().partCount   
        #row[1] = parts
        #row[2] = rings
        #cursor.updateRow(row)

#zone_explode = arcpy.MultipartToSinglepart_management (zones, os.path.join(gdb,'zone_explode'))
#buffer = arcpy.Buffer_analysis(zone_explode, os.path.join(gdb, 'buff_zones'), '.25 Miles')
#arcpy.SummarizeWithin_analysis(buffer, bike_lanes, os.path.join(gdb,'sum_bike_lanes'), keep_all_polygons='KEEP_ALL', sum_shape='ADD_SHAPE_SUM',shape_unit='MILES')


##copyfeatures
#zones = arcpy.FeatureClassToFeatureClass_conversion(microzones, gdb, 'zones')

##add lane/path sum fields
arcpy.AddField_management(zones, field_name="bklane_len", field_type='float')
arcpy.AddField_management(zones, field_name="bkpath_len", field_type='float')

#update cursor (in_memory; shapefiles would also be deletable
#buffer then summarize within?


buffdist = 0.25
count = arcpy.GetCount_management(zones)
progress = 1
with arcpy.da.UpdateCursor(zones, ['SHAPE@','bklane_len','bkpath_len', 'OID@']) as UpdateCursor:
    for UpdateRow in UpdateCursor:
        
        print('working on zone {} of {}'.format(progress, count))
        
        # buffer
        buffer = arcpy.Buffer_analysis(UpdateRow[0], 'in_memory\\temp_buff', '{} Miles'.format(buffdist))
        
        #-----------
        # bike lane
        #-----------
        
        # clip
        bl_clip = arcpy.Clip_analysis(bike_lanes, buffer, 'in_memory\\temp_bl_clip')
        
        # get length in miles (meters -> miles)
        total_lane = 0
        with arcpy.da.SearchCursor(bl_clip, ['SHAPE@LENGTH']) as cursor:
            for row in cursor:
                total_lane = total_lane + row[0] * 0.000621371       
        
        # set value
        UpdateRow[1] = total_lane
        arcpy.management.Delete(bl_clip)
        
        #---------------
        # bike path
        #---------------
        
        # clip
        bp_clip = arcpy.Clip_analysis(bike_paths, buffer, 'in_memory\\temp_bp_clip')
        
        # get length in miles (meters -> miles)
        total_path = 0
        with arcpy.da.SearchCursor(bp_clip, ['SHAPE@LENGTH']) as cursor:
            for row in cursor:
                total_path = total_path + row[0] * 0.000621371       
        
        # set value
        UpdateRow[2] = total_path
        arcpy.management.Delete(bp_clip)        
        
        # update row
        arcpy.management.Delete(buffer)
        progress = progress + 1
        
        try:
            UpdateCursor.updateRow(UpdateRow)
        except:
            print('there was a problem with OID: {}'.format(row[3]))






# get length of bike paths within .25 miles of each buffered zone
print("summarizing bike path length...")
bike_path_sum = os.path.join(gdb, 'bike_path_sum')
arcpy.SummarizeWithin_analysis(buffer, bike_paths_lyr, bike_path_sum, keep_all_polygons='KEEP_ALL', sum_shape='ADD_SHAPE_SUM',shape_unit='MILES')
bike_path_sum_df = pd.DataFrame.spatial.from_featureclass(bike_path_sum)[['zone_id', 'sum_length_mil']]
bike_path_sum_df.columns = ['zone_id', 'bkpath_len']

# merge the tables with the full data table
bk_path_lane = bike_lane_sum_df.merge(bike_path_sum_df, left_on='zone_id', right_on='zone_id', how='inner')
maz_remm_data = maz_remm_data.merge(bk_path_lane, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

del gdb
del network_lyr
del bike_lanes
del bike_paths
del bike_path_sum_df
del bike_lane_sum_df

#================================
# WRAP-UP
#================================ 

# fill NAs where necessary
for field in list(maz_remm_data.columns):
    if field not in ['Shape']:
        maz_remm_data[field].fillna(0, inplace=True)

# final export
final_zones = os.path.join(temp_dir, "microzones.shp")
maz_remm_data.spatial.to_featureclass(location=final_zones)

# add area  square miles
print("Working area square miles...")
arcpy.AddField_management(final_zones, field_name="area_sqmil", field_type='FLOAT')
arcpy.CalculateGeometryAttributes_management(final_zones, [["area_sqmil", "AREA"]], area_unit='SQUARE_MILES_US')

# create csv version
final_zones = pd.DataFrame.spatial.from_featureclass(final_zones)
del final_zones['SHAPE']
del final_zones['Id']
del final_zones['FID']
names_lowercase = [att.lower() for att in list(final_zones.columns)]
final_zones.columns = names_lowercase
final_zones['zone_id'] = final_zones.index
final_zones.to_csv(os.path.join(temp_dir, 'microzones.csv'), index=False)
#arcpy.TableToTable_conversion(final_zones, temp_dir, 'microzones.csv')

print('Zones complete!!')

#=====================================
# Clean up
#=====================================

print('Clean-up')
arcpy.Delete_management(filled_zones)
arcpy.Delete_management(zones_layer) 
arcpy.Delete_management(zones_layer2) 
arcpy.Delete_management(merged_roads)  
arcpy.Delete_management(microzones_geom)
arcpy.Delete_management(microzones_no_rings) 
arcpy.Delete_management(microzones_rings_erased) 
arcpy.Delete_management(prelim_zones) 
arcpy.Delete_management(roads_clipped)
arcpy.Delete_management(taz_dissolved) 
arcpy.Delete_management(taz_outline)
arcpy.Delete_management(zones_eliminated) 
arcpy.Delete_management(zones_eliminated2)
arcpy.Delete_management(out_table)
arcpy.Delete_management(out_table_csv)
arcpy.Delete_management(out_p2r)
arcpy.Delete_management(maz_ce_join)
arcpy.Delete_management(maz_centroids)
arcpy.Delete_management(maz_erased)
arcpy.Delete_management(maz_clipped)
arcpy.Delete_management(maz_and_canyons)
arcpy.Delete_management(target_features)
arcpy.Delete_management(maz_cr_join)
arcpy.Delete_management(maz_bs_join)
arcpy.Delete_management(maz_ind_join)
arcpy.Delete_management(maz_lr_join)
arcpy.Delete_management(maz_th_join)
arcpy.Delete_management(maz_mtbh_join)
arcpy.Delete_management(maz_ldr_join)
arcpy.Delete_management(merged_zones)
arcpy.Delete_management(out_taz_data)
arcpy.Delete_management(output_features)
arcpy.Delete_management(maz_park_identity)
arcpy.Delete_management(maz_park_join)
arcpy.Delete_management(maz_park_join2)
arcpy.Delete_management(parcels_aggd_buildings)
arcpy.Delete_management(maz_school_join)
arcpy.Delete_management(pts_aggd_buildings)
arcpy.Delete_management(park_points)
arcpy.Delete_management(maz_output)
arcpy.Delete_management(microzones)


del cr_lyr
del cursor
del enrollment_lyr
del fieldmappings
del filled_zones
del long_dist_rec_lyr
del lr_lyr
del maz_and_canyons
del maz_clipped
del maz_erased
del maz_ce_join_df
del maz_cr_join_df
del maz_lr_join_df
del maz_park_join_df
del merged_roads
del microzones
del microzones_geom
del microzones_no_rings
del microzones_rings_erased
del mtn_bike_hike_lyr
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
del taz_se_data3
#del trail_heads_lyr
del zonal_table
del zones_eliminated
del zones_eliminated2
del zones_layer
del zones_layer2






