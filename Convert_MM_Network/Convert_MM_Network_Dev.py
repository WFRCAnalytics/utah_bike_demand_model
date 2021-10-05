"""
Created on Mon Mar 30 08:18:19 2020

@author: jreynolds bgranberg 

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb

"""

import arcpy
from arcpy.sa import *
import argparse
import os
import pandas as pd
from arcgis import GIS
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import glob

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

     
# Command line arguments
# parser = argparse.ArgumentParser("Convert Multimodal Network to Node/Link format")
# parser.add_argument('multimodal_network', type=str, help='input multimodal network gdb from WFRC')
# parser.add_argument('mode', type=str, choices=['bike','ped', 'auto'], help='bike, auto, or ped')
# parser.add_argument('--elev', type=str, help='path to overlapping elevation dataset')
# args = parser.parse_args()

# print(args.multimodal_network)
# print(args.mode)
# print(args.elev)

# temporary directory
temp_dir = '.\\Outputs'

# determine network dataset to process
mm_network = r"E:\Active_Transportation\Data\Multimodal_Network\MM_NetworkDataset_08052021.gdb"
# mm_network = args.multimodal_network

print("converting: {}...".format(mm_network))

# create linkpoints toggle
create_linkpoints = True

# Cleanup files toggle
perform_clean_up = True

#=====================================
# Inputs
#=====================================

study_area = r'.\Inputs\TAZ_WFRC_UTM12.shp'
canyon_roads = r'.\Inputs\Canyon_Roads.shp'
traffic_signals = r'.\Inputs\Traffic_Signals.shp'
buffered_signals = r'.\Inputs\Buffered_Signals.shp'

#=====================================
# Prep data
#=====================================

# create outputs folder
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# filter for bike features
network = os.path.join(mm_network, 'BikePedAuto')
network_lyr = arcpy.MakeFeatureLayer_management(network,"network_lyr")
arcpy.SelectLayerByAttribute_management(network_lyr, 'NEW_SELECTION', """ BikeNetwork = 'Y' """)

# select road segments that overlap with study area
arcpy.SelectLayerByLocation_management(network_lyr, 'INTERSECT', study_area, selection_type='SUBSET_SELECTION')
lines_study_area = arcpy.FeatureClassToFeatureClass_conversion(network_lyr, temp_dir, 'temp_lines.shp')

# add canyon roads
print("Adding canyon roads...")

# erase existing canyon roads and add custom versions
lines_erased = arcpy.Erase_analysis(lines_study_area, canyon_roads, os.path.join(temp_dir, 'lines_erased.shp'))
arcpy.Append_management([canyon_roads], lines_erased, schema_type='NO_TEST')

# create a layer object
lines_copy_lyr = arcpy.MakeFeatureLayer_management(lines_erased,"temp_lines_lyr")

# Add unique ID
unique_id_field = 'temp_id'
arcpy.AddField_management(lines_copy_lyr, field_name=unique_id_field, field_type='LONG')
arcpy.CalculateField_management(lines_copy_lyr, unique_id_field, '"!FID!"')

#=====================================
# Create Nodes
#=====================================

print('Creating Nodes')

# Start points
print('--generating start points')

# get start points for each line, 
start_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'start_pts_initial.shp'), 'START')

# Delete extra Start nodes, accounts for rare instance of multiple end nodes created
print('--checking for extra start points')
arcpy.AddField_management(start_pts, field_name='Temp_ID', field_type='LONG')
arcpy.CalculateField_management(start_pts, 'Temp_ID', '"!FID!"')
start_pts_sorted = arcpy.Sort_management(start_pts, os.path.join(temp_dir, 'start_pts.shp'), sort_field=[["Temp_ID", "ASCENDING"]])

previous_id = None
with arcpy.da.UpdateCursor(start_pts_sorted, ['temp_id']) as cursor:
    for row in cursor:
        
        if row[0] == previous_id:
            #print("--Current:{}, Previous:{}".format(row[0], previous_id))
            cursor.deleteRow()
        previous_id = row[0]

arcpy.DeleteField_management(start_pts, 'Temp_ID')
start_pts = start_pts_sorted

