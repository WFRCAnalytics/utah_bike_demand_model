## Link Attributes  

*link_id:*  
Description:unique identifer    

*from_node:* 
Description: from node ID  

*from_x:*  
Description: From x-coordinate  

*from_y:*  
Description: From y-coordinate  

*to_node:*  
Description: to node ID  

*to_x:*  
Description: To x-coordinate  

*to_y:*  
Description: To y-coordinate  

*Name:*  
Description: Street name  

*Oneway:*  
Description: Indicates if road is one-way  

*Speed:*  
Description: Speed limit in MPH  

*AutoNetwork:*  
Description: Indicates if link  is part of Auto Network  

*BikeNetwork:*  
Description: Indicates if link  is part of Bike Network   

*PedNetwork:*  
Description: Indicates if link  is part of Pedestrian Network  

*DriveTime:*    
Description:  

*BikeTime:*  
Description:  

*Pedestrian:*   
Description:  

*Length_Miles:*   
Description: link length in miles  

*ConnectorN:*    
Description:  

*RoadClass:*    
Description: road class description 

*AADT:*   
Description:Average Annual Daily Traffic  

*Length_Meters:*    
Description:link length in miles 

*Signal:*   
Description:1) link has traffic signal 0) link does not have traffic signal  

*Sig_Count:*   
Description:Number signals associated with link  

*from_z:*   
Description:elevation in meters at node A of link  

*to_z:*   
Description:elevation in meters at node B  of link  

*SlopeAB:*   
Description:Slope percentage (from node - to node)  

*SlopeBA:*   
Description:Slope percentage (to node - from node)  

*Slope_Per:*   
Description:Absolute value of slope percentage  

*Bike_Path:*   
Description:Indicates whether link is a bike path (bike path class = '1','1A','1B','1C' or SourceData = 'Trails')  

*Bike_Lane:*   
Description:Indicates whether link is a bike lane (bike path class = '2','2A','2B', '3A')  

*Bike_Blvd:*   
Description:Indicates whether link is a bike boulevard (bike class = '3B' or '3C')  


## Microzone Attributes

*REMM: Real Estate Market Model (WFRC/MAG MPO Areas)*  
*TDM: Wasatch Front Travel Demand Model (WFRC/MAG MPO Areas)*  
*AGRC: Utah Automated Geographic Resource Center (gis.utah.gov)*  

**Residentia**  
Description: Number of residential units  
Source: REMM  

**Households**  
Description: Number of households (residential units that are occupied)  
Source: REMM  

**Population**  
Description: Total population  
Source: REMM  

**jobs1**  
Description: Number of Accommodation, Food Services Jobs  
Source: REMM  

**jobs3**  
Description: Number of Government and Education jobs  
Source: REMM  

**jobs4**  
Description: Number of Health Care jobs  
Source: REMM  

**jobs5**  
Description: Number of Manufacturing jobs  
Source: REMM  

**jobs6**  
Description: Number of Office jobs  
Source: REMM  

**jobs7**  
Description: Number of Other Jobs (non-typical commuting/travel patterns) 
Source: REMM  

**jobs9**  
Description: Number of Retail Trade jobs  
Source: REMM  

**job10**  
Description: Number of Wholesale, transport jobs  
Source: REMM  

**jobs_total**  
Description: Total jobs (1,3,4,5,6,7,9,10)  
Source: REMM  

**AVGINCOME**  
Description: Mean income  
Source: TDM    

**ENROL_ELEM**  
Description: Elementary school enrollment / population
Source: TDM    

**ENROL_MIDL**  
Description: Middle school enrollment  / population
Source: TDM   

**ENROL_HIGH**  
Description: High school enrollment  / population
Source: TDM    

**HHSIZE_LC1**  
Description: Mean Number of residents per household LC1 (households with no children and seniors)  
Source: TDM  

**HHSIZE_LC2**   
Description: Mean Number of residents per household LC2 (households with children and no seniors)  
Source: TDM  

**HHSIZE_LC3**  
Description:Mean Number of residents per household LC3 (households with seniors and may have children)  
Source: TDM  

**PCT_POPLC1**  
Description: Population Percentage LC1 (households with no children and seniors)    
Source: TDM 

**PCT_POPLC2**  
Description: Population Percentage LC2 (households with children and no seniors)  
Source: TDM

**PCT_POPLC3**  
Description: Population Percentage LC3 (households with seniors and may have children)  
Source: TDM  

**PCT_AG1**  
Description:Population Percentage AG1 (Children - 0 to 17)  
Source: TDM  

**PCT_AG2**  
Description:Population Percentage AG2 (Adults - 18 to 64)  
Source: TDM  

**PCT_AG3**  
Description:Population Percentage AG3 (Seniors - 65 +)  
Source: TDM  

**INC1**  
Description: Income Group 1 Percentage   $0 to 34,999  
Source:TDM  

**INC2**  
Description: Income Group 2 Percentage $35,000 to 49,999  
Source:TDM  

**INC3**  
Description: Income Group 3 Percentage $50,000 to 99,999  
Source:TDM  

**INC4**  
Description: Income Group 4 Percentage $100,000+   
Source:TDM  

**PARK_SCORE**  
Description: Presence of desirable park spaces. 1) Acreage > 10, 2) 5 < Acreage < 10, 3)  Acreage < 5  
Source: AGRC   

**SCHOOL_CD**  
Description: Presence of schools. 0) none, 1) Adult High, Residential Treatment, Alternative, Online 2) high schools, Higher Education 3) Elementary/Middle school,
Source: AGRC  

**COLL_ENROLL**  
Description: 2019 enrollment estimates from  
Source: various sources e.g. utah department of education  

**ldr_score**  
Description: Scores determining attractiveness of long distance rec trailheads 3) very attractive 2) moderately attractive 1) slightly attractive 0) no trail head
Source: AGRC  

**mtbh_score**  
Description: Scores determining attractiveness of mountain bike and hiking trailheads 3) very attractive 2) moderately attractive 1) slightly attractive 0) no trail head
Source: AGRC  

**TH_SCORE**  
Description: Scores determining attractiveness of trailheads 3) very attractive 2) moderately attractive 1) slightly attractive 0) no trail head
Source: AGRC 

**COMM_RAIL**  
Description: Presence of commuter rail station  1) yes, 0) no  
Source: AGRC

**LIGHT_RAIL**  
Description: Presence of a light rail station  1) yes, 0) no  
Source: AGRC 

**GQU_RATIO**  
Description: Percentage university student group quarters population by zone (group quarters / total population, where student housing is located)
Source: American Community Survey  

**industrial**
Description: 1) zone overlaps with industrial district 0) zone does not overlap with industrial district  
Source: WFRC Regionally significant centers and land use data layer    

**bike_share**
Description: score given to zones that represents bike share attractiveness 5) best 3) good 1) okay 0) none  
Source: Greenbike docks points buffered

**NODE_ID**  
Description: Centroid Node ID within microzone (closest node to true zone centroid)
Source: nodes dataset (converted from multimodal network)  

**MIXED_USE**  
Description: (households * jobs_total) / (households + jobs_total)
Source:  REMM  

**bklane_len**  
Description: total length (miles) of bike lanes within .25 miles of each zone   
Source: links dataset (converted from multimodal network)   

**bkpath_len**  
Description: total length (miles) of bike paths within .25 miles of each zone  
Source: links dataset (converted from multimodal network)  

**AREA_SQMIL**  
Description: Area in square miles  
Source: Self  


