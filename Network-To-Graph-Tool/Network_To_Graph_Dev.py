"""
Created on Mon Mar 30 08:18:19 2020

@author: jreynolds bgranberg 

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb bike --elev E:\Data\Elevation\wf_elev.tif

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020_JR.gdb bike --elev E:\Data\Elevation\wf_elev.tif

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb bike

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb ped

"""

import arcpy
import argparse
import os
import pandas as pd
import geopandas as gpd
from arcpy.sa import *

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
temp_dir = os.path.join(os.getcwd(), 'Results')

# determine network dataset to process
mm_network = r"E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_08182020.gdb"
mode = 'bike'
# mm_network = args.multimodal_network
# mode = args.mode


if mode == 'bike':
    network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'BikeNetwork')
if mode == 'auto':
    network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'AutoNetwork')
if mode == 'ped':
    network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'PedNetwork')

print("converting: {}...".format(network))


# create linkpoints toggle
create_linkpoints = False

# Store elevation dataset, if provided
elevation = r'E:\Data\Elevation\wf_elev.tif'
#elevation = args.elev

# Cleanup files toggle
perform_clean_up = True

#=====================================
# Prep data
#=====================================

study_area = os.path.join(os.getcwd(), 'Data', 'TAZ_WFRC_UTM12.shp')

# select road segments that overlap with study area
lines_copy_lyr = arcpy.MakeFeatureLayer_management(network,"temp_lines_lyr")
arcpy.SelectLayerByLocation_management("temp_lines_lyr", 'intersect', study_area)
lines_study_area = arcpy.FeatureClassToFeatureClass_conversion(lines_copy_lyr, temp_dir, 'temp_lines.shp')

# erase 
print("Adding canyon roads...")
canyon_roads = r'.\Data\Canyon_Roads.shp'
lines_erased = os.path.join(temp_dir, 'lines_erased.shp')
arcpy.Erase_analysis(lines_study_area, canyon_roads, lines_erased)

# merge
arcpy.Append_management([canyon_roads], lines_erased, schema_type='NO_TEST')


# split lines at vertices
#lines_copy = arcpy.FeatureToLine_management(lines_copy_lyr, os.path.join(temp_dir, 'temp_lines2.shp'))
lines_copy = arcpy.FeatureToLine_management(lines_erased, os.path.join(temp_dir, 'temp_lines2.shp'))

lines_copy_lyr = arcpy.MakeFeatureLayer_management(lines_copy,"temp_lines_lyr2")




# Add unique ID
unique_id_field = 'id'
arcpy.AddField_management(lines_copy, field_name=unique_id_field, field_type='LONG')
arcpy.CalculateField_management(lines_copy, unique_id_field, '"!FID!"')

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
with arcpy.da.UpdateCursor(start_pts_sorted, ['id']) as cursor:
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
arcpy.CalculateGeometryAttributes_management(start_pts, [["xcoord", "POINT_X"],["ycoord", "POINT_Y"]])

# this might allow this section to run in command line
# with arcpy.da.UpdateCursor(start_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
#     for row in cursor:
#         row[0] = row[2]
#         row[1] = row[3]
#         cursor.updateRow(row)
        
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
with arcpy.da.UpdateCursor(end_pts_sorted, ['id']) as cursor:
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
arcpy.CalculateGeometryAttributes_management(end_pts, [["xcoord", "POINT_X"], ["ycoord", "POINT_Y"]])

# this might allow this section to run in command line
# with arcpy.da.UpdateCursor(end_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
#     for row in cursor:
#         row[0] = row[2]
#         row[1] = row[3]
#         cursor.updateRow(row)

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
if elevation:
    print('--extracting z values to nodes')
    nodes_final = ExtractValuesToPoints(merged_pts, elevation, os.path.join(temp_dir, 'nodes.shp'))
    arcpy.CalculateField_management(nodes_final,"zcoord",'!{}!'.format('RASTERVALU'))
    arcpy.DeleteField_management(nodes_final, "RASTERVALU")
else: 
    nodes_final = arcpy.FeatureClassToFeatureClass_conversion(merged_pts, temp_dir, 'nodes.shp')


