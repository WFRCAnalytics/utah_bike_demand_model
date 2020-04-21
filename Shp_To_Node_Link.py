
"""
Created on Mon Mar 30 08:18:19 2020

@author: jreynolds
"""

import arcpy
import os
import pandas as pd
from arcpy.sa import *

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")


"""
PREPARE LINKS
With road feature class
Add StartKey text 20
Add EndKey text 20
Feature vertices to points for start points
Calc XYKey  like 412345|4456789
Join back to road feature class based on road feature id
Calculate StartKey
Feature vertices to points for end points
Calc XYKey like 412345|4456789 - this 
Join back to road feature class based on road feature id
Calculate EndKey

PREPARE NODES
Do this (or just use delete identical) 
Combine start points and end points into one ‘allendpoints’ featureclass
Add z coordinates
(Just for fun -- Summarize on XYKey to get a count (4 way surface intersection will have 4 points present, the end of culdesac/deadend/end of road at state boundary will have justone) of endpoints at each location)
Dissolve this dataset based on XYKey to reduce points down to a single point at each locations (these are your nodes) 

PREPARE LINKPOINTS
FeatureVertices to Points All points
Calc XYKey  like 412345|4456789
Join to ‘allendpoints’ based on XYKey
Delete all records where the join is successful
Add z coordinates
"""

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

#====================
# USER ARGS
#====================

# temporary directory
temp_dir = r'E:\Micromobility\Network_Datasets_Shapefiles\Shp_To_NL\data'

# input network dataset
input_roads = r"E:\Micromobility\Network_Datasets_Shapefiles\BikeNetwork.shp"
unique_id_field = 'id'

# Input elevation raster for z coordinates
elevation = r'E:\Data\Elevation\wf_elev.tif'

#====================
# MAIN
#====================

# Copy centerlines
lines_copy = arcpy.FeatureClassToFeatureClass_conversion(input_roads, temp_dir, 'temp_lines.shp')
lines_copy_lyr = arcpy.MakeFeatureLayer_management(lines_copy,"temp_lines_lyr")

#--------------------
# Start points
#--------------------

print('generating start points')

# get start points for each line, 
start_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'start_pts.shp'), 'START')

# add xy coords to start points
arcpy.AddField_management(start_pts, field_name="xcoord", field_type='double')
arcpy.AddField_management(start_pts, field_name="ycoord", field_type='double')
arcpy.CalculateGeometryAttributes_management(start_pts, [["xcoord", "POINT_X"],
                                                    ["ycoord", "POINT_Y"]])
# create xy key to start points
arcpy.AddField_management(start_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(start_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))

#--------------------
# End points
#--------------------

print('generating end points')

# get end points for each line
end_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'end_pts.shp'), 'END')

# add xy coords to end points
arcpy.AddField_management(end_pts, field_name="xcoord", field_type='double')
arcpy.AddField_management(end_pts, field_name="ycoord", field_type='double')
arcpy.CalculateGeometryAttributes_management(end_pts, [["xcoord", "POINT_X"],
                                                    ["ycoord", "POINT_Y"]])
# add xy key to end points
arcpy.AddField_management(end_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(end_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))

#--------------------
# All points
#--------------------

print('generating  all points')

# get all points for each line
all_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'all_pts.shp'), 'ALL')

# add xy coords to all points
arcpy.AddField_management(all_pts, field_name="xcoord", field_type='double')
arcpy.AddField_management(all_pts, field_name="ycoord", field_type='double')
arcpy.CalculateGeometryAttributes_management(all_pts, [["xcoord", "POINT_X"],["ycoord", "POINT_Y"]])

# add xy key to all points
arcpy.AddField_management(all_pts, field_name="XY_Key", field_type='string')
arcpy.CalculateField_management(all_pts,"XY_Key",'"!{}!|!{}!"'.format('xcoord', 'ycoord'))

# remove duplicates in case they exist
arcpy.DeleteIdentical_management(all_pts, "XY_Key")

#--------------------
# Node/Link Processing
#--------------------

