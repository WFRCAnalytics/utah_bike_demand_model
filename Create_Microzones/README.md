# Create Microzones for bike model

**Steps**

*Create microzones from utah roads network line features*  

Add attributes from REMM  
- residences
- population
- households
- jobs

*Add atrributes from TDM*  
- Average Income
- Elementary School Enrollment
- Middle School Enrollment
- High School Enrollment
- Life Cycles
- Age Groups

*Add attributes from AGRC*  
- Parks
- Schools
- Trailheads
- Light Rail Stops
- Commuter Rail Stops


## Microzone Attributes

*REMM: Real Estate Market Model (WFRC/MAG MPO Areas) 
TDM: Wasatch Front Travel Demand Model (WFRC/MAG MPO Areas) 
AGRC: Utah Automated Geographic Resource Center (gis.utah.gov)*  

**Households**  
Description: Number of households (residential units that are occupied)  
Source: REMM  

**Residentia**  
Description: Number of residential units  
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

**POP_LC1**  
Description: Total Population LC1 (households with no children and seniors)  
Source: TDM  

**POP_LC2**  
Description: Total Population LC2 (households with children and no seniors)  
Source: TDM  

**POP_LC3**  
Description: Total Population LC3 (households with seniors and may have children)  
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

**TH_SCORE**  
Description: Scores determining attractiveness of trailheads 3) very attractive 2) moderately attractive 1) slightly attractive 0) no trail head
Source: AGRC 

**LIGHT_RAIL**  
Description: Presence of a light rail station  1) yes, 0) no  
Source: AGRC  

**COMM_RAIL**  
Description: Presence of commuter rail station  1) yes, 0) no  
Source: AGRC

**GQU_RATIO**
Description: Percentage university student group quarters population by zone (group quarters / total population, where student housing is located)
Source: American Community Survey  

**area_sqm**  
Description: Area square meters  
Source: Self  

**area_acres**  
Description: Area acres
Source: Self  
