#!/usr/bin/env python
#Description: A script to create a DEM suitible for use in APL from ASTER, NextMap or another DEM mosaic. Uses arsf_dem library
"""
Author: Dan Clewley (dac)

Created on: 29 October 2014

License restrictions: Depends on GRASS library, subject to GNU GPL

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import sys
import argparse

# Import DEM library
try:
   from arsf_dem import dem_common
   from arsf_dem import dem_nav_utilities
   from arsf_dem import common_functions
except ImportError as err:
   print("Could not import ARSF DEM library", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

#: Debug mode
DEBUG = False

if __name__ == '__main__':

   description_str = '''A script to create a DEM for use in APL subset to bounds
of hyperspectral navigation data.

Typical usage:

1) Create Next map DEM

 create_apl_dem.py --nextmap -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_NEXTMAP.dem

2) Create ASTER DEM

 create_apl_dem.py --aster -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_ASTER.dem

3) Create STRM DEM

 create_apl_dem.py --srtm -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_SRTM.dem

4) Create DEM from custom dataset, where heights are relative to geoid

 create_apl_dem.py --demmosaic local_dem_egm96.tif --separation_file {0} \\
           -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_custom.dem

5) Create DEM from custom dataset, where heights are already relative to WGS-84 ellipsoid

 create_apl_dem.py --demmosaic local_dem_utm10n.bil \\
           -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_custom.dem

6) Create DEM from ASTER using post-processed bil format navigation data (for delivered data)

 create_apl_dem.py --aster --bil_navigation flightlines/navigation -o 2014_216_aster.dem

7) Create a DEM from downloaded SRTM tiles for use in APL using processed navigation files

 # Create VRT mosaic of downloaded tiles

 gdalbuildvrt srtm_mosaic.vrt *1arc_v3.tif

 # Create DEM

 create_apl_dem.py --demmosaic strm_mosaic.vrt --separation_file {0} \\
           --bil_navigation flightlines/navigation -o 2014_216_strm.dem

If calling from within the project directory, there should be no need to specify the
project path as it will be found from the current location.

Known issues:
If the correct project path is not found or passed in, or for another reason
there is a problem finding hyperspectral navigation files the script will
print a warning but continue and produce a DEM much larger than required.

Report bugs to:

https://arsf-dan.nerc.ac.uk/trac/ticket/545

   '''.format(dem_common.WWGSG_FILE)

   try:
      parser = argparse.ArgumentParser(description=description_str, formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument('-o', '--outdem',
                          metavar ='Out DEM',
                          help ='''Output name for DEM.
                          If not provided will output to standard location for hyperspectral data processing.''',
                          required=False,
                          default=None)
      parser.add_argument('-n', '--nav',
                          metavar ='Nav file',
                          help ='Navigation data (.sol / .sbet file)',
                          default=None,
                          required=False)
      parser.add_argument('-p', '--project',
                          metavar ='Main project directory',
                          help ='Main project directory (default=".")',
                          default='.',
                          required=False)
      parser.add_argument('--aster',
                          action='store_true',
                          help='Use ASTER data ({})'.format(dem_common.ASTER_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--nextmap',
                          action='store_true',
                          help='Use Nextmap data ({})'.format(dem_common.NEXTMAP_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--srtm',
                          action='store_true',
                          help='Use SRTM data ({})'.format(dem_common.SRTM_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--demmosaic',
                          metavar ='Input DEM mosaic',
                          help ='Input DEM mosaic. For non-standard DEM.\
                                 Use "--aster" or "--nextmap" for standard DEMs.',
                          required=False,
                          default=None)
      parser.add_argument('--separation_file',
                          metavar ='Seperation file',
                          help ='''File with Height offset to add if "--demmosaic" is used and
                                 DEM heights are not relative to WGS-84 elepsoid.
                                 Not required if using "--aster", "--nextmap" or "--srtm" for standard DEMs.''',
                          required=False,
                          default=None)
      parser.add_argument('-b', '--bil_navigation',
                          metavar ='BIL Navigation Files',
                          help ='''Directory containing post-processed navigation files in BIL format.
                                   By default raw navigation data will be used for "--project".
                                   If this is not available (e.g., for ARSF-DAN delivered data) use this option and point to
                                   "flightlines/navigation" within delivery directory''',
                          default=None,
                          required=False)
      parser.add_argument('--keepgrassdb',
                          action='store_true',
                          help='Keep GRASS database (default=False)',
                          default=False,
                          required=False)
      args=parser.parse_args()

      dem_source = None

      # ASTER DEM
      if args.aster:
         dem_source = 'ASTER'
      # NEXTMap DEM
      elif args.nextmap:
         dem_source = 'NEXTMAP'
      # SRTM DEM
      elif args.srtm:
         dem_source = 'SRTM'
      # Custom DEM
      elif args.demmosaic is not None:
         dem_source = 'USER'
      else:
         parser.print_help()
         print('\nMust provide at least "--nextmap", "--aster" or "--srtm" flag for standard DEM locations or supply custom DEM with "--demmosaic"', file=sys.stderr)
         sys.exit(1)

      dem_nav_utilities.create_apl_dem_from_mosaic(args.outdem,
                     dem_source=dem_source,
                     dem_mosaic=args.demmosaic,
                     separation_file=args.separation_file,
                     project=args.project,
                     nav=args.nav,
                     bil_navigation=args.bil_navigation,
                     remove_grassdb=(not args.keepgrassdb))

   except KeyboardInterrupt:
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      common_functions.ERROR(err)
      sys.exit(1)
