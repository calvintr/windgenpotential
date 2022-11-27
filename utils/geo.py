# All currently utilised functions concerning geo data wrangling. 

import atlite
import xarray as xr
import rasterio as rio
import rioxarray as rioxr

import os.path

import pandas as pd
from pandas.tseries.offsets import MonthEnd
import numpy as np
import math

import geopandas as gpd

import cartopy.crs as ccrs
from cartopy.crs import PlateCarree as plate
import cartopy.io.shapereader as shpreader
import shapely

from atlite.gis import shape_availability

from skimage import draw, morphology
from scipy.ndimage import binary_dilation as dilation
from scipy.ndimage import convolve 
import math

import time


def reduce(input_array, initial_total, reduction_target, kernel, sensi_start, threshold = 0.005):
    
    main = input_array
    target = input_array.sum()/initial_total - reduction_target
    current = 0
    sensitivity = sensi_start
    k = kernel[0]
    

    print(input_array.sum())
    
    while abs(target - current) > threshold:
           
        b = convolve(main.astype(int), k, mode='constant')                   
        b = np.where(b < sensitivity, 0, 1).astype(bool)
                
        a = main & b
                                           
        if (abs(a.sum()/initial_total) + threshold < target) or \
           (abs(a.sum()/initial_total - current) == 0):
            
            sensitivity = sensitivity-1
            print(f'Sensitivity adjustment: {sensitivity}')
            
            if sensitivity == 0:
                
                if k.sum() == kernel[1].sum():
                    break
                    
                k = kernel[1]
                sensitivity = k.sum() 
                print('Kernel 2 activated')
                
            continue
            
        main = a
        current = main.sum()/initial_total
        print(f'New Best: {current}')
        
    return main


def place_n_turbines(res, 
                     landuse_av, 
                     wind_dir, 
                     turbine_type, turbine_dict, 
                     r_radius_factor, c_radius_factor):    
    
    ## Set-up initial matrices   
    #landuse
    landuse = landuse_av.copy()
    
    #wind direction
    if np.isscalar(wind_dir):
        wind = np.full(landuse_av.shape, wind_dir).astype(int)
    else:
        wind = wind_dir
    
    #turbine elipses
    #turbine_elipse = ~np.zeros(shape = landuse.shape, dtype = int)
    
    #turbine placements
    turbine = np.zeros(shape = landuse.shape, dtype = 'uint8') 
    
    ##Pre-calculate radii for indvidual turbine types
    turbine_precalc = {} 
    for i in turbine_dict.keys():
        turbine_precalc[i] = {'r' : round(turbine_dict[i]/res*r_radius_factor, 0), 
                              'c' : round(turbine_dict[i]/res*c_radius_factor, 0)}
    
    
    for i in sorted(turbine_dict.keys())[::-1]:
    
        tmp = np.zeros(shape = landuse.shape, dtype = bool) 
        a, b = np.where((landuse==1) & (turbine_type==i))
        tmp[a,b] = True

        n = 0
        start = time.time()
        row_last = 0
        
        ## Loop operation
        while True:
            
            n=n+1

            # Find first available index from NW 
            idx = np.argmax(tmp[row_last:, :], axis=None)
            idx = np.unravel_index(idx, landuse.shape)
            idx = (idx[0] + row_last, idx[1])
            
            # Save the last row where a turbine was placed to prevent full array search
            row_last = idx[0]
            
            #If no more turbines to place, quit loop
            if tmp[idx] == 0:
                break
            
            #idx = np.unravel_index(np.argmax(tmp, axis=None), landuse.shape)
            #if idx == (0,0):
            #    break

            # Retrieve favourable turbine characteristics and wind direction at index
            t = turbine_type[idx[0], idx[1]]
            r = wind[idx[0], idx[1]]

            # Save turbine placement center & type
            turbine[idx[0] , idx[1]] = t

            # Draw elipse based on predominant wind direcition and turbine characteristics   
            rr, cc = draw.ellipse(idx[0], idx[1], turbine_precalc[t]['c'], turbine_precalc[t]['r'] , landuse.shape , 
                                  rotation = r)

            landuse[rr,cc] = False
            tmp[rr,cc] = False
            #turbine_elipse[rr,cc] = t
            
            if n == 10000:
                now = time.time()
                print('10000: {0} seconds'.format(round(now-start,2)))
                n=0
                start = time.time()
    
    print(f'Successfully built {np.where(turbine>0,1,0).sum()} turbines')
    
    return [landuse, turbine]#, turbine_elipse] 


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


def dn_to_degrees(dn):
    
    """
    Convert GISCO slope dataset file falues (dn) to slope values according to
    https://ec.europa.eu/eurostat/documents/7116161/7172326/SPEC011-b140109-SLOP.pdf
    
    Parameters:
    -----------
    
    dn : int
        dn value between 0 and 250
        
    Returns:
    --------
    
    corresponding slope degree : float16
    
    """
    
    return np.float16(np.arccos(dn/250.0)*180/math.pi)
    

def mte(exc, country, share_kind = "normal"):
    """
    Function that wraps the calculation of mask and transform affine output from atlite.shape_availibility()
    as well as the calculation of the eligible_share
    
    Parameters
    __________
    
    exc = atlite.ExculsionContainer
    country = gpd.DataFrame
    share_kind = str
    
    Returns
    _______
    
    list where,
    [0] = masked (array)
    [1] = transform (Affine())
    [2] = eligible_area (num)
    [3] = eligible_share (num)  
    """
    
    masked, transform = shape_availability(country, exc)
    eligible_area = masked.astype(float).sum() * exc.res**2

    if share_kind == "normal":
        eligible_share =  eligible_area / country.geometry.item().area
    elif share_kind == "inverse":
        eligible_share =  1-(eligible_area / country.geometry.item().area)

    mte_results = [masked, transform, eligible_area, eligible_share]

    return mte_results