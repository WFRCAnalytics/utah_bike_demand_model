#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import numpy as np
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor


# In[2]:


# show all columns
pd.options.display.max_columns = None


# ## Join Bike volume data to links

# In[3]:


# read in links csv
links = pd.read_csv(r".\Model_Outputs\links.csv")

# read in links shapefile
links_shp = pd.DataFrame.spatial.from_featureclass(r".\Model_Outputs\links.shp")
print(links.shape)
print(links_shp.shape)


# In[4]:


# read in bike volume
bike_volume = pd.read_csv(r".\Model_Outputs\bike_vol.csv")

#should be double the amount of links for both directions
print(bike_volume.shape)

# fill bike volume NAs with -1
bike_volume['bike_vol'] = bike_volume['bike_vol'].fillna(0)


# REMOVE THIS WHEN TABLE BUG IS FIXED
bike_volume.dropna(inplace=True)

# convert node ids to int
bike_volume['from_node'] = bike_volume['from_node'].astype(int)
bike_volume['to_node'] = bike_volume['to_node'].astype(int)


# In[5]:


# Create key to use for joining to links
bike_volume['key'] = np.where(bike_volume['from_node'] < bike_volume['to_node'], 
                              bike_volume['from_node'].astype(str) + "_"+ bike_volume['to_node'].astype(str), 
                              bike_volume['to_node'].astype(str) + "_"+ bike_volume['from_node'].astype(str))

# Create directional keys
bike_volume['ft_key'] = bike_volume['from_node'].astype(str) + "_"+ bike_volume['to_node'].astype(str)
bike_volume['tf_key'] = bike_volume['to_node'].astype(str) + "_"+ bike_volume['from_node'].astype(str)

bike_volume.head(15)


# In[6]:


# summarize trips in each direction
ft_vol_sum = pd.DataFrame(bike_volume.groupby('ft_key')['bike_vol'].sum())
tf_vol_sum = pd.DataFrame(bike_volume.groupby('tf_key')['bike_vol'].sum())

ft_vol_sum.columns = ['ft_bvol']
tf_vol_sum.columns = ['tf_bvol']

tf_vol_sum.head()


# In[7]:


# summarize trips in both directions
volume_sum = pd.DataFrame(bike_volume.groupby('key')['bike_vol'].sum())
volume_sum.columns = ['total_bvol']
volume_sum.head(10)


# In[8]:


#Create FTkey and TF key to use for joining to bike volumes
links['key'] = np.where(links['from_node'].astype(int) < links['to_node'].astype(int), 
                              links['from_node'].astype(str) + "_"+ links['to_node'].astype(str), 
                              links['to_node'].astype(str) + "_"+ links['from_node'].astype(str))

links[['from_node', 'to_node','key']].head(10)


# In[9]:


# copy the links table
links2 = links[['link_id', 'key']].copy()

# join the links with the bike volumes using the common keys
link_bike_vol = links2.merge(volume_sum, left_on='key', right_on='key', how='left')
link_bike_vol2 = link_bike_vol.merge(ft_vol_sum, left_on='key', right_on='ft_key', how='left')
link_bike_vol3 = link_bike_vol2.merge(tf_vol_sum, left_on='key', right_on='tf_key', how='left')

# examine the results
print(links2.shape)
print(link_bike_vol3.shape)


# In[10]:


link_bike_vol3.head(5)


# In[11]:


# Examine the column names
links_shp.columns


# In[12]:


# export final result to csv
link_bike_vol3['link_id'] = link_bike_vol3['link_id'].astype('int64')

# join bike vol to links shapefile
links4 = links_shp.merge(link_bike_vol3, left_on='link_id', right_on='link_id', how='left')

links4.fillna(0, inplace=True)


# export to shape
links4.spatial.to_featureclass(location=r".\Default.gdb\links_bv")


# ## Summarize zone trips by Attracting/Producing Zone

# In[13]:


# read in zones
zones = pd.DataFrame.spatial.from_featureclass(r".\Model_Outputs\microzones.shp")
zones.head()


