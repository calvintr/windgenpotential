from utils import geo, data
import yaml
import geopandas as gpd
from atlite.gis import ExclusionContainer
import sys
from osgeo import gdal
import rasterio as rio

ROOT = sys.argv[1]
cntry = sys.argv[2]
scenario = sys.argv[3] 
urban_distance = int(sys.argv[4])  
slope = int(sys.argv[5]) 
forest_share = int(sys.argv[6])
lpa_share = int(sys.argv[7])

LUISA = ROOT + 'data/input_geodata/luisa.tif'

country = gpd.read_file(ROOT + f'data/country_shapes/{cntry}.gpkg')
country = country.to_crs(3035)
pa = gpd.read_file(ROOT + f'data/country_pa/{cntry}.gpkg')

with open(ROOT + "windgenpotential/gridcode.yaml", 'r') as stream:
    gc_config = yaml.safe_load(stream)    

exc = ExclusionContainer(res=50)

# inclusion
exc.add_raster(LUISA, codes = gc_config[scenario]['inclusion'], crs=3035, invert = True)

# exclusion with fixed distances
for config in gc_config[scenario]['exclusion_fix'].values():
    exc.add_raster(LUISA, codes = config.get('codes'), crs = 3035,  buffer = config.get('distance'))

# exclusion with variable distances
for config in gc_config[scenario]['exclusion_var'].values():
    exc.add_raster(LUISA, codes = config.get('codes'), crs = 3035,  buffer = urban_distance)

# slope exclusion
exc.add_raster(ROOT + f'data/country_slope/{cntry}-{slope}.tif',
                     codes = 1, crs=3035, buffer=175)

# pa exclusion
exc.add_geometry(pa)

#calculate
landuse = geo.mte(exc, country.geometry, share_kind='normal')



if forest_share != 0:

    with rio.open(ROOT + f'data/country_share_forest/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}.tif') as f:
        forest = f.read(1)
        
    landuse[0] = landuse[0] + forest
    del forest
    
    
if lpa_share != 0:
    
    with rio.open(ROOT + f'data/country_share_lpa/{cntry}-{scenario}-{urban_distance}-{slope}-{lpa_share}.tif') as f:
        lpa = f.read(1)
        
    landuse[0] = landuse[0] + lpa
    del lpa
    
        
data.write_geotiff(ROOT + f'data/country_landuse_results/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}.tif', 
              mask = landuse[0],
              trans = landuse[1],
              gdal_write_dtype = gdal.GDT_Byte) 

        
        
