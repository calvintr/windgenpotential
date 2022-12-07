import numpy as np
import geopandas as gpd

from atlite.gis import shape_availability, ExclusionContainer
from osgeo import gdal

from utils import geo, data

import yaml
import sys

ROOT = sys.argv[1]
cntry = sys.argv[2]
scenario = sys.argv[3]
urban_distance = int(sys.argv[4])
slope = sys.argv[5]
lpa_share = int(sys.argv[6])

LUISA = ROOT + 'data/input_geodata/luisa.tif'

#Read in gridcode config
with open(ROOT + "windgenpotential/gridcode.yaml", 'r') as stream:
    gc_config = yaml.safe_load(stream)    
    
#Get country & pa shape
country = gpd.read_file(ROOT + f'data/country_shapes/{cntry}.gpkg').to_crs(3035) 
pa = gpd.read_file(ROOT + f'data/country_pa/{cntry}.gpkg').to_crs(3035)


if (lpa_share != 0) and (pa[pa['IUCN_CAT'] == 'V'].shape[0] != 0): 
    ##Compute total lpa area in country
    exc = ExclusionContainer(res=50)
    exc.add_geometry(pa[pa['IUCN_CAT'] == 'V'], invert = True)
    lpa = geo.mte(exc, country.geometry, share_kind='normal')
    lpa_total = lpa[0].sum()
    del lpa 

    ##Compute available lpa area given gc scenario and urban_distance

    exc = ExclusionContainer(res=50)

    #include lpa
    exc.add_geometry(pa[pa['IUCN_CAT'] == 'V'], invert = True)

    # exclusion with fixed distances
    for config in gc_config[scenario]['exclusion_fix'].values():
        exc.add_raster(LUISA, codes = config.get('codes'), crs = 3035,  buffer = config.get('distance'))
    # exclusion with variable distances
    for config in gc_config[scenario]['exclusion_var'].values():
        exc.add_raster(LUISA, codes = config.get('codes'), crs = 3035,  buffer = urban_distance)
    # slope exclusion
    exc.add_raster(ROOT + f'data/country_slope/{cntry}-{slope}.tif',
                         codes = 1, crs=3035, buffer=175)
    # epa exclusion
    exc.add_geometry(pa[pa['IUCN_CAT'] != 'V'], invert = True)
    lpa = geo.mte(exc, country.geometry, share_kind='normal')

        
        
    
## Compute available shares

kernel_a = np.array([[1, 1, 1],
                     [1, 0, 1],
                     [1, 1, 1]])

kernel_b = np.array([[0, 1, 0],
                     [1, 0, 1],
                     [0, 1, 0]])


if lpa_share == 0:
    None
    
elif pa[pa['IUCN_CAT'] == 'V'].shape[0] == 0:
    exc = ExclusionContainer(res=50)
    lpa = geo.mte(exc, country.geometry, share_kind='normal')
    zeros = np.zeros(lpa[0].shape).astype(bool)
    data.write_geotiff(ROOT + f'data/country_share_lpa/{cntry}-{scenario}-{urban_distance}-{slope}-{lpa_share}.tif', 
                    mask = zeros,
                    trans = lpa[1],
                    gdal_write_dtype = gdal.GDT_Byte) 

else:    
    lpa_reduced = np.logical_xor(lpa[0], 
                                 geo.reduce(lpa[0], initial_total=lpa_total, reduction_target=(lpa_share/100), kernel=[kernel_a, kernel_b], sensi_start=7, threshold = 0.0005))


    data.write_geotiff(ROOT + f'data/country_share_lpa/{cntry}-{scenario}-{urban_distance}-{slope}-{lpa_share}.tif', 
                        mask = lpa_reduced,
                        trans = lpa[1],
                        gdal_write_dtype = gdal.GDT_Byte) 