# ### Read in trip tables, summarize, and format

# In[14]:


def summarize_zones(trips_df, name):
    
    # summarize trips by attraction or production
    trips_sum_attr = pd.DataFrame(trips_df.groupby('azone')['trips'].sum())
    trips_sum_prod = pd.DataFrame(trips_df.groupby('pzone')['trips'].sum())
    
    # format tables
    trips_sum_attr['zone_id'] = trips_sum_attr.index
    trips_sum_attr.columns = [name + '_abk', 'zone_id']
    trips_sum_prod['zone_id'] = trips_sum_prod.index
    trips_sum_prod.columns = [name + '_pbk', 'zone_id']
    
    # join the attraction and production summary tables using zone id
    merged = trips_sum_attr.merge(trips_sum_prod, left_on='zone_id', right_on='zone_id', how='outer')
    return merged
    


# In[15]:


# sch_univ = pd.read_csv(r".\Data\sch_univ_trip.csv")
# sch_univ_sum = summarize_zones(sch_univ, 'univ')
# sch_univ_sum.isnull().values.any()


# In[16]:


# Discretionary trips (social trips, some recreation)
disc = pd.read_csv(r".\Model_Outputs\disc_trip.csv")
disc_sum = summarize_zones(disc, 'disc')
del disc

# Maintenance trips (e.g. groceries)
maint = pd.read_csv(r".\Model_Outputs\maint_trip.csv")
maint_sum = summarize_zones(maint, 'mnt')
del maint

# Maintenance trips non-home-based (e.g. groceries)
maint_nhb = pd.read_csv(r".\Model_Outputs\maint_nhb_trip.csv")
maint_nhb_sum = summarize_zones(maint_nhb, 'mntnhb')
del maint_nhb

# Recreational family trips
rec_fam = pd.read_csv(r".\Model_Outputs\rec_fam_trip.csv")
rec_fam_sum = summarize_zones(rec_fam, 'recfam')
del rec_fam

# Recreation long trips
rec_long = pd.read_csv(r".\Model_Outputs\rec_long_trip.csv")
rec_long_sum = summarize_zones(rec_long, 'reclng')
del rec_long

# Recreation mountain bike trips
rec_mtb = pd.read_csv(r".\Model_Outputs\rec_mtb_trip.csv")
rec_mtb_sum = summarize_zones(rec_mtb, 'recmtb')
del rec_mtb

# Recreation other trips (recreation that doesn't fall into family or long)
rec_oth = pd.read_csv(r".\Model_Outputs\rec_oth_trip.csv")
rec_oth_sum = summarize_zones(rec_oth, 'recoth')
del rec_oth

# school (grade) trips
sch_grade = pd.read_csv(r".\Model_Outputs\sch_grade_trip.csv")
sch_grade_sum = summarize_zones(sch_grade, 'grade')
del sch_grade

# school (university) trips
sch_univ = pd.read_csv(r".\Model_Outputs\sch_univ_trip.csv")
sch_univ_sum = summarize_zones(sch_univ, 'univ')
del sch_univ

# Work trips
work = pd.read_csv(r".\Model_Outputs\work_trip.csv")
work_sum = summarize_zones(work, 'wrk')
del work

# Work non-home-based trips
work_nhb = pd.read_csv(r".\Model_Outputs\work_nhb_trip.csv")
work_nhb_sum = summarize_zones(work_nhb, 'wrknhb')
del work_nhb


# In[17]:


rec_fam_sum


# In[18]:


zones


# ### Merge trip summaries back to microzone shapefile

# In[19]:


# Create a clean copy of zones dataset
# zones2 = zones[['zone_id', 'co_tazid', 'tazid', 'co_fips', 'co_name', 'SHAPE']].copy()
zones2 = zones[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'AREA_SQMIL', 'SHAPE']].copy()
zones2['zone_id'] = zones2['zone_id'].astype('int64')



