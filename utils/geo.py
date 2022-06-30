# All currently utilised functions concerning geo data wrangling. 

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

def merge_cutouts(src):
    """
    Merge a collection of atlite.Cutout
    
    Parameters:
    ----------
    src = str() or list()
        List containing path to atlite.Cutout collections
        
    Returns:
    --------
    atilite.Cutout
    """
    
    cutout = atlite.Cutout(path = src[0])
    
    
    for i in range(1 , len(src)):
        
        cutout = cutout.merge(atlite.Cutout(path = src[i]))
                              
    return cutout


def tif_bb_filter(raster, shapes, output_crs = 'raster'):
    '''
    Reduce gpd shape or shape collection to bounding box of a .tif raster via gpd.overlay
    
    Parameters
    ----------
    raster : rasterio.DatasetReader
        Raster file
    shapes : gpd.DataFrame
        Geopandas DataFrame containing geometry collection
    output_crs : 'str'
        Either 'raster' or 'shapes' which specifies the desired output crs
    
    Returns
    _______
    gpd.DataFrame object restricted by tif raster bounds 
    
    '''
    bb = shapely.geometry.box(*raster.bounds)
    bb = gpd.GeoDataFrame(gpd.GeoSeries(bb), columns=['geometry'], crs=raster.crs)
    
    shapes_crs_adj = shapes.to_crs(raster.crs)

    shapes_filtered = gpd.overlay(shapes_crs_adj, bb, how='intersection')
    
    if output_crs == 'shapes':
        shapes_filtered = shapes_filtered.to_crs(shapes.crs)

    return shapes_filtered