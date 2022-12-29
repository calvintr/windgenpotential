## Overview

This repository contains the codework of the master thesis project:
#### Onshore wind generation in Europe: A GIS-based  sensitivity analysis of future technical potential under  spatial constraints

All neccesary configuration files, Python scripts and Jupyter Notebooks to replicate calculations and analysis can be found here.

Tied to this repository is the following OwnCloud filestorage:
https://tubcloud.tu-berlin.de/s/iCgikHZeQMWpfKW

To avoid path conflicts, download the 'Masterthesis' Project folder. Place the contents ('data', 'results')-folders on the level of this cloned repository. 

The key Jupyter Notebooks 'master.ipynb' and 'analysis.ipynb' allow for the provision of a ROOT filepath that should lead to the folder level of the windgenpotential repository as well as the data and result folder. 

## Necessary input data

The related scripts work on 5 key data inputs: 

Within *data/input_geodata/*:

 - **LUISA Basemap 2018 (50m .tif raster)**
	 - [LINK](http://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/LUISA/EUROPE/Basemaps/LandUse/2018/LATEST/)
	 - provided in the OwnCloud filestorage
- **Corine Land Cover 2018 (100m .tif raster)**
	- [LINK](https://land.copernicus.eu/pan-european/corine-land-cover/clc2018?tab=download)
	- save as corine.tif
	- provided in the OwnCloud filestorage
- **World Database on Protected Areas** for Europe
	- [LINK](https://www.protectedplanet.net/region/EU)
	- place full unzipped folder within *input_geodata*
- **EU-DEM Slope Data for Europe**
	- [LINK](https://ec.europa.eu/eurostat/de/web/gisco/geodata/reference-data/elevation/eu-dem/slope)
	- place full unzipped folder within *input_geodata*

Within *'data/gwa'*:

 - **Global Wind Atlas country data**
	 - [LINK](https://globalwindatlas.info/en)
	 - provided in the OwnCloud filestorage
	 - Notebook gwa_bounds_precalc.ipynb provides inshight on how the country shapes were created.

Within *'data/era5'*:

 - **ERA5 single level wind features**
	 - [LINK](https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels)
	 - download routine provided in era5_downloader.py script

Within *'data/country_era5_gwa_cf'*:

 - Pre calculated correction factors for the ERA5 Data from the GWA data
 - Can be calculated with notebook era5_gwa_cf_prep.ipynb
 - Provided withon OwnCloud filestorage for all countries of the analysis

## Calculations

0. A requirement for the following calculations is the installation of the related python envionrment, provided as ***environment.yaml*** in the repository. 
1. ***master.ipynb*** serves as the 'control' notebook to run all of the necesseary calculations to create the preliminary inputs and final results. The necessary repository scripts are started from the notebook via the `subprocess` library. Therefore a valid pipe to the python enironment needs to be established that may be System specific. Details are pointed out within the notebook.
2. A set of desired restrictions can be specified in *master.ipynb*. Provided functions subsequently scan the 'data' folder if the preliminary inputs and final results exist.
3.  `result_manager.compute_prelims(result_manager.pre_false)` starts the calculation of the preliminary files. `result_manager.compute_res(result_manager.pre_res)` starts the calculation of the final results, provided all preliminaries are computed
4. ***analysis.ipynb*** performs the analysis for all Figures and Tables within presented in the Masterthesis document. Order and numbering are accordingly specified. 
