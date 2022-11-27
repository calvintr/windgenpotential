import geopandas as gpd 
import sys 

ROOT = sys.argv[1]
cntry = sys.argv[2]

import yaml
with open(ROOT + "windgenpotential/countrycode.yaml", 'r') as stream:
    countrycode = yaml.safe_load(stream)  

country = gpd.read_file(ROOT + f'data/country_shapes/{cntry}.gpkg')
cdda = gpd.read_file(ROOT + 'data/input_geodata/WDPA_WDOECM_Nov2022_Public_EU/WDPA_WDOECM_Nov2022_Public_EU.gdb/a00000009.gdbtable')

cdda_country = cdda[cdda.ISO3.str.contains(countrycode[cntry])]
cdda_country_match = gpd.overlay(cdda_country, country, how='intersection')

cdda_country_match.to_crs(3035).to_file(ROOT + f'data/country_pa/{cntry}.gpkg',  driver = 'GPKG')