"""
Created on Mon Mar 30 08:18:19 2020

@author: jreynolds bgranberg 

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb  --elev E:\Data\Elevation\wf_elev.tif

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020_JR.gdb  --elev E:\Data\Elevation\wf_elev.tif

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb 

E:\Micromobility\Data\Multimodal_Network\MM_NetworkDataset_06242020.gdb

"""

import arcpy
import os
import yaml
import pandas as pd
from arcpy.sa import ExtractValuesToPoints
import glob
from arcgis.features import GeoAccessor, GeoSeriesAccessor

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
arcpy.env.parallelProcessingFactor = "90%"

#=====================================
# Inputs
#=====================================

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

config = load_yaml('Convert_MM_Network.yaml')
create_linkpoints = config['create_linkpoints']
perform_clean_up = config['perform_clean_up']
network = config['network']
study_area = config['study_area']
traffic_signals = config['traffic_signals']

#=====================================
# Data and environment prep
#=====================================

outputs = ['.\\Outputs', 'scratch.gdb', "bike_network.gdb"]
if not os.path.exists(outputs[0]):
    os.makedirs(outputs[0])

scratch_gdb = os.path.join(outputs[0], outputs[1])
network_gdb = os.path.join(outputs[0], outputs[2])
if not arcpy.Exists(scratch_gdb): arcpy.CreateFileGDB_management(outputs[0], outputs[1])
if not arcpy.Exists(network_gdb): arcpy.CreateFileGDB_management(outputs[0], outputs[2])

# determine network dataset to process
print("converting: {}...".format(network))

# select road segments that overlap with study area
lines_copy_lyr = arcpy.MakeFeatureLayer_management(network,"temp_lines_lyr", where_clause="BikeNetwork = 'Y'")
arcpy.SelectLayerByLocation_management("temp_lines_lyr", 'intersect', study_area, selection_type='SUBSET_SELECTION')
lines_study_area = arcpy.FeatureClassToFeatureClass_conversion(lines_copy_lyr, scratch_gdb, '_00_temp_lines')

lines_copy = arcpy.FeatureToLine_management(lines_study_area, os.path.join(scratch_gdb, '_01_temp_lines2'))

lines_copy_lyr = arcpy.MakeFeatureLayer_management(lines_copy,"temp_lines_lyr2")

# Add unique ID
unique_id_field = 'temp_id'
arcpy.AddField_management(lines_copy, field_name=unique_id_field, field_type='LONG')
arcpy.CalculateField_management(lines_copy, unique_id_field, '"!OBJECTID!"')

#=====================================
# Create Nodes
#=====================================

print('Creating Nodes')

# Start points
print('--generating start points')

# get start points for each line, 
start_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(scratch_gdb, '_02_start_pts_initial'), 'START')

# Delete extra Start nodes, accounts for rare instance of multiple end nodes created
print('--checking for extra start points')
arcpy.AddField_management(start_pts, field_name='Temp_ID', field_type='LONG')
arcpy.CalculateField_management(start_pts, 'Temp_ID', '"!OBJECTID!"')
start_pts_sorted = arcpy.Sort_management(start_pts, os.path.join(scratch_gdb, '_03_start_pts'), sort_field=[["Temp_ID", "ASCENDING"]])

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
with arcpy.da.UpdateCursor(start_pts, ['xcoord', 'ycoord', 'SHAPE@X', 'SHAPE@Y']) as cursor:
    for row in cursor:
        row[0] = row[2]
        row[1] = row[3]
        cursor.updateRow(row)

# create xy key for  start points
arcpy.AddField_management(start_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(start_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))

# End points
print('--generating end points')

# get end points for each line
end_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(scratch_gdb, '_04_end_pts_initial'), 'END')

