#!/usr/bin/env python
#Description: A script to create a DEM from lidar data.
"""
Author: Dan Clewley (dac)

Created on: 07 Nov 2014

This file has been created by ARSF Data Analysis Node and
is licensed under the GPL v3 Licence. A copy of this
licence is available to download with this file.

"""

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
   description_str = '''A script to create a DEM from LiDAR data in LAS or ASCII format and optionally patch with a DEM

Typical usage

1) Create DEM from LiDAR files in default projection ({0})
 create_dem_from_lidar.py -o lidar_dsm.dem *LAS

2) Create DEM from LiDAR files in UTM30N projection
 create_dem_from_lidar.py --in_projection UTM30N -o lidar_dsm.dem *LAS

3) Create DEM from LiDAR files and patch with ASTER data
Output DEM in WGS84LL projection
 create_dem_from_lidar.py --aster --out_projection WGS84LL -o lidar_aster_dsm.dem *LAS

4) Create DEM from LiDAR files and patch with ASTER data, output bounds based on navigation data.
Output DEM in WGS84LL projection suitible for use in APL. Also export screenshot in JPEG format.

 create_dem_from_lidar.py --aster --out_projection WGS84LL \\
            -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ \\
            -o 2014_216_lidar_aster_dsm.dem \\
            --screenshot /screenshots/2014_216_lidar_aster_dsm.jpg \\
            ../las1.2

Known issues:
If you don't pass in the correct project path, or there is a problem
finding hyperspectral navigation files will print warning but continue and produce
a DEM much larger than is required. If the DEM is not required for APL you can use
the flag '--lidar_bounds', which only uses the bounds of the lidar data, not navigation files
plus a buffer of {1} m.

'create_dem_from_lidar' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
and is made available under the terms of the GPLv3 license.

'''.format(dem_common.DEFAULT_LIDAR_PROJECTION_GRASS, dem_common.DEFAULT_LIDAR_DEM_BUFFER['N'])

   try:
      parser = argparse.ArgumentParser(description=description_str,formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument("lidarfiles", nargs='+',type=str, help="List or directory containing input LiDAR files")
      parser.add_argument('-o', '--outdem',
                          metavar ='Out DEM',
                          help ='Output name for DEM',
                          required=True)
      parser.add_argument('-s', '--screenshot',
                          metavar ='Out Screenshot File or Directory',
                          help ='Output directory for screenshots or single file for screenshot of mosaic, in JPEG format.',
                          default=None,
                          required=False)
      parser.add_argument('--shadedrelief',
                          action='store_true',
                          help='Create shaded relief images for screenshots',
                          default=False,
                          required=False)
      parser.add_argument('--las',
                          action='store_true',
                          help='Input LiDAR data are in LAS format (default=True)',
                          default=True,
                          required=False)
      parser.add_argument('--ascii',
                          action='store_true',
                          help='Input LiDAR data are in ASCII format (default=False)',
                          default=False,
                          required=False)
      parser.add_argument('-r', '--resolution',
                          metavar ='Resolution',
                          help ='Resolution for output DEM (default={})'.format(dem_common.DEFAULT_LIDAR_RES_METRES),
                          default=dem_common.DEFAULT_LIDAR_RES_METRES,
                          required=False)
      parser.add_argument('--in_projection',
                          metavar ='In Projection',
                          help ='Input projection (e.g., UTM30N; default={})'.format(dem_common.DEFAULT_LIDAR_PROJECTION_GRASS),
                          default=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                          required=False)
      parser.add_argument('--out_projection',
                          metavar ='Out Projection',
                          help ='Out projection. Default is same as input',
                          default=None,
                          required=False)
      parser.add_argument('-n', '--nav',
                          metavar ='Nav file',
                          help ='Navigation data (.sbet / .sol file) used if patching with another DEM',
                          default=None,
                          required=False)
      parser.add_argument('-p', '--project',
                          metavar ='Main project directory',
                          help ='Main project directory, used if patching with another DEM',
                          default='.',
                          required=False)
      parser.add_argument('--demmosaic',
                          metavar ='Input DEM mosaic',
                          help ='''Input DEM mosaic to patch with in GDAL compatible format. Vertical datum needs to be the same
                                   as output projection.
                                   Only required for non-standard DEM. Use "--aster" or "--nextmap" for standard DEMs.''',
                          required=False,
                          default=None)
      parser.add_argument('--aster',
                          action='store_true',
                          help='Patch with ASTER data ({})'.format(dem_common.ASTER_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--nextmap',
                          action='store_true',
                          help='Patch with Nextmap data ({})'.format(dem_common.NEXTMAP_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--srtm',
                          action='store_true',
                          help='Use SRTM data ({})'.format(dem_common.SRTM_MOSAIC_FILE),
                          default=False,
                          required=False)
      parser.add_argument('--hyperspectral_bounds',
                          action='store_true',
                          help='''If patching with another DEM, get extent from hyperspectral navigation data,
                                  recommended if DEM is to be used with APL and navigation data are available. This is the default behaviour''',
                          default=False,
                          required=False)
      parser.add_argument('--lidar_bounds',
                          action='store_true',
                          help='''If patching with another DEM, get extent from lidar data plus default buffer of {} m.
                                  If DEM is not required to be used with APL this option is recommended.'''.format(dem_common.DEFAULT_LIDAR_DEM_BUFFER['N']),
                          default=False,
                          required=False)
      parser.add_argument('--fill_lidar_nulls',
                          action='store_true',
                          help='''Fill NULL values in LiDAR data using interpolation.
                                  Not available if patching with another DEM''',
                          default=False,
                          required=False)
      parser.add_argument('-t', '--rastertype',
                          metavar ='Output raster type',
                          help ='Output raster type (default DSM)',
                          default='DSM',
                          required=False)
      parser.add_argument('--keepgrassdb',
                          action='store_true',
                          help='Keep GRASS database (default=False)',
                          default=False,
                          required=False)
      args=parser.parse_args()

      # Set format for input lidar data
      lidar_format = 'LAS'
      if args.ascii:
         lidar_format = 'ASCII'

      # Set source DEM (if patching)
      # ASTER DEM
      if args.aster:
         dem_source = 'ASTER'
      # SRTM DEM
      elif args.srtm:
         dem_source = 'SRTM'
      # NEXTMap DEM
      elif args.nextmap:
         dem_source = 'NEXTMAP'
      else:
         dem_source = None

      # Set if hypersectral bounds are to be used or lidar
      if args.lidar_bounds:
         use_lidar_bounds = True
      else:
         use_lidar_bounds = False

      if args.lidar_bounds and args.hyperspectral_bounds:
         dem_common_functions.ERROR("Can't use '--lidar_bounds' and '--hyperspectral_bounds' together.")
         sys.exit(1)

      in_lidar_projection = args.in_projection.upper()

      dem_lidar.lidar_utilities.create_patched_lidar_mosaic(args.lidarfiles,
                                                args.outdem,
                                                in_lidar_projection=in_lidar_projection,
                                                resolution=args.resolution,
                                                out_projection=args.out_projection,
                                                screenshot=args.screenshot,
                                                shaded_relief_screenshots=args.shadedrelief,
                                                out_raster_type=args.rastertype,
                                                dem_source=dem_source,
                                                dem_mosaic=args.demmosaic,
                                                project=args.project,
                                                nav=args.nav,
                                                lidar_bounds=use_lidar_bounds,
                                                fill_lidar_nulls=args.fill_lidar_nulls)

   except KeyboardInterrupt:
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      dem_common_functions.ERROR(err)
      sys.exit(1)
