from utils import geo, data
import pandas as pd
import geopandas as gpd
import sys
import rasterio as rio
from shapely.geometry import shape
from osgeo import gdal

ROOT = sys.argv[1]
cntry = sys.argv[2] 

# Read in cutout(s) 
src = []
root = ROOT + f'data/era5/{cntry}/'

for i in pd.date_range('2011' , '2022', freq = 'Y').strftime('%Y'): 
    
    src.append(f'{root}{i}.nc')            
               
cutout = geo.merge_cutouts(src)
del src

# Read in ERA-5 Data and compute avg azimuth over time, save as raster file
cutout_az = cutout.data['wnd_azimuth'].mean('time')
cutout_az.rio.to_raster(ROOT + f'data/country_azimuth/{cntry}-cutout-azimuth.tif', recalc_transform = True)

# Open raster 
with rio.open(ROOT + f'data/country_azimuth/{cntry}-cutout-azimuth.tif') as f:

    dta = f.read(1)
    shapes = rio.features.shapes(dta, transform = f.transform)

# read the shapes as separate lists
azimuth = []
geometry = []
for shapedict, value in shapes:
    azimuth.append(value)
    geometry.append(shape(shapedict))

# build the gdf object over the two lists
gdf_az = gpd.GeoDataFrame(
        {'azimuth': azimuth, 'geometry': geometry},
        crs="EPSG:4326"
)

gdf_az = gdf_az.to_crs(3035)


#Clip the weather information to the extent of the landuse raster and save as shapefile
gdf_az_clipped = geo.tif_bb_filter(raster = rio.open(ROOT + f'data/country_landuse_results/{cntry}-base-1000-30-0-0.tif'), shapes = gdf_az)
gdf_az_clipped.to_file(ROOT + f'data/country_azimuth/{cntry}-clipped-azimuth.gpkg')  


#Burn shapefile into raster
data.burn_vector_in_raster(
    raster = ROOT + f'data/country_landuse_results/{cntry}-base-1000-30-0-0.tif',
    vector = ROOT + f'data/country_azimuth/{cntry}-clipped-azimuth.gpkg',
    vector_attribute = 'azimuth',
    out_dtype = gdal.GDT_Float32,
    nodata_val = 2,
    out_path = ROOT + f'data/country_azimuth/{cntry}-burned-azimuth.tif'
)
    