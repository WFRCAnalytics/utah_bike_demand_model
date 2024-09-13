# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 12:22:01 2020

@author: jreynolds

Creates Micro Traffic Analysis Zones (AKA Microzones or MAZs) from Utah roads network.
Also distributes attributes from REMM, TDM, UGRC
Requires data set folder
"""

import arcpy
import os
import yaml
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import numpy as np
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
arcpy.env.parallelProcessingFactor = "90%"

#====================
# FUNCTIONS
#====================

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

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

def fill_na_sedf(df_with_shape_column, fill_value=0):
    if 'SHAPE' in list(df_with_shape_column.columns):
        df = df_with_shape_column.copy()
        shape_column = df['SHAPE'].copy()
        del df['SHAPE']
        return df.fillna(fill_value).merge(shape_column,left_index=True, right_index=True, how='inner')
    else:
        raise Exception("Dataframe does not include 'SHAPE' column")


#==========================
# Inputs
#==========================
 
config = load_yaml('Create_Microzones.yaml')

# From REMM
remm_parcel_se = config['remm_parcel_se']
remm_parcels = config['remm_parcels']

# From TDM
taz_polygons = config['taz_polygons']
taz_se_data = config['taz_se_data']
taz_se_data2 = config['taz_life_cycle']
taz_se_data3 = config['taz_marginal_income']

# From Other sources
microzones = config['microzones']
roads= config['roads']
trail_heads = config['trail_heads']
long_dist_rec = config['long_dist_rec']
mtn_bike_hike = config['mtn_bike_hike']
schools = config['schools']
light_rail_stops = config['light_rail_stops']
parks = config['parks']
commuter_rail_stops = config['commuter_rail_stops']
enrollment_shp = config['enrollment_shp']
enrollment_data = config['enrollment_data']
enrollment_year = config['enrollment_year']
group_quarters = config['group_quarters']
industrial_districts = config['industrial_districts']
bike_kiosks = config['bike_kiosks']
nodes = config['nodes']
network = config['network']


#=====================================
# Data and environment prep
#=====================================

outputs = ['.\\Outputs', 'scratch.gdb', "microzones.gdb"]
if not os.path.exists(outputs[0]):
    os.makedirs(outputs[0])

scratch_gdb = os.path.join(outputs[0], outputs[1])
microzones_gdb = os.path.join(outputs[0], outputs[2])
if not arcpy.Exists(scratch_gdb): arcpy.CreateFileGDB_management(outputs[0], outputs[1])
if not arcpy.Exists(microzones_gdb): arcpy.CreateFileGDB_management(outputs[0], outputs[2])

delete_intermediate_layers = True

    

#==========================
# Zone Prep
#========================== 

print('Creating microzone points...')
microzone_pts = os.path.join(scratch_gdb,'_00_microzone_pts')
arcpy.management.FeatureToPoint(microzones, microzone_pts, "CENTROID")
microzones_df =  pd.DataFrame.spatial.from_featureclass(microzones)[['zone_id', 'area_sqmil', 'SHAPE']].copy()

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

print('Processing parcel level SE data...')

# load csvs as pandas dataframes
buildings = pd.read_csv(remm_parcel_se)

# filter columns
# buildings_filtered = buildings[['parcel_id', 'parcel_acres','residential_units', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']].copy()
buildings_filtered = buildings[['parcel_id', 'residential_units', 'households', 'hhpop', 'jobs_accom_food', 'jobs_gov_edu', 'jobs_health', 'jobs_manuf', 'jobs_office', 'jobs_other', 'jobs_retail', 'jobs_wholesale']].copy()
buildings_filtered.rename({'residential_units':'residentia','hhpop':'population', 'jobs_accom_food':'jobs1', 'jobs_gov_edu':'jobs3', 'jobs_health':'jobs4', 
                           'jobs_manuf':'jobs5', 'jobs_office':'jobs6', 'jobs_other':'jobs7', 'jobs_retail':'jobs9', 'jobs_wholesale':'jobs10'}, 
                           axis=1, inplace=True)

# read in parcel features
parcels = pd.DataFrame.spatial.from_featureclass(remm_parcels)
parcels = parcels[['parcel_id', 'acres', 'SHAPE']].copy()

#  join to aggregated buildings
# parcels_join = parcels.merge(buildings_grouped, left_on = 'parcel_id', right_on = 'parcel_id' , how = 'inner')
parcels_join = parcels.merge(buildings_filtered, left_on = 'parcel_id', right_on = 'parcel_id' , how = 'left')
parcels_join = fill_na_sedf(parcels_join)

# export to shape
parcels_aggd_buildings = os.path.join(scratch_gdb, "_01_parcels_with_aggd_buildings_data")
parcels_join.spatial.to_featureclass(location=parcels_aggd_buildings, sanitize_columns=False)
microzone_parcel_apportion = os.path.join(scratch_gdb, '_02_maz_parcels_app')


arcpy.analysis.ApportionPolygon(parcels_aggd_buildings, 
                            ['residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10'], 
                            microzones, 
                            microzone_parcel_apportion, 'AREA')


# Select fields
maz_remm_data = pd.DataFrame.spatial.from_featureclass(microzone_parcel_apportion)
maz_remm_data = maz_remm_data[['zone_id', 'residentia', 'households', 'population', 'jobs1', 'jobs3', 'jobs4', 'jobs5', 'jobs6', 'jobs7', 'jobs9', 'jobs10']]
# create total jobs attribute
maz_remm_data['jobs_total'] = maz_remm_data['jobs1']+ maz_remm_data['jobs3'] + maz_remm_data['jobs4'] +  maz_remm_data['jobs5'] + maz_remm_data['jobs6'] +  maz_remm_data['jobs7']

microzones_df = microzones_df.merge(maz_remm_data, on='zone_id', how='left')
print('maz_remm_data',microzones_df.shape)
# Free up memory
del maz_remm_data
del buildings
del buildings_filtered
del parcels
del parcels_join



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

# Read in taz level se data]
taz_se_data = pd.read_csv(taz_se_data).rename({';TAZID':'TAZID'}, axis=1).drop(['AVGINCOME'], axis=1)

# Read in taz level life cycle/age data and recreate COTAZID field
taz_se_data2 = pd.read_csv(taz_se_data2).rename({'Z':'TAZID'}, axis=1)

# Read in taz level income distribution data and recreate COTAZID field
taz_se_data3 = pd.read_csv(taz_se_data3).rename({'Z':'TAZID'}, axis=1)

# read in taz polygons
taz_geometry = pd.DataFrame.spatial.from_featureclass(taz_polygons)[['SA_TAZID', 'SHAPE']].rename({'SA_TAZID':'TAZID'}, axis=1)

# join se data to taz polygons 
taz_join = taz_geometry.merge(taz_se_data, on='TAZID',how = 'left')
taz_join2 = taz_join.merge(taz_se_data2.drop(['HHPOP'], axis=1), on='TAZID' , how = 'left')
taz_join3 = taz_join2.merge(taz_se_data3, on='TAZID' , how = 'left')


# filter to desired columns
taz_join_filt = taz_join3[['TAZID', 'SHAPE', 'HHPOP','AVGINCOME','Enrol_Elem', 'Enrol_Midl','Enrol_High', 'POP_LC1', 'POP_LC2', 'POP_LC3', 'HHSIZE_LC1', 'HHSIZE_LC2', 'HHSIZE_LC3', 'PCT_POPLC1', 'PCT_POPLC2', 'PCT_POPLC3', 'PCT_AG1', 'PCT_AG2', 'PCT_AG3', 'INC1', 'INC2', 'INC3', 'INC4']].copy()

# export taz data to shape
out_taz_data = os.path.join(scratch_gdb, "_03_taz_with_se_data")
taz_join_filt['AVGINCOME'] = taz_join_filt['AVGINCOME'].astype('Float64')
taz_join_filt['Enrol_Elem'] = taz_join_filt['Enrol_Elem'].astype('Float64')
taz_join_filt['Enrol_Midl'] = taz_join_filt['Enrol_Midl'].astype('Float64')
taz_join_filt['Enrol_High'] = taz_join_filt['Enrol_High'].astype('Float64')
taz_join_filt.spatial.to_featureclass(location=out_taz_data, sanitize_columns=False)

# Distribute attributes larger TAZ attributes to MAZ

count_columns = ['HHPOP','Enrol_Elem', 'Enrol_Midl','Enrol_High', 'INC1', 'INC2', 'INC3', 'INC4']
taz_apportion = os.path.join(scratch_gdb, '_04_taz_se_apportion')

arcpy.analysis.ApportionPolygon(out_taz_data, 
                            count_columns, 
                            microzones, 
                            taz_apportion, 'AREA')


taz_apportion_df = pd.DataFrame.spatial.from_featureclass(taz_apportion)

# non count columns
non_count_columns = ['AVGINCOME', 'HHSIZE_LC1', 'HHSIZE_LC2', 'HHSIZE_LC3', 'PCT_POPLC1', 'PCT_POPLC2', 'PCT_POPLC3', 'PCT_AG1', 'PCT_AG2', 'PCT_AG3']
target_features = microzone_pts
join_features = out_taz_data
microzone_taz_join = os.path.join(scratch_gdb, "_05_microzone_taz_join")

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(target_features)
fieldmappings.addTable(join_features)

# run the spatial join, use 'Join_Count' for number of units
arcpy.SpatialJoin_analysis(target_features, join_features, microzone_taz_join,'JOIN_ONE_TO_ONE', "KEEP_ALL", 
                           fieldmappings, "INTERSECT")

del fieldmappings

taz_sj_df = pd.DataFrame.spatial.from_featureclass(microzone_taz_join)[['zone_id']+ non_count_columns]
microzones_df = microzones_df.merge(taz_sj_df[['zone_id'] + non_count_columns], on='zone_id', how='left')
print(microzones_df.shape)
del taz_sj_df

    
microzones_df = microzones_df.merge(taz_apportion_df[['zone_id', 'HHPOP','Enrol_Elem', 'Enrol_Midl', 'Enrol_High', 'INC1', 'INC2', 'INC3', 'INC4']], on='zone_id', how='left')
del taz_apportion_df

# normalize school enrollment data
microzones_df['Enrol_Elem'] = (microzones_df['Enrol_Elem']/microzones_df['HHPOP']).replace(np.inf, 0)
microzones_df['Enrol_Midl'] = (microzones_df['Enrol_Midl']/microzones_df['HHPOP']).replace(np.inf, 0)
microzones_df['Enrol_High'] = (microzones_df['Enrol_High']/microzones_df['HHPOP']).replace(np.inf, 0)

# normalize income group data
microzones_df['INC1'] = (microzones_df['INC1']/microzones_df['HHPOP']).replace(np.inf, 0)
microzones_df['INC2'] = (microzones_df['INC2']/microzones_df['HHPOP']).replace(np.inf, 0)
microzones_df['INC3'] = (microzones_df['INC3']/microzones_df['HHPOP']).replace(np.inf, 0)
microzones_df['INC4'] = (microzones_df['INC4']/microzones_df['HHPOP']).replace(np.inf, 0)

# Free up memory
del taz_se_data
del taz_se_data2


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

# use spatial join to get park score on to microzones (maximum score in zone will be used)
target_features = microzone_pts
join_features = parks_lyr
microzone_parks_join = os.path.join(scratch_gdb, "_06_microzone_parks_join")

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(target_features)
fieldmappings.addTable(join_features)
modFieldMapping(fieldmappings, 'PARK_SCORE', 'max')

arcpy.SpatialJoin_analysis(target_features, parks_lyr, microzone_parks_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del parks_lyr

# merge park score field back to full table
maz_park_join_df = pd.DataFrame.spatial.from_featureclass(microzone_parks_join)
maz_park_join_df =  maz_park_join_df[['zone_id', "PARK_SCORE"]].copy()
microzones_df = microzones_df.merge(maz_park_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_park_join_df

#-------------------
# Parks Area
#-------------------

print("Working on park area...")

# identity
maz_park_identity = os.path.join(scratch_gdb, "_07_maz_park_identity")
parks_separated = arcpy.Identity_analysis(parks, microzones, maz_park_identity)

# calculate area of each separated park - sq. meters
arcpy.AddField_management(parks_separated, field_name="PARK_AREA", field_type='LONG')
with arcpy.da.UpdateCursor(parks_separated, ['Park_Area', 'SHAPE@AREA']) as cursor:
    for row in cursor:
        row[0] = row[1]
        cursor.updateRow(row)

park_points = os.path.join(scratch_gdb, "_08_park_pts")   
arcpy.FeatureToPoint_management(parks_separated,park_points)
maz_park_join2 = os.path.join(scratch_gdb, "_09_maz_park_join2")                                
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(park_points)
modFieldMapping(fieldmappings, "Park_Area", 'sum')

arcpy.SpatialJoin_analysis(microzones, park_points, maz_park_join2, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")

# merge park area field back to full table
maz_park_join2_df = pd.DataFrame.spatial.from_featureclass(maz_park_join2)
maz_park_join2_df =  maz_park_join2_df[['zone_id', "PARK_AREA"]].copy()
microzones_df = microzones_df.merge(maz_park_join2_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')
del maz_park_join2_df


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


# use spatial join to get school code on to microzones (if multiple scores present, maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(schools_lyr)
modFieldMapping(fieldmappings, "SCHOOL_CD", 'max')

maz_school_join = os.path.join(scratch_gdb, "_10_maz_schools_join")
arcpy.SpatialJoin_analysis(microzones, schools, maz_school_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del schools_lyr

# merge school score field back to full table
maz_school_join_df = pd.DataFrame.spatial.from_featureclass(maz_school_join)
maz_school_join_df =  maz_school_join_df[['zone_id', "SCHOOL_CD"]].copy()
microzones_df = microzones_df.merge(maz_school_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_school_join_df
#-------------------
# College Enrollment
#-------------------
"""
  Enrollment count from TDM Trip table control except LDS Business College and Westminster

