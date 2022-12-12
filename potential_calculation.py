from utils import geo

import pandas as pd
import numpy as np
import rioxarray as rioxr
import xarray as xr
import geopandas as gpd
import atlite
import sys
import yaml
import glob
import os

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

if turbine_2 != None:
    
    turbine_placement = gpd.read_file(ROOT + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}-{turbine_2}.gpkg')
    
    ## 2. Get GWA data for mean correction
    # Import GWA Data for Germany
    gwa_cf = np.load(ROOT + f'data/country_era5_gwa_cf/{cntry}.npy')
    
    files = glob.glob(ROOT + f'data/era5/{cntry}/' + '*.nc')
    files = [os.path.basename(file) for file in files]
    
    output={}
    
    for wy in files:
    
        ##1. Get y-cutout
        cutout = atlite.Cutout(path = ROOT + f'data/era5/{cntry}/{wy}')

        # Mean correction in data
        cutout.data['wnd100m'].values = cutout.data['wnd100m'].values * gwa_cf

        # Get the cell layout 
        cells = cutout.grid

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
        
        output[wy] = gen
        
    output = pd.concat(output.values(), axis = 0)
        
    store = pd.HDFStore(ROOT + f'data/country_generation_potential/{cntry}.h5')
    store[f'{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}-{turbine_2}'] = output 
    store.close()

    
else: 

    turbine_placement = gpd.read_file(root + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}.gpkg')

    ## 2. Get GWA data for mean correction
    # Import GWA Data for Germany
    gwa_cf = np.load(ROOT + f'data/country_era5_gwa_cf/{cntry}.npy')
    
    files = glob.glob(ROOT + f'data/era5/{cntry}/' + '*.nc')
    files = [os.path.basename(file) for file in files]
    
    output={}
    
    for wy in files:
    
        ##1. Get y-cutout
        cutout = atlite.Cutout(path = ROOT + f'data/era5/{cntry}/{wy}')

        # Mean correction in data
        cutout.data['wnd100m'].values = cutout.data['wnd100m'].values * gwa_cf

        # Get the cell layout 
        cells = cutout.grid
    
    
        ## 3. Join the placed turbines and the era-grid to create the layout
        a = cells.drop(['x', 'y'], axis = 1)
        b = gpd.sjoin(a, turbine_placement.to_crs(4326) , how="left").drop('index_right', axis = 1).reset_index().dissolve(by = 'index', aggfunc='count')# .groupby('index_right').sum()
        b['capacity'] = b['ttype'] * turbine_config[turbine_1].get('capacity')

        #create layout
        layout = xr.DataArray(b.capacity.values.reshape(cutout.shape), coords = cutout.data['wnd100m'].mean('time').coords).rename('Installed Capacity [MW]')

        ## 4. Compute the generation timeseries

        gen = cutout.wind(turbine=turbine_1, layout = layout).to_dataframe().droplevel(1)
        gen.rename(columns = {'specific generation' : turbine_1}, inplace = True)
        
        output[wy] = gen
        
    output = pd.concat(output.values(), axis = 0)

    store = pd.HDFStore(root + f'data/country_generation_potential/{cntry}.h5')
    store[f'{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}'] = gen 
    store.close()