# Join trip tables
zones2 = zones2.merge(disc_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(maint_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(maint_nhb_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(rec_fam_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(rec_long_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(rec_mtb_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(rec_oth_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(sch_grade_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(sch_univ_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(work_sum, left_on='zone_id', right_on='zone_id', how='left')
zones2 = zones2.merge(work_nhb_sum, left_on='zone_id', right_on='zone_id', how='left')




# preview table
zones2.head(5)


# In[20]:


zones2.columns


# In[21]:


# fill na's with 0
zones3 = zones2

# fill NAs where necessary
for field in list(zones3.columns):
    if field not in ['SHAPE']:
        zones3[field].fillna(0, inplace=True)

# calc totals        
zones3['total_abk'] = (zones3['disc_abk'] + zones3['mnt_abk'] + zones3['mntnhb_abk'] + 
                       zones3['recfam_abk'] + zones3['reclng_abk'] + zones3['recmtb_abk'] + zones3['recoth_abk'] + 
                       zones3['grade_abk'] + zones3['univ_abk'] + zones3['wrk_abk'] + zones3['wrknhb_abk']) 

zones3['total_pbk'] = (zones3['disc_pbk'] + zones3['mnt_pbk'] + zones3['mntnhb_pbk'] + 
                       zones3['recfam_pbk'] + zones3['reclng_pbk'] + zones3['recmtb_pbk'] + zones3['recoth_pbk'] + 
                       zones3['grade_pbk'] + zones3['univ_pbk'] + zones3['wrk_pbk'] + zones3['wrknhb_pbk']) 


# In[22]:


# then export to shape
zones3.spatial.to_featureclass(location=r".\Outputs\Microzone_Trip_Summaries.shp")


# ## Merge zone attraction and production scores with the microzone geometry

# In[23]:


# Create a clean copy of zones dataset
# zones2 = zones[['zone_id', 'co_tazid', 'tazid', 'co_fips', 'co_name', 'SHAPE']].copy()
zones2 = zones[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'AREA_SQMIL', 'SHAPE']].copy()
zones2['zone_id'] = zones2['zone_id'].astype('int64')

# NOTE: need to add zone_id to empty field in output csv
ascore = pd.read_csv(r".\Model_Outputs\zone_attraction_size.csv")
pscore = pd.read_csv(r".\Model_Outputs\zone_production_size.csv")

zones3a = zones2.merge(ascore, left_on='zone_id', right_on='zone_id', how='left')
zones3p = zones2.merge(pscore, left_on='zone_id', right_on='zone_id', how='left')


# In[24]:


# fill NAs where necessary
for field in list(zones3a.columns):
    if field !='SHAPE':
        zones3a[field].fillna(-1, inplace=True)

# fill NAs where necessary
for field in list(zones3p.columns):
    if field !='SHAPE':
        zones3p[field].fillna(-1, inplace=True)

zones3p.rename({'sch_grade_nhb': 'grade_nhb', 'sch_univ_nhb': 'univ_nhb', 'rec_oth_nhb':'recothnhb'}, axis=1, inplace=True)        
        
# Fill NAs with -1, then export to shape
zones3a.spatial.to_featureclass(location=r".\Outputs\Microzone_A_Scores.shp")
zones3p.spatial.to_featureclass(location=r".\Outputs\Microzone_P_Scores.shp")


# ## Get Centroid Nodes

# In[25]:


nodes = pd.DataFrame.spatial.from_featureclass(r".\Model_Outputs\nodes.shp")
nodes['node_id'] = nodes.index
nodes.shape


# In[26]:


nodes2 = nodes[['node_id', 'xcoord', 'ycoord', 'zcoord', 'SHAPE']].copy()
centroids = nodes2.merge(zones[['NODE_ID', 'zone_id']], left_on='node_id', right_on='NODE_ID', how='inner')
print(centroids.columns)


# In[27]:


centroids = centroids[['node_id', 'xcoord', 'ycoord', 'zcoord', 'zone_id', 'SHAPE']].copy()
centroids.spatial.to_featureclass(location=r".\Outputs\Microzone_Centroids.shp")

