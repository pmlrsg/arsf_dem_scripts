#!/usr/bin/env python
"""
Setup script for arsf_dem
"""

import glob, os, sys
from distutils.core import setup

# For windows also copy batch files, incase .py files
# aren't associated with Python.
if sys.platform == 'win32':
   scripts_list = ['scripts\\create_apl_dem.py',
                   'scripts\\create_apl_dem.bat',
                   'scripts\\create_dem_from_lidar.py',
                   'scripts\\create_dem_from_lidar.bat',
                   'scripts\\las_to_dtm.py',
                   'scripts\\las_to_dtm.bat',
                   'scripts\\las_to_dsm.py',
                   'scripts\\las_to_dsm.bat']
else:
   scripts_list = ['scripts/create_apl_dem.py',
                   'scripts/create_dem_from_lidar.py',
                   'scripts/demcompare.py',
                   'scripts/las_to_dsm.py',
                   'scripts/las_to_dtm.py']

setup(
  name='arsf_dem',
  version = '0.1',
  description = 'ARSF-DAN utilities for working with DEMs',
  url = 'https://arsf-dan.nerc.ac.uk/trac/',
  packages = ['arsf_dem','arsf_dem.dem_lidar'],
  package_dir={'arsf_dem': 'arsf_dem'},
  package_data={'arsf_dem' : ['arsf_dem.cfg']},
  data_files=[('share/grass_db_template/WGS84LL/PERMANENT/',glob.glob('data/grass_db_template/WGS84LL/PERMANENT/*')),
              ('share/grass_db_template/UKBNG/PERMANENT/',glob.glob('data/grass_db_template/UKBNG/PERMANENT/*')) ],
  scripts = scripts_list,
)
