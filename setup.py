#!/usr/bin/env python
"""
Setup script for arsf_dem
"""

import glob, os
from numpy.distutils.core import setup

scripts_list = ['scripts/create_apl_dem.py',
                'scripts/create_dem_from_lidar.py',
                'scripts/demcompare.py']

setup(
  name='arsf_dem',
  version = '0.1',
  description = 'ARSF-DAN utilities for working with DEMs',
  url = 'https://arsf-dan.nerc.ac.uk/trac/',
  packages = ['arsf_dem','arsf_dem.dem_lidar'],
  package_dir={'arsf_dem': 'arsf_dem'},
  package_data={'arsf_dem' : ['arsf_dem.cfg']},
  scripts = scripts_list,
)