# add xy coords to start points
arcpy.AddField_management(start_pts, field_name="xcoord", field_type='double')
arcpy.AddField_management(start_pts, field_name="ycoord", field_type='double')

# this might allow this section to run in command line
with arcpy.da.UpdateCursor(start_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
    for row in cursor:
        row[0] = row[2]
        row[1] = row[3]
        cursor.updateRow(row)
        
# create xy key to start points
arcpy.AddField_management(start_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(start_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))


# End points
print('--generating end points')

# get end points for each line
end_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'end_pts_initial.shp'), 'END')

# Delete extra End nodes, accounts for rare instance of multiple end nodes created
print('--checking for extra end points')
arcpy.AddField_management(end_pts, field_name='Temp_ID', field_type='LONG')
arcpy.CalculateField_management(end_pts, 'Temp_ID', '"!FID!"')
end_pts_sorted = arcpy.Sort_management(end_pts, os.path.join(temp_dir, 'end_pts.shp'), sort_field=[["Temp_ID", "DESCENDING"]])

previous_id = None
with arcpy.da.UpdateCursor(end_pts_sorted, ['temp_id']) as cursor:
    for row in cursor:
        
        if row[0] == previous_id:
            #print("--Current:{}, Previous:{}".format(row[0], previous_id))
            cursor.deleteRow()
        previous_id = row[0]

arcpy.DeleteField_management(end_pts, 'Temp_ID')
end_pts = end_pts_sorted

# add xy coords to end points
arcpy.AddField_management(end_pts, field_name="xcoord", field_type='double')
arcpy.AddField_management(end_pts, field_name="ycoord", field_type='double')