"""
print("Working on college enrollment...")
enrollment_df = pd.DataFrame.spatial.from_featureclass(enrollment_shp)


enrollment_data_df = pd.read_csv(enrollment_data)
enrollment_data_df = enrollment_data_df[enrollment_data_df[';Year']==enrollment_year].copy()
enrollment_data_df = enrollment_data_df.transpose().reset_index()[1:]
enrollment_data_df.columns = ['SHORTNAME', enrollment_year]
enrollment_df = enrollment_df.merge(enrollment_data_df, on='SHORTNAME')
enrollment_df = enrollment_df[enrollment_df['USE']==1].copy()
enrollment_output = os.path.join(scratch_gdb, f'_11_college_enrollment_{enrollment_year}')
enrollment_df.spatial.to_featureclass(location=enrollment_output,sanitize_columns=False) 
enrollment_lyr =  arcpy.MakeFeatureLayer_management(enrollment_output, 'college_enrollment')

# use spatial join to get enrollment on to microzones (maximum score in zone will be used)
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzones)
fieldmappings.addTable(enrollment_lyr)
modFieldMapping(fieldmappings, 'Enrollment', 'max')

maz_ce_join = os.path.join(scratch_gdb, "_12_maz_ce_join")
arcpy.SpatialJoin_analysis(microzones, enrollment_lyr, maz_ce_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del enrollment_lyr

# merge college enrollment field back to full table
maz_ce_join_df = pd.DataFrame.spatial.from_featureclass(maz_ce_join) # Might have to fill in zeroes
maz_ce_join_df =  maz_ce_join_df[['zone_id', 'Enrollment']].copy()
maz_ce_join_df.columns = ['zone_id', 'coll_enrol']
microzones_df = microzones_df.merge(maz_ce_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_ce_join_df
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

maz_mtbh_join = os.path.join(scratch_gdb, "_13_maz_mtbh_join")
arcpy.SpatialJoin_analysis(microzones, mtn_bike_hike_lyr, maz_mtbh_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del mtn_bike_hike_lyr

# merge park score field back to full table
maz_mtbh_join_df = pd.DataFrame.spatial.from_featureclass(maz_mtbh_join) # Might have to fill in zeroes
maz_mtbh_join_df =  maz_mtbh_join_df[['zone_id', 'mtbh_score']].copy()
microzones_df = microzones_df.merge(maz_mtbh_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_mtbh_join_df

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

maz_ldr_join = os.path.join(scratch_gdb, "_14_maz_ldr_join")
arcpy.SpatialJoin_analysis(microzones, long_dist_rec_lyr, maz_ldr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del long_dist_rec_lyr

# merge park score field back to full table
maz_ldr_join_df = pd.DataFrame.spatial.from_featureclass(maz_ldr_join) # Might have to fill in zeroes
maz_ldr_join_df =  maz_ldr_join_df[['zone_id', 'ldr_score']].copy()
microzones_df = microzones_df.merge(maz_ldr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_ldr_join_df


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

maz_th_join = os.path.join(scratch_gdb, "_15_maz_th_join")
arcpy.SpatialJoin_analysis(microzones, trail_heads_lyr, maz_th_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del trail_heads_lyr

# merge park score field back to full table
maz_th_join_df = pd.DataFrame.spatial.from_featureclass(maz_th_join) # Might have to fill in zeroes
maz_th_join_df =  maz_th_join_df[['zone_id', 'TH_SCORE']].copy()
microzones_df = microzones_df.merge(maz_th_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')
del maz_th_join_df


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

maz_cr_join = os.path.join(scratch_gdb, "_16_maz_cr_join")
arcpy.SpatialJoin_analysis(microzones, cr_lyr, maz_cr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del cr_lyr

# merge park score field back to full table
maz_cr_join_df = pd.DataFrame.spatial.from_featureclass(maz_cr_join) # Might have to fill in zeroes
maz_cr_join_df =  maz_cr_join_df[['zone_id', 'COMM_RAIL']].copy()
microzones_df = microzones_df.merge(maz_cr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')
del maz_cr_join_df


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

maz_lr_join = os.path.join(scratch_gdb, "_17_maz_lr_join")
arcpy.SpatialJoin_analysis(microzones, lr_lyr, maz_lr_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del lr_lyr

# merge park score field back to full table
maz_lr_join_df = pd.DataFrame.spatial.from_featureclass(maz_lr_join) # Might have to fill in zeroes
maz_lr_join_df =  maz_lr_join_df[['zone_id', 'LIGHT_RAIL']].copy()
microzones_df = microzones_df.merge(maz_lr_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')

del maz_lr_join_df

#----------------------
# Group quarters
#----------------------

print("Working on group quarters data...")

# distribute gqu_ratio field - group quarters (university) / population
field = 'GQU_RATIO'

# apportion group quarters and totalpop to zones
# load result into pandas
# calculate gqu ratio there

gq_columns = ['GQPOP', 'TOTALPOP']
gq_apportion = os.path.join(scratch_gdb, '_18_gq_apportion')

arcpy.analysis.ApportionPolygon(group_quarters, 
                            gq_columns, 
                            microzones, 
                            gq_apportion, 'AREA')


gq_apportion_df = pd.DataFrame.spatial.from_featureclass(gq_apportion)
gq_apportion_df['GQ_RATIO'] = gq_apportion_df['GQPOP'] / gq_apportion_df['TOTALPOP']
gq_apportion_df['GQ_RATIO'] = gq_apportion_df['GQ_RATIO'].fillna(0)


microzones_df = microzones_df.merge(gq_apportion_df[['zone_id', 'GQ_RATIO']], left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del gq_apportion_df

#----------------------
# Mixed-Use 
#----------------------

print("Working on mixed use...")

# create mixed use attribute (fill NAs and infinites from dividing by 0, with 0)
microzones_df['MIXED_USE'] = ((microzones_df['households'] * microzones_df['jobs_total']) / (microzones_df['households'] + microzones_df['jobs_total'])).replace(np.inf, 0)
microzones_df['MIXED_USE'].fillna(0, inplace=True)

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

maz_bs_join = os.path.join(scratch_gdb, "_19_maz_bs_join")
arcpy.SpatialJoin_analysis(microzones, bike_kiosks_lyr, maz_bs_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del bike_kiosks_lyr

# merge park score field back to full table
maz_bs_join_df = pd.DataFrame.spatial.from_featureclass(maz_bs_join) # Might have to fill in zeroes
maz_bs_join_df =  maz_bs_join_df[['zone_id', 'bike_share']]
microzones_df = microzones_df.merge(maz_bs_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_bs_join_df
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

maz_ind_join = os.path.join(scratch_gdb, "_20_maz_ind_join")
arcpy.SpatialJoin_analysis(microzones, industrial_districts_lyr, maz_ind_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
del industrial_districts_lyr

# merge park score field back to full table
maz_ind_join_df = pd.DataFrame.spatial.from_featureclass(maz_ind_join) # Might have to fill in zeroes
maz_ind_join_df =  maz_ind_join_df[['zone_id', 'industrial']]
microzones_df = microzones_df.merge(maz_ind_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del maz_ind_join_df
#----------------------
# Centroid Node 
#----------------------

print("Working on node centroids...")

# add node ID to zones these ID will be from the node/link output
maz_centroids = os.path.join(scratch_gdb, "_21_maz_centroids")   
arcpy.FeatureToPoint_management(microzones, maz_centroids)

arcpy.Near_analysis(maz_centroids, nodes)

# merge centroid field back to full table
maz_centroid_join_df = pd.DataFrame.spatial.from_featureclass(maz_centroids) # Might have to fill in zeroes
maz_centroid_join_df =  maz_centroid_join_df[['zone_id', 'NEAR_FID']]
maz_centroid_join_df.columns = ['zone_id', 'NODE_ID']
microzones_df = microzones_df.merge(maz_centroid_join_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'inner')
del maz_centroid_join_df

#-----------------------------------
# Summarize Bike Path and Bike Lane
#-----------------------------------

print("summarizing bike lane and path length...")


print("-- buffering zones")
buffdist = 0.25
microzone_buffer = arcpy.analysis.PairwiseBuffer(
    in_features=microzones,
    out_feature_class=os.path.join(scratch_gdb, '_22_microzone_buffer'),
    buffer_distance_or_field="0.25 Miles",
    dissolve_option="NONE",
    dissolve_field=None,
    method="GEODESIC",
    max_deviation="0 Meters"
)

network_lyr = arcpy.MakeFeatureLayer_management(network, 'network_lyr')

print("-- working on bike lanes")

# filter network for bike lanes and paths
query1 = (""" Bike_Lane = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query1)
lanes_intersect = arcpy.analysis.Intersect(
    in_features= [network_lyr, microzone_buffer],
    out_feature_class=os.path.join(scratch_gdb, '_23_lanes_intersect'),
    join_attributes="ONLY_FID",
    cluster_tolerance=None,
    output_type="LINE"
)
arcpy.CalculateGeometryAttributes_management(os.path.realpath(lanes_intersect[0]), [['bklane_len','LENGTH_GEODESIC']],  length_unit='MILES_US')

