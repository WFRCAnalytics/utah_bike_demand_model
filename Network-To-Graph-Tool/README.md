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
DriveTime: (No longer reliable)  
BikeTime:  (No longer reliable)  
Pedestrian:  (No longer reliable)  
Length_Miles:  
ConnectorN:  
RoadClass:  road class  
AADT: Average Annual Daily Traffic  
Length_Meters:  



**Notes**  
May need to consider removing disconnected lines from network before creating nodes and links.  
These two tool would be useful for this:  
https://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/create-geometric-network.htm  
https://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/find-disconnected-features-in-geometric-network.htm  