import rasterio
import numpy as np
import geopandas as gpd 
from affine import Affine
from pyproj import Proj, transform
import rasterio as rio
from shapely.geometry import Point
import yaml
import sys
from utils import geo

ROOT = sys.argv[1]
cntry = sys.argv[2]
scenario = sys.argv[3]
urban_distance = int(sys.argv[4])
slope = int(sys.argv[5])
forest_share = int(sys.argv[6])
lpa_share = int(sys.argv[7])
turbine_1 = sys.argv[8]

try:
    turbine_2 = sys.argv[9]
except IndexError:
    turbine_2 = None
        

with open(ROOT + "windgenpotential/turbine.yaml", 'r') as stream:
    turbine_config = yaml.safe_load(stream)    
    
with rio.open(ROOT + f'data/country_landuse_results/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}.tif') as f:
    landuse = f.read(1)
    transform = f.transform

with rio.open(ROOT + f'data/country_azimuth/{cntry}-burned-azimuth.tif') as f:
    wind_az = f.read(1)

    
## Routine for turbine placement if 2 trubines are given   
if turbine_2 != None:
        
    #get turbine decision raster 
    with rio.open(ROOT + f'data/country_turbine_decision/{cntry}-{turbine_1}-{turbine_2}-burned-decision.tif') as f:
        wind_tt = f.read(1)
    
    turbine_dict = {1 : turbine_config[turbine_1].get('diameter'), 2 : turbine_config[turbine_2].get('diameter')}


    turbine_mask = geo.place_n_turbines(res = 50, 
                                        landuse_av = landuse,
                                        wind_dir = wind_az[::-1],
                                        turbine_type = wind_tt[::-1], turbine_dict = turbine_dict,
                                        r_radius_factor = 4,
                                        c_radius_factor = 8) 
    
    
## Routine for turbine placement if ony 1 trubine is given
else:     
    turbine_dict = {1 : turbine_config[turbine_1].get('diameter')}

    wind_tt = np.ones(shape = landuse.shape)
    
    turbine_mask = geo.place_n_turbines(res = 50, 
                                        landuse_av = landuse,
                                        wind_dir = wind_az[::-1],
                                        turbine_type = wind_tt, turbine_dict = turbine_dict,
                                        r_radius_factor = 4,
                                        c_radius_factor = 8) 

    ## Infer coordinates for each placed turbines
T0 = transform #r.transform  # upper-left pixel corner affine transform
p1 = Proj("epsg:3035")#Proj(r.crs)
A = turbine_mask[1]# r.read()  # pixel values

# All rows and columns
cols, rows = np.meshgrid(np.arange(A.shape[1]), np.arange(A.shape[0]))

# Get affine transform for pixel centres
T1 = T0 * Affine.translation(0.5, 0.5)
# Function to convert pixel row/column index (from 0) to easting/northing at centre
rc2en = lambda r, c: (c, r) * T1

eastings, northings = np.vectorize(rc2en, otypes=[int, int])(np.where(turbine_mask[1] > 0)[0], np.where(turbine_mask[1] > 0)[1])
ttype = turbine_mask[1][turbine_mask[1] > 0 ]


# Coordinates to list
c = []

for i in range(0,np.where(turbine_mask[1] > 0, 1, 0).sum()):
    c.append(Point(eastings[i], northings[i]))

idx = np.array(range(0,np.where(turbine_mask[1] > 0, 1, 0).sum()))   

df = gpd.GeoDataFrame(index = idx , crs='epsg:3035',
                      data = ttype, geometry=c, columns = ['ttype'])


if turbine_2 != None:
    df.to_file(ROOT + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}-{turbine_2}.gpkg')    
else:
    df.to_file(ROOT + f'data/country_turbine_placements/{cntry}-{scenario}-{urban_distance}-{slope}-{forest_share}-{lpa_share}-{turbine_1}.gpkg')

    