arcpy.management.DeleteIdentical(
    in_dataset=lanes_intersect,
    fields="Shape"
)

lanes_intersect_pts = arcpy.management.FeatureToPoint(
    in_features=lanes_intersect,
    out_feature_class=os.path.join(scratch_gdb, '_24_lanes_intersect_pts'),
    point_location="INSIDE"
)


print("-- running lanes spatial join")
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzone_buffer)
fieldmappings.addTable(lanes_intersect_pts)
modFieldMapping(fieldmappings, 'bklane_len', 'sum')
maz_lane_join = os.path.join(scratch_gdb, "_025_maz_lane_join")
arcpy.SpatialJoin_analysis(microzone_buffer, lanes_intersect_pts, maz_lane_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
bike_lane_sum_df = pd.DataFrame.spatial.from_featureclass(maz_lane_join)[['zone_id', 'bklane_len']].copy()
microzones_df = microzones_df.merge(bike_lane_sum_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del bike_lane_sum_df

print("-- working on bike paths")

query2 = (""" Bike_Path = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query2)
paths_intersect = arcpy.analysis.Intersect(
    in_features= [network_lyr, microzone_buffer],
    out_feature_class=os.path.join(scratch_gdb, '_26_paths_intersect'),
    join_attributes="ALL",
    cluster_tolerance=None,
    output_type="LINE"
)
arcpy.CalculateGeometryAttributes_management(os.path.realpath(paths_intersect[0]), [['bkpath_len','LENGTH_GEODESIC']],  length_unit='MILES_US')

arcpy.management.DeleteIdentical(
    in_dataset=paths_intersect,
    fields="Shape"
)


paths_intersect_pts = arcpy.management.FeatureToPoint(
    in_features=paths_intersect,
    out_feature_class=os.path.join(scratch_gdb, '_27_paths_intersect_pts'),
    point_location="INSIDE"
)

# use spatial join to get school code on to microzones (maximum score in zone will be used)
print("-- running paths spatial join")
fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(microzone_buffer)
fieldmappings.addTable(paths_intersect_pts)
modFieldMapping(fieldmappings, 'bkpath_len', 'sum')
maz_path_join = os.path.join(scratch_gdb, "_28_maz_path_join")
arcpy.SpatialJoin_analysis(microzone_buffer, paths_intersect_pts, maz_path_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT")
bike_path_sum_df = pd.DataFrame.spatial.from_featureclass(maz_path_join)[['zone_id', 'bkpath_len']].copy()
microzones_df = microzones_df.merge(bike_path_sum_df, left_on = 'zone_id', right_on = 'zone_id' , how = 'left')
del bike_path_sum_df

# del gdb
del network_lyr


#================================
# WRAP-UP
#================================ 

# fill NAs where necessary
microzones_df = fill_na_sedf(microzones_df)

# final export
names_lowercase = [att.lower() if att != 'SHAPE' else att for att in list(microzones_df.columns) ]
microzones_df.columns = names_lowercase
microzones_df['zone_id'] = microzones_df.index # IMPORTANT, ensures zone_id is 0-indexed and sequential

microzones_df['zone_id'] = microzones_df['zone_id'].astype('Float64')
microzones_df['avgincome'] = microzones_df['avgincome'].astype('Float64')
microzones_df['enrol_elem'] = microzones_df['enrol_elem'].fillna(0)
microzones_df['mixed_use'] = microzones_df['mixed_use'].fillna(0)
microzones_df.drop(['SHAPE'], axis=1).to_csv(os.path.join(outputs[0], 'microzones.csv'), index=False)
# microzones_df.spatial.to_featureclass(location=os.path.join(temp_dir, "microzones.shp"), sanitize_columns=False)

print('Zones complete!!')

#=====================================
# Clean up
#=====================================

print('Clean-up')
del microzones
del microzones_df
del cursor
del fieldmappings
del join_features
del taz_geometry
del taz_join
del taz_join2
del taz_join3
del taz_join_filt
del taz_se_data3