# Delete extra End nodes, accounts for rare instance of multiple end nodes created
print('--checking for extra end points')
arcpy.AddField_management(end_pts, field_name='Temp_ID', field_type='LONG')
arcpy.CalculateField_management(end_pts, 'Temp_ID', '"!OBJECTID!"')
end_pts_sorted = arcpy.Sort_management(end_pts, os.path.join(scratch_gdb, '_05_end_pts'), sort_field=[["Temp_ID", "DESCENDING"]])

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
arcpy.CalculateField_management(lines_copy_lyr,"Start_Key",'!{}!'.format('_03_start_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# join with centerlines, copy xy key
arcpy.AddJoin_management(lines_copy_lyr, unique_id_field, end_pts, unique_id_field)
arcpy.CalculateField_management(lines_copy_lyr,"End_Key",'!{}!'.format('_05_end_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# Create 'both ends' nodes data set by merging start nodes and end nodes
print('--merging start and end points')    
merged_pts = arcpy.Merge_management([start_pts, end_pts], os.path.join(scratch_gdb, "_06_merged_pts"))
arcpy.AddField_management(merged_pts, field_name="zcoord", field_type='LONG')

# Remove duplicate nodes (dissolve drops fields, delete identical does not)
print('--deleting duplicate nodes')
arcpy.DeleteIdentical_management(merged_pts, "XY_Key")

# Get Z values from 10m DEM
print('--mosaicing elevation tiles')
elevation_tifs  = glob.glob(os.path.join(r'.\Inputs\Elevation_Tiles', '*.tif'))
elevation = os.path.join(outputs[0], "elevation.tif")
if os.path.exists(elevation) == False:
    arcpy.MosaicToNewRaster_management(elevation_tifs, outputs[0], "elevation.tif", pixel_type="16_BIT_UNSIGNED", cellsize="10", number_of_bands="1", mosaic_method="MEAN")
print('--extracting z values to nodes')
nodes_extract = os.path.abspath(os.path.join(scratch_gdb, '_07_nodes_extract'))
arcpy.sa.ExtractValuesToPoints(merged_pts, elevation, nodes_extract,"NONE", "VALUE_ONLY")
arcpy.CalculateField_management(nodes_extract,"zcoord",'!{}!'.format('RASTERVALU'))
arcpy.DeleteField_management(nodes_extract, "RASTERVALU")

# Remove duplicate nodes, extract z values seems to add duplicates
print('--deleting duplicate nodes (again)')
arcpy.DeleteIdentical_management(nodes_extract, "XY_Key")

arcpy.AddField_management(nodes_extract, field_name="node_id", field_type='LONG')
arcpy.CalculateField_management(nodes_extract,"node_id",'!OBJECTID!-1')

#=====================================
# Create Links
#=====================================
 
print('Creating Links')    
print('--recalculating length')
arcpy.AddField_management(lines_copy_lyr, field_name='Length_Meters', field_type='float')
arcpy.management.CalculateField(lines_copy_lyr, 'Length_Meters', f'!SHAPE_LENGTH!', "PYTHON3")
arcpy.management.CalculateField(lines_copy_lyr, 'Length_Miles', f'!Length_Meters!* 0.000621371', "PYTHON3")
  
arcpy.AddField_management(lines_copy_lyr, field_name="link_id", field_type='LONG')
arcpy.CalculateField_management(lines_copy_lyr,"link_id",'!OBJECTID!-1')

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
bp = ['Trails', '1','1A','1B','1C', 'PP']

# bike blvd codes
bb = ['3B', '3C']

fields = ['BIKE_L', 'BIKE_R', 'SourceData', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd', 'AADT']
print('--setting bike attributes')
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


# Load and buffer traffic signals
print('--adding signal attribute')
buffered_signals = arcpy.Buffer_analysis(traffic_signals, os.path.join(scratch_gdb, "_08_Buffered_Signals"), "20 Meters")

# Perform spatial join
links_signal_join = arcpy.SpatialJoin_analysis(lines_copy_lyr, buffered_signals, os.path.join(scratch_gdb, "_09_links_signal_join"), "JOIN_ONE_TO_ONE", "KEEP_ALL", match_option="INTERSECT")


#=====================================
# Create Linkpoints
#=====================================

if create_linkpoints == True:
    print('Creating Linkpoints')  
    print('--generating all points')
    
    # get all points for each line
    all_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(scratch_gdb, '_10_all_pts'), 'ALL')
    
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
    linkpoints_layer = arcpy.MakeFeatureLayer_management(all_pts,"all_pts_lyr")
    arcpy.AddField_management(linkpoints_layer, field_name="Join_Key", field_type='string')
    arcpy.AddJoin_management(linkpoints_layer, "XY_Key", nodes_extract, 'XY_Key', join_type="KEEP_ALL")
    arcpy.CalculateField_management(linkpoints_layer,"all_pts.Join_Key",'!{}!'.format('_07_nodes_extract.XY_Key'))
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
    print('--extracting z values to linkpoints')
    linkpoints_extract = os.path.abspath(os.path.join(scratch_gdb, '_11_linkpoints_extract'))
    arcpy.sa.ExtractValuesToPoints(linkpoints_layer, elevation, linkpoints_extract,"NONE", "VALUE_ONLY")
    arcpy.CalculateField_management(linkpoints_extract,"zcoord",'!{}!'.format('RASTERVALU'))
    arcpy.DeleteField_management(linkpoints_extract, "RASTERVALU")

    
    # Remove duplicate nodes, extract z values seems to add duplicates
    print('--deleting duplicate linkpoints')
    arcpy.DeleteIdentical_management(linkpoints_extract, "XY_Key")

#=====================================
# read nodes and links into pandas
#=====================================

print('Creating final outputs')

# Read csvs into pandas
nodes_dataframe = pd.DataFrame.spatial.from_featureclass(nodes_extract)  
links_dataframe = pd.DataFrame.spatial.from_featureclass(links_signal_join[0])  
if create_linkpoints == True:
    linkpoints_dataframe = pd.DataFrame.spatial.from_featureclass(linkpoints_extract)  


#-------------------
# format nodes
#-------------------

print('--formatting nodes')
nodes_dataframe_formatted = nodes_dataframe[['node_id', 'xcoord', 'ycoord', 'zcoord', 'XY_Key', 'SHAPE']].copy()
nodes_field_names = ['node_id', 'xcoord', 'ycoord', 'zcoord', 'XY_Key']
nodes_dataframe_formatted.columns = nodes_field_names + ['SHAPE']
nodes_dataframe_formatted = nodes_dataframe_formatted.sort_values(by=['node_id'])

#-------------------
# format links
#-------------------

print('--formatting links')

# Create from/to node columns
links_dataframe = links_dataframe.assign(from_node='', to_node='', from_x='', from_y='', to_x='', to_y='')

# Join with nodes to get start node IDs
links_dataframe_temp = links_dataframe.merge(nodes_dataframe_formatted.drop('SHAPE', axis=1), left_on = 'Start_Key', right_on = 'XY_Key' , how = 'left')
links_dataframe_temp['from_node'] = links_dataframe_temp['node_id']
links_dataframe_temp['from_x'] = links_dataframe_temp['xcoord']
links_dataframe_temp['from_y'] = links_dataframe_temp['ycoord']
links_dataframe_temp.drop(nodes_field_names, axis=1, inplace=True)

# Join with nodes to get end node IDs
links_dataframe_temp = links_dataframe_temp.merge(nodes_dataframe_formatted.drop('SHAPE',  axis=1), left_on = 'End_Key', right_on = 'XY_Key' , how = 'left')
links_dataframe_temp['to_node'] = links_dataframe_temp['node_id']
links_dataframe_temp['to_x'] = links_dataframe_temp['xcoord']
links_dataframe_temp['to_y'] = links_dataframe_temp['ycoord']
links_dataframe_temp.drop(nodes_field_names,  axis=1, inplace=True)

links_dataframe_temp['Signal'] = links_dataframe_temp['Signal'].fillna(0)

# subset and rename columns

links_field_names = ['link_id', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork','PedNetwork', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Miles', 'ConnectorN', 'CartoCode', 'AADT', 'Length_Meters', 'Signal', 'Sig_Count', 'BIKE_L', 'BIKE_R', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd', 'SHAPE']
links_dataframe_formatted = links_dataframe_temp[['link_id', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork', 'PedNetwork', 'DriveTime', 'BikeTime', 'PedestrianTime', 'Length_Miles', 'ConnectorNetwork', 'CartoCode', 'AADT', 'Length_Meters', 'Signal', 'Join_Count','BIKE_L', 'BIKE_R', 'Bike_Lane', 'Bike_Path', 'Bike_Blvd', 'SHAPE']].copy()
links_dataframe_formatted.columns = links_field_names
links_dataframe_formatted = links_dataframe_formatted.sort_values(by=['link_id'])



#------------------------
# Calculate link slope
#------------------------


    
ln_from = links_dataframe_formatted.merge(nodes_dataframe_formatted.drop('SHAPE', axis=1), left_on = 'from_node', right_on = 'node_id' , how = 'inner')
ln_from = ln_from[['link_id', 'zcoord']].copy()
ln_from.columns = ['link_id', 'from_z']

ln_to = links_dataframe_formatted.merge(nodes_dataframe_formatted.drop('SHAPE', axis=1), left_on = 'to_node', right_on = 'node_id' , how = 'inner')
ln_to = ln_to[['link_id', 'zcoord']].copy()
ln_to.columns = ['link_id', 'to_z']

links_df2 = links_dataframe_formatted.merge(ln_from, left_on = 'link_id', right_on = 'link_id' , how = 'inner')
links_df2 = links_df2.merge(ln_to, left_on = 'link_id', right_on = 'link_id' , how = 'inner')

links_df2['Slope_AB'] = ((links_df2['from_z'] - links_df2['to_z']) / links_df2['Length_Meters'] * 100) 
links_df2['Slope_BA'] = ((links_df2['to_z'] - links_df2['from_z']) / links_df2['Length_Meters'] * 100) 
links_df2['Slope_Per'] = abs(links_df2['Slope_AB'])

links_dataframe_formatted = links_df2

#-------------------
# format linkpoints
#-------------------

if create_linkpoints == True:

    print('--formatting linkpoints')
    linkpoints_dataframe = linkpoints_dataframe.assign(link_id='', point_no='')
    linkpoints_dataframe_temp = linkpoints_dataframe.merge(links_dataframe, left_on = 'temp_id', right_on = 'temp_id' , how = 'inner')
    linkpoints_dataframe_temp['link_id'] = linkpoints_dataframe_temp['OBJECTID']
    
    # subset and rename columns
    linkpoints_field_names = ['linkpoint_id','link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']
    linkpoints_dataframe_formatted = linkpoints_dataframe_temp[['OBJECTID', 'link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']].copy()
    linkpoints_dataframe_formatted.columns = linkpoints_field_names
    linkpoints_dataframe_formatted = linkpoints_dataframe_formatted.sort_values(by=['linkpoint_id'])
    linkpoints_dataframe_formatted['point_no'] = linkpoints_dataframe_formatted.groupby('link_id')['link_id'].rank(method='first')




#------------------------------
# write final csvs and shapes
#------------------------------

# export formatted csvs
print('--exporting to csv')
nodes_dataframe_formatted.drop(['XY_Key','SHAPE'], axis=1).to_csv(os.path.join(outputs[0], 'nodes.csv'),index=False)
links_dataframe_formatted.drop('SHAPE', axis=1).to_csv(os.path.join(outputs[0], 'links.csv'),index=False)
if create_linkpoints == True:
    linkpoints_dataframe_formatted.drop('SHAPE', axis=1).to_csv(os.path.join(outputs[0], 'linkpoints.csv'),index=False)


# export links to shapefile
print('--exporting to shape')

links_dataframe_formatted['link_id'] = links_dataframe_formatted['link_id'].astype('Float64')
links_dataframe_formatted['from_node'] = links_dataframe_formatted['from_node'].astype('Float64')
links_dataframe_formatted['to_node'] = links_dataframe_formatted['to_node'].astype('Float64')
nodes_dataframe_formatted['node_id'] = nodes_dataframe_formatted['node_id'].astype('Float64')

links_dataframe_formatted.spatial.to_featureclass(location=os.path.join(network_gdb, 'links'),sanitize_columns=False) 
nodes_dataframe_formatted.spatial.to_featureclass(location=os.path.join(network_gdb, 'nodes'),sanitize_columns=False)  

# =====================================
# Clean up
# =====================================

# if perform_clean_up == True:
#     print('Performing clean-up')
#     trash = [elevation, merged_pts, buffered_signals, lines_copy_lyr, lines_copy, start_pts, end_pts, os.path.join(temp_dir, 'start_pts_initial.shp'),  os.path.join(temp_dir, 'end_pts_initial.shp'), os.path.join(temp_dir, 'temp_lines.shp'), os.path.join(temp_dir, 'nodes_draft.shp')]
#     for item in trash:
#         try:
#             arcpy.Delete_management(item)
#         except:
#             print("--Unable to delete {}".format(item))
#     del item 
    
#     if create_linkpoints == True:
#         arcpy.Delete_management(os.path.join(temp_dir, 'all_pts.shp'))
    
    
#     del elevation
#     del end_pts
#     del lines_copy
#     del lines_copy_lyr
#     del start_pts
#     del merged_pts
#     if create_linkpoints == True:
#         del all_pts
#         del linkpoints_layer

print('Done!')