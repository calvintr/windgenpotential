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

from osgeo import gdal
from osgeo import gdalconst
from osgeo import ogr

from utils import geo 

def burn_vector_in_raster(raster, vector, vector_attribute ,out_dtype, nodata_val, out_path):

    ndsm = raster
    shp = vector 
    dta = gdal.Open(ndsm, gdalconst.GA_ReadOnly)
    geo_transform = dta.GetGeoTransform()
    #source_layer = dta.GetLayer()
    x_min = geo_transform[0]
    y_max = geo_transform[3]
    x_max = x_min + geo_transform[1] * dta.RasterXSize
    y_min = y_max + geo_transform[5] * dta.RasterYSize
    x_res = dta.RasterXSize
    y_res = dta.RasterYSize
    mb_v = ogr.Open(shp)
    mb_l = mb_v.GetLayer()
    pixel_width = geo_transform[1]
    output = out_path 
    target_ds = gdal.GetDriverByName('GTiff').Create(output, x_res, y_res, 1, gdal.GDT_Float32)
    target_ds.SetGeoTransform((x_min, pixel_width, 0, y_min, 0, pixel_width))
    band = target_ds.GetRasterBand(1)
    NoData_value = nodata_val
    band.SetNoDataValue(NoData_value)
    band.FlushCache()
    gdal.RasterizeLayer(target_ds, [1], mb_l, options=[f"ATTRIBUTE={vector_attribute}"])

    target_ds = None
    

def write_geotiff(filename, mask, trans, proj = 'epsg:3035', gdal_write_dtype = gdal.GDT_Float32):
    """
    Write np.array to GeoTiff rasterfile. Utilizes mask and transfrom objectes returned from atlite.shape_availibility()
    
    Parameters
    ----------
    
    filename : 'str'
    mask : numpy.ndarray
        Array containing raster matrix returned from shape_availability()[0]
    trans : Affine()
        Geometry information returned from shape_availability()[1]
    proj : str()
        Projection valid by gdal.driver.SetProjection()
        Default: 'epsg:3035'
    gdal_write_dtype : int (GDAL dtype index)
        Information on which dtype to use when writing geotiff.
        Available types: https://naturalatlas.github.io/node-gdal/classes/Constants%20(GDT).html
        Most common: gdal.GDT_Float32, gdal.GDT_Byte, gdal.GDT_UInt16
    """
    
    arr_type = gdal_write_dtype

    driver = gdal.GetDriverByName("GTiff")
    
    out_ds = driver.Create(filename, mask.shape[1], mask.shape[0], 1, arr_type)
    out_ds.SetProjection(proj)
    out_ds.SetGeoTransform([trans[2], trans[0], trans[1], trans[5], trans[3], trans[4]])
    
    band = out_ds.GetRasterBand(1)
    band.WriteArray(mask)
    band.FlushCache()

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
    
    #Exclude Canary Islands
    if country == 'Spain':
        bounds = country.geometry.bounds.values[0]
        bb = box(bounds[0], 34, bounds[2], bounds[3])
        bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
        country_shp = gpd.overlay(country, bb, how = 'intersection')

    # Exclude Madeira
    if country == 'Portugal':
        bounds = country.geometry.bounds.values[0]
        bb = box(-15, bounds[1], bounds[2], bounds[3])
        bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
        country_shp = gpd.overlay(country, bb, how = 'intersection')

    # Exclude Jan Mayen
    if country == 'Norway':
        bounds = country.geometry.bounds.values[0]
        bb = box(0, bounds[1], bounds[2], bounds[3])
        bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
        country_shp = gpd.overlay(country, bb, how = 'intersection')
    
    #Retrieve bounds of country shape + buffer for download
    bounds = country_shp.bounds.values[0]
    bb = shapely.geometry.box(bounds[0]-0.125, bounds[1]-0.125, bounds[2]+0.125, bounds[3]+0.125)
    bb = gpd.GeoDataFrame(gpd.GeoSeries(bb), columns=['geometry'])
              
    #Loop Over DT Range
    for i in dt:
    
        savepath = f'{path}{country}/{i}.nc'

        if os.path.isfile(path) == True:
            print(f'{country} {i} already exists.')
            continue 

        cutout = atlite.Cutout(path=savepath,
                               module='era5',
                               bounds=bb.unary_union.bounds,
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
