# All currently utilised functions concerning data download, reading and writing

import atlite
import xarray as xr
import rasterio as rio
import rioxarray as rioxr

import os.path

import pandas as pd
from pandas.tseries.offsets import MonthEnd
import numpy as np
import geopandas as gpd

import cartopy.crs as ccrs
from cartopy.crs import PlateCarree as plate
import cartopy.io.shapereader as shpreader
import shapely

from utils import geo 


def cutout_download(country, start, end, path, feature = None, freq = 'M', shape_filter = None):
    """
    Wrapper function for atlite.Cutout downloader to call api requests to Copernicus CDS in loop.

    Parameters:
    ----------

    country : str()
        Country recognised by shpreader.natural_earth
    start, end : datetime.timestamp
    path : str()
        Path to folder root on country level
    freq : str()
        Download frequency of weather data: 'DS', 'MS', 'YS'
    shape_filter : rasterio.rasterio.DatasetReader
        Filter the shape for rasterbounds
    feature : str()
        Feature that should be passed to atlite.Cutout.prepare()
        If 'None', all features are downloaded

    """
    
    #Initialize DT Range
    if freq == 'D':
        dt = pd.date_range(start, end, freq = 'D').strftime('%Y-%m-%d')
    elif freq == 'M':
        dt = pd.date_range(start, end, freq = 'MS').strftime('%Y-%m')
    elif freq == 'Y':
        dt = pd.date_range(start, end, freq = 'YS').strftime('%Y')

    
    #Get Country Shape
    shpfilename = shpreader.natural_earth(resolution='10m',
                                          category='cultural',
                                          name='admin_0_countries')
    
    reader = shpreader.Reader(shpfilename)

    country_shp = gpd.GeoSeries({r.attributes['NAME_EN']: r.geometry
                        for r in reader.records()},
                        crs='epsg:4326'
                       ).reindex([country])
    
    if shape_filter != None:
        
        raster = rio.open(shape_filter)
        
        country_shp = geo.tif_bb_filter(raster,
                                    	gpd.GeoDataFrame(country_shp, columns = ['geometry']),
                                    	output_crs = 'shapes')
        
              
    #Loop Over DT Range
    for i in dt:
    
        savepath = f'{path}{country}/{i}.nc'

        if os.path.isfile(path) == True:
            print(f'{country} {i} already exists.')
            continue 

        cutout = atlite.Cutout(path=savepath,
                               module='era5',
                               bounds=country_shp.unary_union.bounds,
                               time=i)
        
        if feature != None:
            cutout.prepare(features = feature)
        else:
            cutout.prepare()


def agora_tile_to_dict(wind_dist,z,x,y):
    """
    Function that scrapes the agroa-windflächenrechner tileserver for one vectortile.
    
    Prameters
    ----------
    wind_dist = str, can be '400', '600', '800', '1000'
        Distance to settlement setting
    x,y,z = str
        Parameters of vectortile where:
        x = horizontal extent, y = vertical extent, z = zoom-level 
        
    Returns
    -------
    dict 
        Dictinary entry with x and y parameter plus the GeoJSON information on the vectortile-
    """
    
    url = "https://wfr.agora-energiewende.de/potential_area_mvt/{}/{}/{}/?setup__wind_distance={}".format(z,x,y,wind_dist)
    
    print(f'Downloading tile {x} / {y}')
    r = requests.get(url)
    
    try:
        assert r.status_code == 200, r.content
        
    except AssertionError:
        print(f'    Tile {x} / {y} not available')
    
    vt_content = r.content
    
    # Transformation of binary vectortiles into text-based GeoJson
    features = vt_bytes_to_geojson(vt_content, x, y, z)
    
    return {"x": x, "y": y, 'features': features}
