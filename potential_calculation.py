from utils import geo

import pandas as pd
import rioxarray as rioxr
import xarray as xr
import geopandas as gpd
import sys
import yaml

ROOT = sys.argv[1]
cntry = sys.argv[2]
scenario = sys.argv[3]
urban_distance = int(sys.argv[4])
slope = int(sys.argv[5])
forest_share = int(sys.argv[6])
lpa_share = int(sys.argv[7])
turbine_1 = sys.argv[8]

try:
    turbine_2 = sys.argv[9]
except:
    turbine_2 = None

## 0. Get turbine_config .yaml
with open(ROOT + "windgenpotential/turbine.yaml", 'r') as stream:
    turbine_config = yaml.safe_load(stream)    
    
## 1. Read in cutout(s) 
src = []
root = ROOT + f'data/era5/{cntry}/'

for i in pd.date_range('2011' , '2022', freq = 'Y').strftime('%Y'): 
    
    src.append(f'{root}{i}.nc')            
               
cutout = geo.merge_cutouts(src)

   
## 2. Get GWA data for mean correction
# Import GWA Data for Germany
gwa = rioxr.open_rasterio(ROOT + f'data/gwa/{cntry}_wind-speed_100m.tif')
gwa = gwa.rename({'x' : 'lon', 'y' : 'lat'})

# Move the spatial_ref to attributes
gwa.attrs['spatial_ref'] = gwa['spatial_ref'].attrs
gwa = gwa.drop(['spatial_ref'])

# Drop the flat band dimension 
gwa = gwa.squeeze('band')
gwa = gwa.reset_coords('band', drop=True)
 
# Interpolate -> downscale GWA grid to ERA5 resolution
gwa_interpol = gwa.interp(lat=cutout.data.lat, lon=cutout.data.lon, method = 'linear')

# Mean correction in data
cutout.data['wnd100m'].values = cutout.data['wnd100m'].values * (gwa_interpol / cutout.data['wnd100m'].mean('time')).values

# Get the cell layout 
cells = cutout.grid


if turbine_2 != None:
    
    turbine_placement = gpd.read_file(ROOT + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}-{turbine_2}.gpkg')
    
    a = cells.drop(['x', 'y'], axis = 1)

    b = gpd.sjoin(a, turbine_placement[turbine_placement.ttype == 1].to_crs(4326) , how="left").drop('index_right', axis = 1).reset_index().dissolve(by = 'index', aggfunc='count')
    b['capacity'] = b['ttype'] * turbine_config[turbine_1].get('capacity')

    c = gpd.sjoin(a, turbine_placement[turbine_placement.ttype == 2].to_crs(4326) , how="left").drop('index_right', axis = 1).reset_index().dissolve(by = 'index', aggfunc='count')
    c['capacity'] = c['ttype'] * turbine_config[turbine_2].get('capacity')
    
    layout = xr.DataArray(b.capacity.values.reshape(cutout.shape), coords = cutout.data['wnd100m'].mean('time').coords).rename('Installed Capacity [MW]')
    generation_1 = cutout.wind(turbine=turbine_1, layout = layout).to_dataframe().droplevel(1)

    layout = xr.DataArray(c.capacity.values.reshape(cutout.shape), coords = cutout.data['wnd100m'].mean('time').coords).rename('Installed Capacity [MW]')
    generation_2 = cutout.wind(turbine=turbine_2, layout = layout).to_dataframe().droplevel(1)
    
    generation_1.rename(columns = {'specific generation' : turbine_1}, inplace = True)
    generation_2.rename(columns = {'specific generation' : turbine_2}, inplace = True)

    gen = pd.concat([generation_1, generation_2], axis = 1)
    
    store = pd.HDFStore(ROOT + f'data/country_generation_potential/{cntry}.h5')
    store[f'{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}-{turbine_2}'] = gen 
    store.close()

    
else: 

    turbine_placement = gpd.read_file(root + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}.gpkg')

    ## 3. Join the placed turbines and the era-grid to create the layout
    a = cells.drop(['x', 'y'], axis = 1)
    b = gpd.sjoin(a, turbine_placement.to_crs(4326) , how="left").drop('index_right', axis = 1).reset_index().dissolve(by = 'index', aggfunc='count')# .groupby('index_right').sum()
    b['capacity'] = b['ttype'] * turbine_config[turbine_1].get('capacity')
    
    #create layout
    layout = xr.DataArray(b.capacity.values.reshape(cutout.shape), coords = cutout.data['wnd100m'].mean('time').coords).rename('Installed Capacity [MW]')

    ## 4. Compute the generation timeseries

    gen = cutout.wind(turbine=turbine_1, layout = layout).to_dataframe().droplevel(1)
    gen.rename(columns = {'specific generation' : turbine_1}, inplace = True)

    store = pd.HDFStore(root + f'data/country_generation_potential/{cntry}.h5')
    store[f'{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}'] = gen 
    store.close()