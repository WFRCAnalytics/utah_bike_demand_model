
"""
Created on Mon Mar 30 08:18:19 2020

@author: jreynolds bgranberg 

E:\Micromobility\MM_NetworkDataset_04152019.gdb bike --elev E:\Data\Elevation\wf_elev.tif
E:\Micromobility\MM_NetworkDataset_04152019.gdb bike
E:\Micromobility\MM_NetworkDataset_04152019.gdb ped

"""

import arcpy
import argparse
import os
import pandas as pd
from arcpy.sa import *

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

def main():
     
    # Command line arguments
    parser = argparse.ArgumentParser("Convert Multimodal Network to Node/Link format")
    parser.add_argument('multimodal_network', type=str, help='input multimodal network gdb from WFRC')
    parser.add_argument('mode', type=str, choices=['bike','ped', 'auto'], help='bike, auto, or ped')
    parser.add_argument('--elev', type=str, help='path to overlapping elevation dataset')
    args = parser.parse_args()
    
    # print(args.multimodal_network)
    # print(args.mode)
    # print(args.elev)
    
    # temporary directory
    temp_dir = os.path.join(os.getcwd(), 'Results')
    
    # determine network dataset to process
    mm_network = args.multimodal_network
    mode = args.mode
    
    if mode == 'bike':
        network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'BikeNetwork')
    if mode == 'auto':
        network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'AutoNetwork')
    if mode == 'ped':
        network = os.path.join(os.path.join(mm_network, 'NetworkDataset'), 'PedNetwork')
    
    print("converting: {}...".format(network))
    
    # Store elevation dataset, if provided
    elevation = args.elev
    
    # Cleanup files toggle
    perform_clean_up = True
    
    #=====================================
    # Prep data
    #=====================================
    
    study_area = os.path.join(os.getcwd(), 'Data', 'TAZ_WFRC_UTM12.shp')
    
    # Copy centerlines by clipping to TAZ study area
    lines_copy = arcpy.Clip_analysis(network, study_area, os.path.join(temp_dir, 'temp_lines.shp'))
    #lines_copy = arcpy.FeatureClassToFeatureClass_conversion(network, temp_dir, 'temp_lines.shp')
    lines_copy_lyr = arcpy.MakeFeatureLayer_management(lines_copy,"temp_lines_lyr")
    
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
    start_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'start_pts.shp'), 'START')
    
    # add xy coords to start points
    arcpy.AddField_management(start_pts, field_name="xcoord", field_type='double')
    arcpy.AddField_management(start_pts, field_name="ycoord", field_type='double')
    arcpy.CalculateGeometryAttributes_management(start_pts, [["xcoord", "POINT_X"],["ycoord", "POINT_Y"]])
    
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
    end_pts = arcpy.FeatureVerticesToPoints_management(lines_copy_lyr, os.path.join(temp_dir, 'end_pts.shp'), 'END')
    
    # add xy coords to end points
    arcpy.AddField_management(end_pts, field_name="xcoord", field_type='double')
    arcpy.AddField_management(end_pts, field_name="ycoord", field_type='double')
    arcpy.CalculateGeometryAttributes_management(end_pts, [["xcoord", "POINT_X"], ["ycoord", "POINT_Y"]])
    
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
    
    
    #=====================================
    # Create Links
    #=====================================
     
    print('Creating Links')    
    links_final = arcpy.FeatureClassToFeatureClass_conversion(lines_copy_lyr, temp_dir, 'links.shp')
    
    # recalc meters and miles
    with arcpy.da.UpdateCursor(links_final, ['Length_Mil', 'Shape_Leng', 'SHAPE@LENGTH']) as cursor:
        for row in cursor:
            
            row[0] = row[2]
            
            # meters to miles
            row[1] = row[2] * 0.000621371
            cursor.updateRow(row)    
    
    
    #=====================================
    # Create Linkpoints
    #=====================================
    
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
    
    
    
    #=====================================
    # Create CSV Tables
    #=====================================
    
    print('Creating table outputs')
    
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
    # links_field_names = ['link_id', 'from_node', 'to_node', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork','PedNetwork', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Miles', 'ConnectorN', 'RoadClass', 'AADT', 'Length_Meters']
    # links_dataframe_formatted = links_dataframe_temp[['FID', 'from_node', 'to_node','Name_x', 'Oneway_x', 'Speed_x', 'AutoNetwor_x', 'BikeNetwor_x', 'PedNetwork_x', 'DriveTime_x', 'BikeTime_x', 'Pedestrian_x', 'Length_Mil_x', 'ConnectorN_x', 'RoadClass_x', 'AADT_x', 'Shape_Leng_x']].copy()
    links_field_names = ['link_id', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name', 'Oneway', 'Speed', 'AutoNetwork', 'BikeNetwork','PedNetwork', 'DriveTime', 'BikeTime', 'Pedestrian', 'Length_Miles', 'ConnectorN', 'RoadClass', 'AADT', 'Length_Meters']
    links_dataframe_formatted = links_dataframe_temp[['FID', 'from_node', 'from_x', 'from_y', 'to_node', 'to_x', 'to_y', 'Name_x', 'Oneway_x', 'Speed_x', 'AutoNetwor_x', 'BikeNetwor_x', 'PedNetwork_x', 'DriveTime_x', 'BikeTime_x', 'Pedestrian_x', 'Length_Mil_x', 'ConnectorN_x', 'RoadClass_x', 'AADT_x', 'Shape_Leng_x']].copy()
    links_dataframe_formatted.columns = links_field_names
    links_dataframe_formatted = links_dataframe_formatted.sort_values(by=['link_id'])
    
    #-------------------
    # format linkpoints
    #-------------------
    
    print('--formatting linkpoints')
    linkpoints_dataframe = linkpoints_dataframe.assign(link_id='', point_no='')
    linkpoints_dataframe_temp = linkpoints_dataframe.merge(links_dataframe, left_on = 'id', right_on = 'id' , how = 'inner')
    linkpoints_dataframe_temp['link_id'] = linkpoints_dataframe_temp['FID_y']
    
    # subset and rename columns
    linkpoints_field_names = ['linkpoint_id','link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']
    linkpoints_dataframe_formatted = linkpoints_dataframe_temp[['FID_x', 'link_id', 'point_no', 'xcoord', 'ycoord', 'zcoord']].copy()
    linkpoints_dataframe_formatted.columns = linkpoints_field_names
    linkpoints_dataframe_formatted = linkpoints_dataframe_formatted.sort_values(by=['linkpoint_id'])
    
    #-----------------
    # write final csvs
    #-----------------
    
    # export formatted csvs
    print('--exporting to csv')
    nodes_dataframe_formatted.to_csv(os.path.join(temp_dir, 'nodes.csv'),index=False)
    links_dataframe_formatted.to_csv(os.path.join(temp_dir, 'links.csv'),index=False)
    linkpoints_dataframe_formatted.to_csv(os.path.join(temp_dir, 'linkpoints.csv'),index=False)
    
    #=====================================
    # Clean up
    #=====================================
    
    if perform_clean_up == True:
        print('Performing clean-up')
        trash = [merged_pts, all_pts, lines_copy_lyr, lines_copy, start_pts, end_pts]
        for item in trash:
            try:
                arcpy.Delete_management(item)
            except:
                print("--Unable to delete {}".format(item))
        del item 
            
        # remove temp csvs
        os.remove(os.path.join(temp_dir, 'nodes_temp.csv'))
        os.remove(os.path.join(temp_dir, 'links_temp.csv'))
        os.remove(os.path.join(temp_dir, 'linkpoints_temp.csv'))
        os.remove(os.path.join(temp_dir, 'nodes_temp.csv.xml'))
        os.remove(os.path.join(temp_dir, 'links_temp.csv.xml'))
        os.remove(os.path.join(temp_dir, 'linkpoints_temp.csv.xml'))
        
        del all_pts
        del elevation
        del end_pts
        del lines_copy
        del lines_copy_lyr
        del start_pts
        del linkpoints_layer
        del links_final
        del merged_pts
    
    print('Done!')


if __name__ == '__main__':
    main()
