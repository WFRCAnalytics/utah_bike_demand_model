#!/usr/bin/env python
# coding: utf-8

# In[1]:


import geopandas as gpd
import pandas as pd
import os
import numpy as np


# In[2]:


# show all columns
pd.options.display.max_columns = None


# ## Join Bike volume data to links

# In[3]:


# read in links csv
links = gpd.read_file(r".\Data\links.csv")

# read in links shapefile
links_shp = gpd.read_file(r".\Data\links.shp")
print(links.shape)
print(links_shp.shape)


# In[4]:


# read in bike volume
bike_volume = pd.read_csv(r".\Data\bike_vol.csv")

#should be double the amount of links for both directions
print(bike_volume.shape)

# fill bike volume NAs with -1
bike_volume['bike_vol'] = bike_volume['bike_vol'].fillna(0)


# In[5]:


# Create key to use for joining to links
bike_volume['key'] = np.where(bike_volume['from_node'].astype(int) < bike_volume['to_node'].astype(int), 
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
links4 = links_shp.merge(link_bike_vol3, left_on='link_id', right_on='link_id', how='outer')

# export to shape
links4.to_file(r".\Results\links_bv.shp")


# ## Summarize zone trips by Attracting/Producing Zone

# In[45]:


# read in zones
zones = gpd.read_file(r".\Data\microzones.shp")


# ### Read in trip tables, summarize, and format

# In[46]:


def summarize_zones(trips_df, name):
    
    # summarize trips by attraction or production
    trips_sum_attr = pd.DataFrame(trips_df.groupby('azone')['bk'].sum())
    trips_sum_prod = pd.DataFrame(trips_df.groupby('pzone')['bk'].sum())
    
    # format tables
    trips_sum_attr['zone_id'] = trips_sum_attr.index
    trips_sum_attr.columns = [name + '_abk', 'zone_id']
    trips_sum_prod['zone_id'] = trips_sum_prod.index
    trips_sum_prod.columns = [name + '_pbk', 'zone_id']
    
    # join the attraction and production summary tables using zone id
    merged = trips_sum_attr.merge(trips_sum_prod, left_on='zone_id', right_on='zone_id', how='outer')
    return merged
    


# In[47]:


# sch_univ = pd.read_csv(r".\Data\sch_univ_trip.csv")
# sch_univ_sum = summarize_zones(sch_univ, 'univ')
# sch_univ_sum.isnull().values.any()


# In[48]:


# Discretionary trips (social trips, some recreation)
disc = pd.read_csv(r".\Data\disc_trip.csv")
disc_sum = summarize_zones(disc, 'disc')
del disc

# Maintenance trips (e.g. groceries)
maint = pd.read_csv(r".\Data\maint_trip.csv")
maint_sum = summarize_zones(maint, 'mnt')
del maint

# Maintenance trips non-home-based (e.g. groceries)
maint_nhb = pd.read_csv(r".\Data\maint_trip_nhb.csv")
maint_nhb_sum = summarize_zones(maint_nhb, 'mntnhb')
del maint_nhb

# Recreational family trips
rec_fam = pd.read_csv(r".\Data\rec_fam_trip.csv")
rec_fam_sum = summarize_zones(rec_fam, 'recfam')
del rec_fam

# Recreation long trips
rec_long = pd.read_csv(r".\Data\rec_long_trip.csv")
rec_long_sum = summarize_zones(rec_long, 'reclng')
del rec_long

# Recreation other trips (recreation that doesn't fall into family or long)
rec_oth = pd.read_csv(r".\Data\rec_oth_trip.csv")
rec_oth_sum = summarize_zones(rec_oth, 'recoth')
del rec_oth

# school (grade) trips
sch_grade = pd.read_csv(r".\Data\sch_grade_trip.csv")
sch_grade_sum = summarize_zones(sch_grade, 'grade')
del sch_grade

# school (university) trips
sch_univ = pd.read_csv(r".\Data\sch_univ_trip.csv")
sch_univ_sum = summarize_zones(sch_univ, 'univ')
del sch_univ

# Work trips
work = pd.read_csv(r".\Data\work_trip.csv")
work_sum = summarize_zones(work, 'wrk')
del work

# Work non-home-based trips
work_nhb = pd.read_csv(r".\Data\work_trip_nhb.csv")
work_nhb_sum = summarize_zones(work_nhb, 'wrknhb')
del work_nhb


# In[49]:


rec_fam_sum


# ### Merge trip summarizes back to microzone shapefile

# In[50]:


# Create a clean copy of zones dataset
zones2 = zones[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'geometry']].copy()
zones2['zone_id'] = zones2['zone_id'].astype('int64')

# Join trip tables
zones2 = zones2.merge(disc_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(maint_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(maint_nhb_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(rec_fam_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(rec_long_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(rec_oth_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(sch_grade_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(sch_univ_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(work_sum, left_on='zone_id', right_on='zone_id', how='outer')
zones2 = zones2.merge(work_nhb_sum, left_on='zone_id', right_on='zone_id', how='outer')

# preview table
zones2.head(30)


# In[51]:


# Fill NAs with -1, then export to shape
zones2.fillna(-1).to_file(r".\Results\Microzone_Trip_Summaries.shp")


# ## Merge zone attraction and production scores with the microzone geometry

# In[53]:


# Create a clean copy of zones dataset
zones2 = zones[['zone_id', 'CO_TAZID', 'TAZID', 'CO_FIPS', 'CO_NAME', 'geometry']].copy()
zones2['zone_id'] = zones2['zone_id'].astype('int64')

ascore = pd.read_csv(r".\Data\zone_attraction_size.csv")
pscore = pd.read_csv(r".\Data\zone_production_size.csv")

zones3a = zones2.merge(ascore, left_on='zone_id', right_on='zone_id', how='outer')
zones3p = zones2.merge(pscore, left_on='zone_id', right_on='zone_id', how='outer')


# In[54]:


# Fill NAs with -1, then export to shape
zones3a.fillna(-1).to_file(r".\Results\Microzone_A_Scores.shp")
zones3p.fillna(-1).to_file(r".\Results\Microzone_P_Scores.shp")


# ## Get Centroid Nodes

# In[55]:


nodes = gpd.read_file(r".\Data\nodes.shp")
nodes['node_id'] = nodes.index
nodes.shape


# In[56]:


nodes2 = nodes[['node_id', 'xcoord', 'ycoord', 'zcoord', 'geometry']].copy()
centroids = nodes2.merge(zones[['NODE_ID', 'zone_id']], left_on='node_id', right_on='NODE_ID', how='inner')
print(centroids.columns)


# In[57]:


centroids = centroids[['node_id', 'xcoord', 'ycoord', 'zcoord', 'zone_id', 'geometry']].copy()
centroids.to_file(r".\Results\Microzone_Centroids.shp")

