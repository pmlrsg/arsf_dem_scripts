#!/usr/bin/env python
#Description: A script to create a DSM from as LAS file.
"""
Author: Dan Clewley (dac)

Created on: 16 March 2015

Known issues:

License restrictions: Depends on GRASS library, subject to GNU GPL.
Can also use SPDLib (GPL) and LAStools (commercial license required)

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import sys
import argparse
# Import DEM library
try:
   from arsf_dem import dem_common
   from arsf_dem import dem_utilities
   from arsf_dem import dem_lidar
   from arsf_dem import dem_common_functions
except ImportError as err:
   print("Could not import ARSF DEM library.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

#: Debug mode
DEBUG = False

if __name__ == '__main__':
   description_str = '''Create a Digital Surface Model (DSM) from a LAS file.

Report bugs to:

https://arsf-dan.nerc.ac.uk/trac/ticket/545

or email arsf-processing@pml.ac.uk

'''

   try:
      parser = argparse.ArgumentParser(description=description_str,formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument("lasfile", nargs=1,type=str, help="Input LAS file")
      parser.add_argument('-o', '--outdem',
                          metavar ='Out DEM',
                          help ='Output name for DTM',
                          required=True)
      parser.add_argument('--hillshade',
                          metavar ='Out Hillshade',
                          help ='Output name for hillshade image (optional)',
                          default=None,
                          required=False)
      parser.add_argument('-r', '--resolution',
                          metavar ='Resolution',
                          help ='Resolution for output DEM (default={})'.format(dem_common.DEFAULT_LIDAR_RES_METRES),
                          default=dem_common.DEFAULT_LIDAR_RES_METRES,
                          required=False)
      parser.add_argument('--projection',
                          metavar ='In Projection',
                          help ='Input projection (e.g., UTM30N)',
                          default=None,
                          required=False)
      parser.add_argument('--method',
                          metavar ='Method',
                          help ='Software package to use: GRASS (Default), SPDLib or LAStools.',
                          default='GRASS',
                          required=False)
      args=parser.parse_args()

      dem_lidar.las_to_dsm(args.lasfile[0], args.outdem,
                           resolution=args.resolution,
                           projection=args.projection,
                           method=args.method)

      # If hillshade image is required, create this
      if args.hillshade is not None:
         out_raster_format = dem_utilities.get_gdal_type_from_path(args.hillshade)

         dem_utilities.call_gdaldem(args.outdem, args.hillshade,
                      dem_product='hillshade',
                      of=out_raster_format)

   except KeyboardInterrupt:
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      dem_common_functions.ERROR(err)
      sys.exit(1)
