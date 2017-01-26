#!/usr/bin/env python
"""
Setup script for arsf_dem

This file has been created by ARSF Data Analysis Node and
is licensed under the GPL v3 Licence. A copy of this
licence is available to download with this file.

"""

import glob, os, sys
from distutils.core import setup

# For windows also copy batch files, incase .py files
# aren't associated with Python.
if sys.platform == 'win32':
    scripts_list = glob.glob('scripts\\*.py')
    scripts_list.extend(glob.glob('scripts\\*.bat'))
else:
    scripts_list = glob.glob('scripts/*.py')

setup(
  name='arsf_dem',
  version = '0.1',
  description = 'ARSF-DAN utilities for working with DEMs',
  url = 'https://arsf-dan.nerc.ac.uk/trac/',
  packages = ['arsf_dem','arsf_dem.dem_lidar'],
  package_dir={'arsf_dem': 'arsf_dem'},
  package_data={'arsf_dem' : ['arsf_dem.cfg']},
  data_files=[(os.path.join('share','grass_db_template','WGS84LL','PERMANENT'),glob.glob(os.path.join('data','grass_db_template','WGS84LL','PERMANENT','*'))),
              (os.path.join('share','grass_db_template','UKBNG','PERMANENT'),glob.glob(os.path.join('data','grass_db_template','UKBNG','PERMANENT','*')))],
  scripts = scripts_list,
)
