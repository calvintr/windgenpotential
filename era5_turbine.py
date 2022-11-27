from utils import geo, data
import pandas as pd
import geopandas as gpd
import sys
import rasterio as rio
import xarray as xr
import rioxarray as rioxr
from shapely.geometry import shape
from osgeo import gdal
import yaml
import math

ROOT = sys.argv[1]
cntry = sys.argv[2]
turbine_1 = sys.argv[3]

try: 
    turbine_2 = sys.argv[4]
except IndexError:
    turbine_2 = print("Only provided one turbine type") 

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

## 3. calculate capacity factors for turbine A and B, as well as area for capacity density

cap_factors_1 = cutout.wind(turbine=turbine_1, capacity_factor=True)
cap_factors_2 = cutout.wind(turbine=turbine_2, capacity_factor=True)

# elipse area a = pi * r * c, rotor diameter distance fixed to (4,8) 
area_1 = math.pi * (4*turbine_config[turbine_1].get('diameter')) * ((8*turbine_config[turbine_1].get('diameter')))
area_2 = math.pi * (4*turbine_config[turbine_2].get('diameter')) * ((8*turbine_config[turbine_2].get('diameter')))  

threshold = (turbine_config[turbine_2].get('capacity') / area_2) / (turbine_config[turbine_1].get('capacity') / area_1) 

# where(A/B > threshold,1,0)

decision = xr.where((cap_factors_1/cap_factors_2) > threshold, 1, 2)

## 4. burn to raster

decision.rio.to_raster(ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-cutout-decision.tif', recalc_transform = True)

# Open raster 
with rio.open(ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-cutout-decision.tif') as f:
    dta = f.read(1)
    shapes = rio.features.shapes(dta, transform = f.transform)

# read the shapes as separate lists
ttype = []
geometry = []
for shapedict, value in shapes:
    ttype.append(value)
    geometry.append(shape(shapedict))

# build the gdf object over the two lists
gdf_tt = gpd.GeoDataFrame(
        {'ttype': ttype, 'geometry': geometry},
        crs="EPSG:4326"
)

gdf_tt = gdf_tt.to_crs(3035)


#Clip the weather information to the extent of the landuse raster and save as shapefile
gdf_tt_clipped = geo.tif_bb_filter(raster = rio.open(ROOT + f'data/country_landuse_results/{cntry}-base-1000-30-0-0.tif'), shapes = gdf_tt)
gdf_tt_clipped.to_file(ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-clipped-decision.gpkg')  


#Burn shapefile into raster
data.burn_vector_in_raster(
    raster = ROOT + f'data/country_landuse_results/{cntry}-base-1000-30-0-0.tif',
    vector = ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-clipped-decision.gpkg',
    vector_attribute = 'ttype',
    out_dtype = gdal.GDT_Float32,
    nodata_val = 2,
    out_path = ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-burned-decision.tif'
)