# Remove duplicate nodes, extract z values seems to add duplicates
print('--deleting duplicate nodes (again)')
arcpy.DeleteIdentical_management(nodes_final, "XY_Key")

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

# # Add Bike boulevard attribute
# arcpy.AddField_management(lines_copy_lyr, field_name="BikeBlvd", field_type='Short')

# with arcpy.da.UpdateCursor(lines_copy_lyr, ['BIKE_L', 'BIKE_R', 'BikeBlvd']) as cursor:
#     for row in cursor:
        
#         if row[0] in ['3B', '3C']:
#             row[2] = 1
#         else:
#             row[2] = 0
            
#         cursor.updateRow(row)

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

fields = ['BIKE_L', 'BIKE_R', 'SourceData', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd']
with arcpy.da.UpdateCursor(lines_copy_lyr, fields) as cursor:
    for row in cursor:
             
        # set bike lane attribute
        if row[0] in bl or row[1] in bl:
            row[3] = 1
        else:
            row[3] = 0
            
        # set bike path attribute
        if row[2] in bp or row[0] in bp or row[1] in bp:
            row[4] = 1
        else:
            row[4] = 0
            
        # set bike blvd attribute
        if row[0] in bb or row[1] in bb:
            row[5] = 1
        else:
            row[5] = 0
            
        cursor.updateRow(row)

#------------------------------------------------
# Add traffic signal attribute
#------------------------------------------------

# Load and buffer traffic signals
traffic_signals = os.path.join(os.getcwd(), 'Data', 'Traffic_Signals.shp')
buffered_signals = os.path.join(temp_dir, "Buffered_Signals.shp")
arcpy.Buffer_analysis(traffic_signals, buffered_signals, "20 Meters")

# Perform spatial join
links_final = os.path.join(temp_dir, "links_temp.shp")
arcpy.SpatialJoin_analysis(lines_copy_lyr, buffered_signals, links_final, "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="INTERSECT")


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
    arcpy.CalculateGeometryAttributes_management(all_pts, [["xcoord", "POINT_X"],["ycoord", "POINT_Y"]])
    
    # with arcpy.da.UpdateCursor(all_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
    #     for row in cursor:
    #         row[0] = row[2]
    #         row[1] = row[3]
    #         cursor.updateRow(row)
    
    # add xy key to all points
    arcpy.AddField_management(all_pts, field_name="XY_Key", field_type='string')
    arcpy.CalculateField_management(all_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))
    
    # remove duplicates in case they exist
    arcpy.DeleteIdentical_management(all_pts, "XY_Key")
    
    # Join all nodes to both ends nodes and calculate a field to use for tracking start/end nodes
    linkpoints_layer = arcpy.MakeFeatureLayer_management(all_pts,"all_pts_lyr")
    arcpy.AddField_management(linkpoints_layer, field_name="Join_Key", field_type='string')
    arcpy.AddJoin_management(linkpoints_layer, "XY_Key", nodes_final, 'XY_Key', join_type="KEEP_ALL")
    arcpy.CalculateField_management(linkpoints_layer,"all_pts.Join_Key",'!{}!'.format('nodes.XY_Key'))
    arcpy.RemoveJoin_management(linkpoints_layer)
    arcpy.AddField_management(linkpoints_layer, field_name="zcoord", field_type='LONG')
    
    # Use update cursor to delete start and end nodes from linkpoints
    print('--Deleting Start/End Nodes from all points')
    total_joined_nodes = 0
    with arcpy.da.UpdateCursor(linkpoints_layer, ['Join_Key']) as cursor:
        for row in cursor:
            if row[0] != ' ':
                cursor.deleteRow()
                total_joined_nodes += 1
        
    del cursor
    print("--Total Nodes deleted: {}".format(total_joined_nodes))
    arcpy.DeleteField_management(linkpoints_layer, 'Join_Key')
    
    # add z values if specified
    if elevation:   
        print('--extracting z values to linkpoints')
        linkpoints_final = ExtractValuesToPoints(linkpoints_layer, elevation, os.path.join(temp_dir, 'linkpoints.shp'))
        arcpy.CalculateField_management(linkpoints_final,"zcoord",'!{}!'.format('RASTERVALU'))
        arcpy.DeleteField_management(linkpoints_final, "RASTERVALU")
    else: 
        linkpoints_final = arcpy.FeatureClassToFeatureClass_conversion(linkpoints_layer, temp_dir, 'linkpoints.shp')
    
    # Remove duplicate nodes, extract z values seems to add duplicates
    print('--deleting duplicate linkpoints')
    arcpy.DeleteIdentical_management(linkpoints_final, "XY_Key")

#=====================================
# Create CSV Tables
#=====================================

print('Creating table outputs')

# Convert shapefiles to csv for formatting in Pandas
arcpy.TableToTable_conversion(nodes_final, temp_dir, 'nodes_temp.csv')
arcpy.TableToTable_conversion(links_final, temp_dir, 'links_temp.csv')
if create_linkpoints == True:
    arcpy.TableToTable_conversion(linkpoints_final, temp_dir, 'linkpoints_temp.csv')

# Read csvs into pandas
nodes_dataframe = pd.read_csv(os.path.join(temp_dir, 'nodes_temp.csv'))
links_dataframe = pd.read_csv(os.path.join(temp_dir, 'links_temp.csv'))
if create_linkpoints == True:
    linkpoints_dataframe = pd.read_csv(os.path.join(temp_dir, 'linkpoints_temp.csv'))

#-------------------
# format nodes
#-------------------

print('--formatting nodes')
nodes_field_names = ['node_id', 'xcoord', 'ycoord', 'zcoord']
nodes_dataframe_formatted = nodes_dataframe[['FID', 'xcoord', 'ycoord', 'zcoord']].copy()
nodes_dataframe_formatted.columns = nodes_field_names
nodes_dataframe_formatted = nodes_dataframe_formatted.sort_values(by=['node_id'])

#-------------------
# format links
#-------------------

print('--formatting links')

# Create from/to node columns
links_dataframe = links_dataframe.assign(from_node='', to_node='', from_x='', from_y='', to_x='', to_y='')

# Join with nodes to get start node IDs
links_dataframe_temp = links_dataframe.merge(nodes_dataframe, left_on = 'Start_Key', right_on = 'XY_Key' , how = 'inner')
links_dataframe_temp['from_node'] = links_dataframe_temp['FID_y']
links_dataframe_temp['from_x'] = links_dataframe_temp['xcoord']
links_dataframe_temp['from_y'] = links_dataframe_temp['ycoord']


# Join with nodes to get end node IDs
links_dataframe_temp = links_dataframe_temp.merge(nodes_dataframe, left_on = 'End_Key', right_on = 'XY_Key' , how = 'inner')
links_dataframe_temp['to_node'] = links_dataframe_temp['FID']
links_dataframe_temp['to_x'] = links_dataframe_temp['xcoord_y']
links_dataframe_temp['to_y'] = links_dataframe_temp['ycoord_y']

# subset and rename columns
links_field_names = ['link_id', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork','PedNetwork', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Miles', 'ConnectorN', 'RoadClass', 'AADT', 'Length_Meters', 'Signal', 'Sig_Count', 'BIKE_L', 'BIKE_R', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd']
links_dataframe_formatted = links_dataframe_temp[['FID_x', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name_x', 'Oneway_x', 'Speed_x', 'AutoNetwor_x', 'BikeNetwor_x', 'PedNetwork_x', 'DriveTime_x', 'BikeTime_x', 'Pedestrian_x', 'Length_Mil_x', 'ConnectorN_x', 'RoadClass_x', 'AADT_x', 'Shape_Leng_x', 'Signal', 'Join_Count','BIKE_L', 'BIKE_R', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd']].copy()
links_dataframe_formatted.columns = links_field_names
links_dataframe_formatted = links_dataframe_formatted.sort_values(by=['link_id'])


#------------------------
# Calculate link slope
#------------------------

if elevation:
    
    ln_from = links_dataframe_formatted.merge(nodes_dataframe_formatted, left_on = 'from_node', right_on = 'node_id' , how = 'inner')
    ln_from = ln_from[['link_id', 'zcoord']].copy()
    ln_from.columns = ['link_id', 'from_z']
    
    ln_to = links_dataframe_formatted.merge(nodes_dataframe_formatted, left_on = 'to_node', right_on = 'node_id' , how = 'inner')
    ln_to = ln_to[['link_id', 'zcoord']].copy()
    ln_to.columns = ['link_id', 'to_z']
    
    links_df2 = links_dataframe_formatted.merge(ln_from, left_on = 'link_id', right_on = 'link_id' , how = 'inner')
    links_df2 = links_df2.merge(ln_to, left_on = 'link_id', right_on = 'link_id' , how = 'inner')
    
    links_df2['Slope_AB'] = ((links_df2['from_z'] - links_df2['to_z']) / links_df2['Length_Meters'] * 100) 
    links_df2['Slope_BA'] = ((links_df2['to_z'] - links_df2['from_z']) / links_df2['Length_Meters'] * 100) 

    links_dataframe_formatted = links_df2




#-------------------
# format linkpoints
#-------------------

if create_linkpoints == True:
    links_nodes = links_dataframe_formatted[['link_id', 'from_node', 'to_node']].copy()
    
    links_node_ids = set(list(set(list(links_nodes['from_node']) + list(links_nodes['to_node']))))
    nodes_ids = set(list(nodes_dataframe_formatted['node_id']))
    diff =  nodes_ids - links_node_ids
    
    print('--formatting linkpoints')
    linkpoints_dataframe = linkpoints_dataframe.assign(link_id='', point_no='')
    linkpoints_dataframe_temp = linkpoints_dataframe.merge(links_dataframe, left_on = 'id', right_on = 'id' , how = 'inner')
    linkpoints_dataframe_temp['link_id'] = linkpoints_dataframe_temp['FID_y']
    
    # subset and rename columns
    linkpoints_field_names = ['linkpoint_id','link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']
    linkpoints_dataframe_formatted = linkpoints_dataframe_temp[['FID_x', 'link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']].copy()
    linkpoints_dataframe_formatted.columns = linkpoints_field_names
    linkpoints_dataframe_formatted = linkpoints_dataframe_formatted.sort_values(by=['linkpoint_id'])





#------------------------------
# write final csvs and shapes
#------------------------------

# export formatted csvs
print('--exporting to csv')
nodes_dataframe_formatted.to_csv(os.path.join(temp_dir, 'nodes.csv'),index=False)
links_dataframe_formatted.to_csv(os.path.join(temp_dir, 'links.csv'),index=False)
if create_linkpoints == True:
    linkpoints_dataframe_formatted.to_csv(os.path.join(temp_dir, 'linkpoints.csv'),index=False)


# export links
links = gpd.read_file(links_final)
links = links.merge(pd.read_csv(os.path.join(temp_dir, 'links.csv')), left_on = 'id', right_on = 'link_id' , how = 'inner')
links.to_file(os.path.join(temp_dir, 'links.shp'))

# =====================================
# Clean up
# =====================================

if perform_clean_up == True:
    print('Performing clean-up')
    trash = [merged_pts, lines_copy_lyr, lines_copy, start_pts, end_pts]
    for item in trash:
        try:
            arcpy.Delete_management(item)
        except:
            print("--Unable to delete {}".format(item))
    del item 
        
    # remove temp csvs
    os.remove(os.path.join(temp_dir, 'nodes_temp.csv'))
    os.remove(os.path.join(temp_dir, 'links_temp.csv'))
    os.remove(os.path.join(temp_dir, 'nodes_temp.csv.xml'))
    os.remove(os.path.join(temp_dir, 'links_temp.csv.xml'))
    if create_linkpoints == True:
        os.remove(os.path.join(temp_dir, 'linkpoints_temp.csv'))
        os.remove(os.path.join(temp_dir, 'linkpoints_temp.csv.xml'))
    
    
    del elevation
    del end_pts
    del lines_copy
    del lines_copy_lyr
    del start_pts
    
    del links_final
    del merged_pts
    if create_linkpoints == True:
        del all_pts
        del linkpoints_layer

print('Done!')


