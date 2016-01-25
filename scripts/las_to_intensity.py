#!/usr/bin/env python
#Description: A script to create an intensity raster from a LAS file.
"""
Author: Dan Clewley (dac)

Created on: 19 January 2016

"""
# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import sys
import argparse
# Import DEM library
try:
   from arsf_dem import dem_common
   from arsf_dem import dem_lidar
   from arsf_dem import dem_common_functions
except ImportError as err:
   print("Could not import ARSF DEM library.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

#: Debug mode
DEBUG = False

if __name__ == '__main__':
   description_str = '''Create an Intensity Raster from a LAS file.

'las_to_intensity' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
and is made available under the terms of the GPLv3 license.

The programs used by las_to_intensity are available under a range of licenses, please
consult their respective documentation for more details.

'''

   try:
      parser = argparse.ArgumentParser(description=description_str,formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument("lasfile", nargs=1,type=str, help="Input LAS file")
      parser.add_argument('-o', '--outintensity',
                          metavar ='Out Intensity',
                          help ='Output name for Intensity image',
                          required=True)
      parser.add_argument('-r', '--resolution',
                          metavar ='Resolution',
                          help ='Resolution for output image (default={})'.format(dem_common.DEFAULT_LIDAR_RES_METRES),
                          default=dem_common.DEFAULT_LIDAR_RES_METRES,
                          required=False)
      parser.add_argument('--projection',
                          metavar ='In Projection',
                          help ='Input projection (e.g., UTM30N)',
                          default=None,
                          required=False)
      parser.add_argument('--method',
                          metavar ='Method',
                          help ='Software package to use. Options are:\n{}'.format(','.join(dem_lidar.LAS_TO_INTENSITY_METHODS)),
                          default='GRASS',
                          required=False)
      args=parser.parse_args()

      dem_lidar.las_to_intensity(args.lasfile[0], args.outintensity,
                                 resolution=args.resolution,
                                 projection=args.projection,
                                 method=args.method)

   except KeyboardInterrupt:
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      dem_common_functions.ERROR(err)
      sys.exit(1)
