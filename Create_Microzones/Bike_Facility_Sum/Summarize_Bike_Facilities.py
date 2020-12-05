# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 13:03:13 2020

@author: jreynolds
"""

import arcpy
import os
import pandas as pd
arcpy.env.overwriteOutput = True
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# main directory
base = r'E:\Projects\utah_bike_demand_model\Create_Microzones\Bike_Facility_Sum'


# create output gdb
gdb = os.path.join(base, "test.gdb")
if not arcpy.Exists(gdb):
    arcpy.CreateFileGDB_management(base, "test.gdb")


# inputs
zones = r"E:\Projects\utah_bike_demand_model\Create_Microzones\Outputs\microzones.shp"
zones_lyr = arcpy.MakeFeatureLayer_management(zones, 'zones_lyr')

network = r"E:\Projects\utah_bike_demand_model\Convert_MM_Network\Outputs\links.shp"
network_lyr = arcpy.MakeFeatureLayer_management(network, 'network_lyr')


# filter network for bike lanes and paths
query1 = (""" Bike_Lane = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query1)
bike_lanes = arcpy.MakeFeatureLayer_management(network_lyr, 'bike_lanes_lyr')

query2 = (""" Bike_Path = 1 """)
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', query2)
bike_paths =  arcpy.MakeFeatureLayer_management(network_lyr, 'bike_paths_lyr')



# get length of bike paths within each buffered zone
print("summarizing bike lane length...")
bike_lane_sum = os.path.join(gdb, 'bike_lane_sum')

arcpy.SummarizeNearby_analysis(in_features=zones_lyr,in_sum_features=bike_lanes,out_feature_class=bike_lane_sum, distance_type ='STRAIGHT_LINE', distances=.25, distance_units='MILES', keep_all_polygons='KEEP_ALL', sum_fields=[['Length_Mil', 'Sum']], sum_shape='ADD_SHAPE_SUM', shape_unit='MILES')

bike_lane_sum_df = pd.DataFrame.spatial.from_featureclass(bike_lane_sum)[['zone_id', 'SUM_Length_Mil']]
bike_lane_sum_df.columns = ['zone_id', 'bklane_len']


# get length of bike paths within each buffered zone
print("summarizing bike path length...")
bike_path_sum = os.path.join(gdb, 'bike_path_sum')

arcpy.SummarizeNearby_analysis(in_features=zones_lyr,in_sum_features=bike_paths,out_feature_class=os.path.join(gdb, 'bike_path_sum'), distance_type ='STRAIGHT_LINE', distances=.25, distance_units='MILES', keep_all_polygons='KEEP_ALL', sum_fields=[['Length_Mil', 'Sum']], sum_shape='ADD_SHAPE_SUM', shape_unit='MILES')

bike_path_sum_df = pd.DataFrame.spatial.from_featureclass(bike_path_sum)[['zone_id', 'SUM_Length_Mil']]
bike_path_sum_df.columns = ['zone_id', 'bkpath_len']

# merge em
bk_path_lane = bike_lane_sum_df.merge(bike_path_sum_df, left_on='zone_id', right_on='zone_id', how='inner')

print("done")

