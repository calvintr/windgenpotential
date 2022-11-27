from utils import geo, data
import geopandas as gpd 
import numpy as np
import rasterio as rio 
from rasterio.windows import from_bounds
from osgeo import gdal

import sys

cntry = sys.argv[1]
slope_cutoff = int(sys.argv[2])

country = gpd.read_file(f'C:/CaT/Masterthesis/repository/data/country_shapes/{cntry}.gpkg')
country = country.to_crs(3035)

with rio.open('C:/CaT/Masterthesis/repository/data/input_geodata/EUD_CP_SLOP_mosaic/eudem_slop_3035_europe.tif') as src: 
    window = from_bounds(country.bounds['minx'].values, country.bounds['miny'].values, country.bounds['maxx'].values, country.bounds['maxy'].values, src.transform)
    slope = src.read(1, window=window)
    
slope[slope == 0] = 250
 
slope = geo.dn_to_degrees(slope) 

slope_eli = np.where(slope >= slope_cutoff, 1, 0).astype(bool)

data.write_geotiff(f'C:/CaT/Masterthesis/repository/data/country_slope/{cntry}-{str(slope_cutoff)}.tif', 
                   mask = slope_eli,
                   trans = rio.windows.transform(window, src.transform),
                   gdal_write_dtype = gdal.GDT_Byte) 