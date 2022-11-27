# CDS ERA5 Downloader via wrapped atlite.Cutout

from utils import data
import yaml 

ROOT = 'C:/CaT/Masterthesis/repository/' 

with open(ROOT + "windgenpotential/countrycode.yaml", 'r') as stream:
    countrycode = yaml.safe_load(stream)  

countries = [i for i in countrycode.keys()]

for i in countries:

	data.cutout_download(i, 
						'2011-01-01', '2021-12-31',
						ROOT + 'data/era5/',
						freq = 'Y',
						shape_filter = ROOT + 'data/input_geodata/luisa.tif',
						feature = ['wind']
						)



