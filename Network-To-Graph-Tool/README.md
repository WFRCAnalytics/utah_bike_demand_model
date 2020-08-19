# Network-To-Graph-Tool
Converts Multi-modal Network Features to graph format (nodes/links) using Arcpy  
 
**Usage**  
E:\Micromobility\MM_NetworkDataset_04152019.gdb bike --elev E:\Data\Elevation\wf_elev.tif  
E:\Micromobility\MM_NetworkDataset_04152019.gdb bike  
E:\Micromobility\MM_NetworkDataset_04152019.gdb ped  

**Link Attributes**  
link_id: unique identifer    
from_node: from node ID  
from_x: From x-coordinate  
from_y: From y-coordinate  
to_node: to node ID  
to_x: To x-coordinate  
to_y: To y-coordinate  
Name: Street name  
Oneway: Indicates if road is one-way  
Speed: Speed limit in MPH  
AutoNetwork: Indicates if link  is part of Auto Network  
BikeNetwork: Indicates if link  is part of Bike Network   
PedNetwork: Indicates if link  is part of Pedestrian Network  
DriveTime:  
BikeTime:
Pedestrian: 
Length_Miles: link length in miles  
ConnectorN:  
RoadClass:  road class  
AADT: Average Annual Daily Traffic  
Length_Meters:  link length in miles 
Signal: 1) link has traffic signal 0) link does not have traffic signal 
Sig_Count: Number signals associated with link  
from_z: elevation in meters at node A of link  
to_z: elevation in meters at node B  of link  
SlopeAB: Slope percentage (from node - to node)  
SlopeBA: Slope percentage (to node - from node)  
Bike_Path: Indicates whether link is a bike path (bike path class = '1','1A','1B','1C' or SourceData = 'Trails')  
Bike_Lane: Indicates whether link is a bike lane (bike path class = '2','2A','2B', '3A')  
Bike_Blvd: Indicates whether link is a bike boulevard (bike class = '3B' or '3C')  

