from utils import geo
import geopandas as gpd
from shapely.geometry import shape, box
import cartopy.io.shapereader as shpreader
import rasterio as rio 
import sys

ROOT = sys.argv[1]
cntry = sys.argv[2]

LUISA = ROOT + 'data/input_geodata/luisa.tif'

# Get shape of country 
shpfilename = shpreader.natural_earth(resolution='10m',
                                          category='cultural',
                                          name='admin_0_countries')  
reader = shpreader.Reader(shpfilename)

country = gpd.GeoSeries({r.attributes['NAME_EN']: r.geometry
                    for r in reader.records()},
                    crs='epsg:4326'
                   ).reindex([cntry])

# Filter country shape for LUISA grid availability 
country = geo.tif_bb_filter(raster = rio.open(LUISA), shapes = gpd.GeoDataFrame(country, columns = ['geometry']), output_crs = 'shapes')

#Exclude Canary Islands
if cntry == 'Spain':
    bounds = country.geometry.bounds.values[0]
    bb = box(bounds[0], 34, bounds[2], bounds[3])
    bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
    country = gpd.overlay(country, bb, how = 'intersection')

# Exclude Madeira
if cntry == 'Portugal':
    bounds = country.geometry.bounds.values[0]
    bb = box(-15, bounds[1], bounds[2], bounds[3])
    bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
    country = gpd.overlay(country, bb, how = 'intersection')

# Exclude Jan Mayen
if cntry == 'Norway':
    bounds = country.geometry.bounds.values[0]
    bb = box(0, bounds[1], bounds[2], bounds[3])
    bb = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[bb])
    country = gpd.overlay(country, bb, how = 'intersection')

country.to_file(ROOT + f'data/country_shapes/{cntry}.gpkg',  driver = 'GPKG')