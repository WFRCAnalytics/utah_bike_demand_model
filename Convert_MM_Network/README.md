# Convert_MM_Network
Converts Multi-modal Network Features to graph format (nodes/links) using Arcpy  
 
**Usage**  
E:\Micromobility\MM_NetworkDataset_04152019.gdb bike --elev E:\Data\Elevation\wf_elev.tif  
E:\Micromobility\MM_NetworkDataset_04152019.gdb bike  
E:\Micromobility\MM_NetworkDataset_04152019.gdb ped  

**Input Data**  
https://drive.google.com/file/d/1Ovpx-hWZtIfUo2b2dqYNwQlRfErHONx6/view

**Notes**  
May need to consider removing disconnected lines from network before creating nodes and links.  
These two tool would be useful for this:  
https://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/create-geometric-network.htm  
https://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/find-disconnected-features-in-geometric-network.htm  
