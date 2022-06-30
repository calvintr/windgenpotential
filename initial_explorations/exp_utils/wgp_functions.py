# A dump of all experimental functions used in the initial_explorations notebook
# Refinded fuctions used utils


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


def get_grid(da, crs):

    """
    Retrieve grid as gpd.DataFrame from a xr.dataArray or Set
    
    Parameters:
    ----------
    da : xarray.DataArray
    crs : Desired output CRS

    Returns: 
    -------
    gpd.DataFrame
    
    """
    xs, ys = np.meshgrid(da.coords["x"], da.coords["y"])
    coords = np.asarray((np.ravel(xs), np.ravel(ys))).T
    span = (coords[da.shape[1] + 1] - coords[0]) / 2
    cells = [shapely.geometry.box(*c) for c in np.hstack((coords - span, coords + span))]

    return gpd.GeoDataFrame(
        {"x": coords[:, 0], "y": coords[:, 1], "geometry": cells}, crs=crs
    )


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
        
        country_shp = tif_bb_filter(raster,
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


def store_dict(file, dictionary):
    """
    Pickle dump a dictionary
    """
    with open(file, 'wb') as f:
        pickle.dump(dictionary, f)

        
def open_dict(file):
    """
    Opens pickle dump
    """
    with open(file, 'rb') as f:
        dta_import = pickle.load(f)
    return dta_import


def write_geotiff(filename, mask, trans, proj = 'epsg:3035'):
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
    """
    
    if mask.dtype == np.float32:
        arr_type = gdal.GDT_Float32
    else:
        arr_type = gdal.GDT_Int32

    driver = gdal.GetDriverByName("GTiff")
    
    out_ds = driver.Create(filename, mask.shape[1], mask.shape[0], 1, arr_type)
    out_ds.SetProjection(proj)
    out_ds.SetGeoTransform([trans[2], trans[0], trans[1], trans[5], trans[3], trans[4]])
    
    band = out_ds.GetRasterBand(1)
    band.WriteArray(mask)
    band.FlushCache()



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


def invert(array):
    """
    Inverts an array. Turns 0 to 1 and 1 to 0 simultaneously.
    Used for inverting maksed objects from atlite.shape_availibility()
    Contents must be type == int for bitwise XOR
    
    Parameters
    __________
    
    array : np.array
    """
    
    a = array.astype(int)
    b = np.where((a==0)|(a==1), a^1, a)
    
    return b


def side_by_side(m1, t1, e1, m2, t2, e2, c_shape, title, savepath = None, close = False, dpi=100):
    '''
    Creating side-by-side plot for two masked rasters
    
    Parameters
    __________
    
    m1, m2 : numpy.ndarray
        Array containing raster matrix returned from shape_availability()[0]
    t1, t2 : Affine()
        Geometry information for transfomation in plotting raster
    e1, e2 : numpy.float64
        Eligible share [0,1]
    c_shape : gpd.DataFrame
        Geopandas DataFrame containing geometry collection.
    title : 'str'
    savepath : 'str' or None
        Default: None
        If None, plot is not saved 
    close : bool
        Default: None
        If True, plt.close(fig) is run
        Useful for saving memory when plots are produced in loop
    '''

    fig, ax = plt.subplots(1,2, figsize=(18,12), dpi = dpi,
                          num=1, clear=True) # Helps with memory preservation

    ax[0] = show(m1, transform=t1, cmap='Greens', ax=ax[0])
    c_shape.plot(ax=ax[0], edgecolor='k', color='None')
    ax[0].set_title(f'LUISA Data: Eligible area (green) {e1 * 100:2.2f}%', size=16);

    ax[1] = show(m2, transform=t2, cmap='Greens', ax=ax[1])
    c_shape.plot(ax=ax[1], edgecolor='k', color='None')
    ax[1].set_title(f'CORINE Data: Eligible area (green) {e2 * 100:2.2f}%', size=16);
    
    fig.tight_layout()

    if title != None:
        plt.suptitle(title, y=1.01, size=16)
        
    if savepath != None:
        plt.savefig(savepath, bbox_inches='tight')
        
    if close == True:
        plt.close(fig)


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