# join with centerlines, copy xy key
arcpy.AddJoin_management(lines_copy_lyr, unique_id_field, start_pts, unique_id_field)
arcpy.CalculateField_management(lines_copy_lyr,"Start_Key",'!{}!'.format('start_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# join with centerlines, copy xy key
arcpy.AddJoin_management(lines_copy_lyr, unique_id_field, end_pts, unique_id_field)
arcpy.CalculateField_management(lines_copy_lyr,"End_Key",'!{}!'.format('end_pts.XY_Key'))
arcpy.RemoveJoin_management (lines_copy_lyr)

# Create 'both ends' nodes data set by merging start nodes and end nodes
print('merging start and end points')
merged_pts = arcpy.Merge_management([start_pts, end_pts], os.path.join(temp_dir, "merged_pts.shp"))

# Remove duplicate nodes (dissolve drops fields, delete identical does not)
print('deleting duplicate nodes')
arcpy.DeleteIdentical_management(merged_pts, "XY_Key")

# Join all nodes to both ends nodes and calculate a field to use for tracking start/end nodes
print('working on linkpoints')
all_pts_lyr = arcpy.MakeFeatureLayer_management(all_pts,"all_pts_lyr")
arcpy.AddField_management(all_pts_lyr, field_name="Join_Key", field_type='string')
arcpy.AddJoin_management(all_pts_lyr, "XY_Key", merged_pts, 'XY_Key', join_type="KEEP_ALL")
arcpy.CalculateField_management(all_pts_lyr,"all_pts.Join_Key",'!{}!'.format('merged_pts.XY_Key'))
arcpy.RemoveJoin_management(all_pts_lyr)

# Use update cursor to delete start and end nodes from linkpoints
print('Deleting Start/End Nodes from linkpoints')
total_joined_nodes = 0
with arcpy.da.UpdateCursor(all_pts_lyr, ['Join_Key']) as cursor:
    for row in cursor:
        if row[0] != ' ':
            cursor.deleteRow()
            total_joined_nodes += 1
    
del cursor
print("Total Nodes deleted: {}".format(total_joined_nodes))
arcpy.DeleteField_management(all_pts_lyr, 'Join_Key')

# Get Z values from 10m DEM

print('extracting z values to nodes')
nodes_final = ExtractValuesToPoints(merged_pts, elevation, os.path.join(temp_dir, 'nodes.shp'))
arcpy.AddField_management(nodes_final, field_name="zcoord", field_type='LONG')
arcpy.CalculateField_management(nodes_final,"zcoord",'!{}!'.format('RASTERVALU'))
arcpy.DeleteField_management(nodes_final, "RASTERVALU")

print('extracting z values to linkpoints')
linkpoints_final = ExtractValuesToPoints(all_pts_lyr, elevation, os.path.join(temp_dir, 'linkpoints.shp'))
arcpy.AddField_management(linkpoints_final, field_name="zcoord", field_type='LONG')
arcpy.CalculateField_management(linkpoints_final,"zcoord",'!{}!'.format('RASTERVALU'))
arcpy.DeleteField_management(linkpoints_final, "RASTERVALU")

# Export links shapefile
links_final = arcpy.FeatureClassToFeatureClass_conversion(lines_copy_lyr, temp_dir, 'links.shp')

#====================
# Clean up
#====================

trash = [all_pts_lyr, all_pts, merged_pts, lines_copy_lyr, lines_copy, start_pts, end_pts]
for item in trash:
    try:
        arcpy.Delete_management(item)
    except:
        print("Unable to delete {}".format(item))

del all_pts
del all_pts_lyr
del elevation
del end_pts
del input_roads
del lines_copy
del lines_copy_lyr
del merged_pts
del start_pts

#====================
# CSV Formatting
#====================

print('formatting csvs')

# Convert shapefiles to csv for formatting in Pandas
arcpy.TableToTable_conversion(nodes_final, temp_dir, 'nodes_temp.csv')
arcpy.TableToTable_conversion(links_final, temp_dir, 'links_temp.csv')
arcpy.TableToTable_conversion(linkpoints_final, temp_dir, 'linkpoints_temp.csv')

# Read csvs into pandas
nodes_dataframe = pd.read_csv(os.path.join(temp_dir, 'nodes_temp.csv'))
links_dataframe = pd.read_csv(os.path.join(temp_dir, 'links_temp.csv'))
linkpoints_dataframe = pd.read_csv(os.path.join(temp_dir, 'linkpoints_temp.csv'))

#-------------------
# format nodes
#-------------------

nodes_field_names = ['node_id', 'xcoord', 'ycoord', 'zcoord']
nodes_dataframe_formatted = nodes_dataframe.iloc[:,[0,21,22,24]].copy()
nodes_dataframe_formatted.columns = nodes_field_names
nodes_dataframe_formatted = nodes_dataframe_formatted.sort_values(by=['node_id'])

#-------------------
# format links
#-------------------

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


links_field_names = ['link_id', 'from_node', 'to_node', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork','PedNetwork', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Miles', 'ConnectorN', 'RoadClass', 'AADT', 'Length_Meters', 'class']
links_dataframe_formatted = links_dataframe_temp.iloc[:,[0,22,23,2,3,4,5,6,7,9,10,11,12,13,14,15,17,18]].copy()
links_dataframe_formatted.columns = links_field_names
links_dataframe_formatted = links_dataframe_formatted.sort_values(by=['link_id'])
#-------------------
# format linkpoints
#-------------------

linkpoints_dataframe = linkpoints_dataframe.assign(link_id='', point_no='')
linkpoints_dataframe_temp = linkpoints_dataframe.merge(links_dataframe, left_on = 'id', right_on = 'id' , how = 'inner')
linkpoints_dataframe_temp['link_id'] = linkpoints_dataframe_temp['FID_y']

linkpoints_field_names = ['linkpoint_id','link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']
linkpoints_dataframe_formatted = linkpoints_dataframe_temp.iloc[:,[0,25,26,21,22,24]].copy()
linkpoints_dataframe_formatted.columns = linkpoints_field_names
linkpoints_dataframe_formatted = linkpoints_dataframe_formatted.sort_values(by=['linkpoint_id'])
#-----------------
# overwrite csvs
#-----------------

# export formatted csvs
nodes_dataframe_formatted.to_csv(os.path.join(temp_dir, 'nodes.csv'),index=False)
links_dataframe_formatted.to_csv(os.path.join(temp_dir, 'links.csv'),index=False)
linkpoints_dataframe_formatted.to_csv(os.path.join(temp_dir, 'linkpoints.csv'),index=False)

# remove temp csvs
os.remove(os.path.join(temp_dir, 'nodes_temp.csv'))
os.remove(os.path.join(temp_dir, 'links_temp.csv'))
os.remove(os.path.join(temp_dir, 'linkpoints_temp.csv'))