# this might allow this section to run in command line
with arcpy.da.UpdateCursor(end_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
    for row in cursor:
        row[0] = row[2]
        row[1] = row[3]
        cursor.updateRow(row)

# add xy key to end points
arcpy.AddField_management(end_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(end_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))


# join with centerlines, copy xy key
arcpy.AddJoin_management(lines_copy_lyr, unique_id_field, start_pts, unique_id_field)
arcpy.CalculateField_management(lines_copy_lyr,"Start_Key",'!{}!'.format('start_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# join with centerlines, copy xy key
arcpy.AddJoin_management(lines_copy_lyr, unique_id_field, end_pts, unique_id_field)
arcpy.CalculateField_management(lines_copy_lyr,"End_Key",'!{}!'.format('end_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# Create 'both ends' nodes data set by merging start nodes and end nodes
print('--merging start and end points')    
merged_pts = arcpy.Merge_management([start_pts, end_pts], os.path.join(temp_dir, "merged_pts.shp"))
arcpy.AddField_management(merged_pts, field_name="zcoord", field_type='LONG')

# Remove duplicate nodes (dissolve drops fields, delete identical does not)
print('--deleting duplicate nodes')
arcpy.DeleteIdentical_management(merged_pts, "XY_Key")

# Get Z values from 10m DEM
print('--extracting z values to nodes')
items = glob.glob('.\Inputs\Elevation_Tiles\wfrc_elev_tile*.tif')
elevation = arcpy.MosaicToNewRaster_management(items, r'.\Inputs','Elev_Mosaic.tif',pixel_type='16_BIT_UNSIGNED',cellsize=10, number_of_bands=1)        

nodes_extract = arcpy.sa.ExtractValuesToPoints(merged_pts, elevation, os.path.abspath(os.path.join(temp_dir, 'nodes_extract.shp')),"NONE", "VALUE_ONLY")

arcpy.CalculateField_management(nodes_extract,"zcoord",'!{}!'.format('RASTERVALU'))
arcpy.DeleteField_management(nodes_extract, "RASTERVALU")

# Remove duplicate nodes, extract z values seems to add duplicates
print('--deleting duplicate nodes (again)')
arcpy.DeleteIdentical_management(nodes_extract, "XY_Key")

#=====================================
# Create Links
#=====================================
 
print('Creating Links')    

# recalc meters and miles
with arcpy.da.UpdateCursor(lines_copy_lyr, ['Length_Mil', 'Shape_Leng', 'SHAPE@LENGTH']) as cursor:
    for row in cursor:
        
        row[1] = row[2]
        
        # meters to miles
        row[0] = row[2] * 0.000621371
        cursor.updateRow(row)    

#------------------------------------------------
# Add bike_lane, bike_path, bike_blvd attributes
#------------------------------------------------

# Add bike_lane, bike_path, bike_blvd fields
arcpy.AddField_management(lines_copy_lyr, field_name="Bike_Lane", field_type='Short')
arcpy.AddField_management(lines_copy_lyr, field_name="Bike_Path", field_type='Short')
arcpy.AddField_management(lines_copy_lyr, field_name="Bike_Blvd", field_type='Short')

# bike lane codes
bl = ['2','2A','2B', '3A']

# bike path code
bp = ['Trails', '1','1A','1B','1C']

# bike blvd codes
bb = ['3B', '3C']

fields = ['BIKE_L', 'BIKE_R', 'SourceData', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd', 'AADT']
with arcpy.da.UpdateCursor(lines_copy_lyr, fields) as cursor:
    for row in cursor:
             
        # set bike lane attribute
        if row[0] in bl or row[1] in bl:
            row[3] = 1
        else:
            row[3] = 0
            
        # set bike blvd attribute
        if row[0] in bb or row[1] in bb:
            row[5] = 1
        else:
            row[5] = 0        
            
        # set bike path attribute
        if row[2] in bp or row[0] in bp or row[1] in bp:
            row[4] = 1
            row[6] = 0 # set aadt to zero
        else:
            row[4] = 0
            
        
            
        cursor.updateRow(row)

#------------------------------------------------
# Add traffic signal attribute
#------------------------------------------------

#buffer traffic signals
arcpy.Buffer_analysis(traffic_signals, buffered_signals, "20 Meters")

# Perform spatial join
links_signal_join = arcpy.SpatialJoin_analysis(lines_copy_lyr, buffered_signals, os.path.join(temp_dir, "links_signal_join.shp"), "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="INTERSECT")


#=====================================
# Create Linkpoints
#=====================================

if create_linkpoints == True:
    print('Creating Linkpoints')  
    print('--generating all points')
    
    # get all points for each line
    all_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'all_pts.shp'), 'ALL')
    
    # add xy coords to all points
    arcpy.AddField_management(all_pts, field_name="xcoord", field_type='double')
    arcpy.AddField_management(all_pts, field_name="ycoord", field_type='double')
    with arcpy.da.UpdateCursor(all_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
        for row in cursor:
            row[0] = row[2]
            row[1] = row[3]
            cursor.updateRow(row)    
    
    # add xy key to all points
    arcpy.AddField_management(all_pts, field_name="XY_Key", field_type='string')
    arcpy.CalculateField_management(all_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))
    
    # remove duplicates in case they exist
    arcpy.DeleteIdentical_management(all_pts, "XY_Key")
    
    # Join all nodes to both ends nodes and calculate a field to use for tracking start/end nodes
    linkpoints_layer = arcpy.MakeFeatureLayer_management(all_pts,"linkpoints_layer")
    arcpy.AddField_management(linkpoints_layer, field_name="Join_Key", field_type='string')
    arcpy.AddJoin_management(linkpoints_layer, "XY_Key", nodes_extract, 'XY_Key', join_type="KEEP_ALL")
    arcpy.CalculateField_management(linkpoints_layer,"all_pts.Join_Key",'!{}!'.format('nodes_extract.XY_Key'))
    arcpy.RemoveJoin_management(linkpoints_layer)
    arcpy.AddField_management(linkpoints_layer, field_name="zcoord", field_type='LONG')
    
    #arcpy.FeatureClassToFeatureClass_conversion(linkpoints_layer, temp_dir, 'lp_test.shp')
    
    # Use update cursor to delete start and end nodes from linkpoints
    print('--Deleting Start/End Nodes from all points')
    total_joined_nodes = 0
    with arcpy.da.UpdateCursor(linkpoints_layer, ['Join_Key']) as cursor:
        for row in cursor:
            if row[0] != "0":
                cursor.deleteRow()
                total_joined_nodes += 1
        
    del cursor
    print("--Total Nodes deleted: {}".format(total_joined_nodes))
    arcpy.DeleteField_management(linkpoints_layer, 'Join_Key')
    
    # add z values
    print('--extracting z values to linkpoints')      
    
    linkpoints_extract = ExtractValuesToPoints(linkpoints_layer, elevation, os.path.abspath(os.path.join(temp_dir, 'linkpoints_extract.shp')),"NONE", "VALUE_ONLY")
    arcpy.CalculateField_management(linkpoints_extract,"zcoord",'!{}!'.format('RASTERVALU'))
    arcpy.DeleteField_management(linkpoints_extract, "RASTERVALU")
    
    # Remove duplicate nodes, extract z values seems to add duplicates
    print('--deleting duplicate linkpoints')
    arcpy.DeleteIdentical_management(linkpoints_extract, "XY_Key")

#=====================================
# read nodes and links into pandas
#=====================================

print('Creating final outputs')
nodes_dataframe  = pd.DataFrame.spatial.from_featureclass(nodes_extract)
links_dataframe  = pd.DataFrame.spatial.from_featureclass(links_signal_join)
if create_linkpoints == True:
    linkpoints_dataframe  = pd.DataFrame.spatial.from_featureclass(linkpoints_extract)

#-------------------
# format nodes
#-------------------

print('--formatting nodes')
nodes_dataframe_formatted = nodes_dataframe[['FID', 'xcoord', 'ycoord', 'zcoord', 'XY_Key','SHAPE']].copy()
nodes_dataframe_formatted.columns = ['node_id', 'xcoord', 'ycoord', 'zcoord','XY_Key','SHAPE']
nodes_dataframe_formatted = nodes_dataframe_formatted.sort_values(by=['node_id'])

#-------------------
# format links
#-------------------

print('--formatting links')

# Create from/to node columns
links_dataframe = links_dataframe.assign(from_node='', to_node='', from_x='', from_y='', to_x='', to_y='')

# Join with nodes to get start node IDs
links_dataframe_temp = links_dataframe.merge(nodes_dataframe_formatted, left_on = 'Start_Key', right_on ='XY_Key' , how='inner')
links_dataframe_temp['from_node'] = links_dataframe_temp['node_id']
links_dataframe_temp['from_x'] = links_dataframe_temp['xcoord']
links_dataframe_temp['from_y'] = links_dataframe_temp['ycoord']


# Join with nodes to get end node IDs
links_dataframe_temp = links_dataframe_temp.merge(nodes_dataframe_formatted, left_on = 'End_Key', right_on='XY_Key' , how='inner')
links_dataframe_temp['to_node'] = links_dataframe_temp['node_id_y']
links_dataframe_temp['to_x'] = links_dataframe_temp['xcoord_y']
links_dataframe_temp['to_y'] = links_dataframe_temp['ycoord_y']

# subset and rename columns
links_dataframe_formatted = links_dataframe_temp[['FID','temp_id', 'from_node', 'to_node','from_x', 'from_y', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Mil', 'ConnectorN', 'CartoCode', 'AADT', 'Shape_Leng', 'Signal', 'Join_Count', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd','SHAPE_x']].copy()
links_field_names = ['link_id', 'temp_id', 'from_node','to_node','from_x', 'from_y', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'DriveTime', 'BikeTime', 'Pedestrian', 'Len_Miles', 'ConnectorN', 'CartoCode', 'AADT', 'Len_Meters', 'Signal', 'Sig_Count', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd','SHAPE']
links_dataframe_formatted.columns = links_field_names
links_dataframe_formatted = links_dataframe_formatted.sort_values(by=['link_id'])


#------------------------
# Calculate link slope
#------------------------

   
ln_from = links_dataframe_formatted.merge(nodes_dataframe_formatted, left_on = 'from_node', right_on = 'node_id' , how = 'inner')
ln_from = ln_from[['link_id', 'zcoord']].copy()
ln_from.columns = ['link_id', 'from_z']

ln_to = links_dataframe_formatted.merge(nodes_dataframe_formatted, left_on = 'to_node', right_on = 'node_id' , how = 'inner')
ln_to = ln_to[['link_id', 'zcoord']].copy()
ln_to.columns = ['link_id', 'to_z']

links_df2 = links_dataframe_formatted.merge(ln_from, left_on = 'link_id', right_on = 'link_id' , how = 'inner')
links_df2 = links_df2.merge(ln_to, left_on = 'link_id', right_on = 'link_id' , how = 'inner')

links_df2['Slope_AB'] = ((links_df2['from_z'] - links_df2['to_z']) / links_df2['Len_Meters'] * 100) 
links_df2['Slope_BA'] = ((links_df2['to_z'] - links_df2['from_z']) / links_df2['Len_Meters'] * 100) 
links_df2['Slope_Per'] = abs(links_df2['Slope_AB'])

links_dataframe_formatted = links_df2

# identify nodes that are not in use on the network - not used for anything - need to explore more
links_nodes = links_dataframe_formatted[['link_id', 'from_node', 'to_node']].copy()
links_node_ids = set(list(links_nodes['from_node']) + list(links_nodes['to_node']))
nodes_ids = set(list(nodes_dataframe_formatted['node_id']))
nodes_no_link =  nodes_ids - links_node_ids
# *** filter all nodes down to nodes no link using loc

#-------------------
# format linkpoints
#-------------------

if create_linkpoints == True:
    
    print('--formatting linkpoints')
    linkpoints_dataframe = linkpoints_dataframe.assign(link_id='', point_no='')
    linkpoints_dataframe_temp = linkpoints_dataframe.merge(links_dataframe_formatted, left_on = 'temp_id', right_on = 'temp_id' , how = 'inner')
    linkpoints_dataframe_temp['link_id'] = linkpoints_dataframe_temp['link_id_y']
    
    # subset and rename columns
    linkpoints_dataframe_formatted = linkpoints_dataframe_temp[['FID', 'link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord','SHAPE_x']].copy()
    linkpoints_field_names = ['linkpoint_id','link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord','SHAPE']
    linkpoints_dataframe_formatted.columns = linkpoints_field_names
    linkpoints_dataframe_formatted = linkpoints_dataframe_formatted.sort_values(by=['linkpoint_id'])
    linkpoints_dataframe_formatted['point_no'] = linkpoints_dataframe_formatted.groupby('link_id')['link_id'].rank(method='first')


#------------------------------
# write final csvs and shapes
#------------------------------

# export formatted csvs
print('--exporting to shape')
nodes_dataframe_formatted.spatial.to_featureclass(location=os.path.join(temp_dir, 'nodes.shp'),sanitize_columns=False)
links_dataframe_formatted.spatial.to_featureclass(location=os.path.join(temp_dir, 'links.shp'),sanitize_columns=False)

print('--exporting to csv')
del nodes_dataframe_formatted['SHAPE']
del links_dataframe_formatted['SHAPE']
nodes_dataframe_formatted.to_csv(os.path.join(temp_dir, 'nodes.csv'),index=False)
links_dataframe_formatted.to_csv(os.path.join(temp_dir, 'links.csv'),index=False)


if create_linkpoints == True:
    linkpoints_dataframe_formatted.spatial.to_featureclass(location=os.path.join(temp_dir, 'linkpoints.shp'),sanitize_columns=False)
    del linkpoints_dataframe_formatted['SHAPE']
    linkpoints_dataframe_formatted.to_csv(os.path.join(temp_dir, 'linkpoints.csv'),index=False)


# =====================================
# Clean up
# =====================================

if perform_clean_up == True:
    print('Performing clean-up')
    trash = [merged_pts, buffered_signals, lines_copy_lyr, lines_erased, start_pts, end_pts, os.path.join(temp_dir, 'start_pts_initial.shp'),  os.path.join(temp_dir, 'end_pts_initial.shp'), os.path.join(temp_dir, 'temp_lines.shp'), os.path.join(temp_dir, 'nodes_draft.shp'),elevation]
    for item in trash:
        try:
            arcpy.Delete_management(item)
        except:
            print("--Unable to delete {}".format(item))
    del item 
    
    if create_linkpoints == True:
        arcpy.Delete_management(os.path.join(temp_dir, 'all_pts.shp'))
    
    del elevation
    del end_pts
    del lines_copy_lyr
    del start_pts
    del merged_pts
    if create_linkpoints == True:
        del all_pts
        del linkpoints_layer

print('Done!')


