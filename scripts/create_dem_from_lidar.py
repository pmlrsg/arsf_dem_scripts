#!/usr/bin/env python
#Description: A script to create a DEM from lidar data.
"""
Author: Dan Clewley (dac)

Created on: 07 Nov 2014

Known issues: 

License restrictions: Depends on GRASS library, subject to GNU GPL

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import glob
import argparse
import tempfile
import shutil
# Import DEM library
try:
   from arsf_dem import dem_common
   from arsf_dem import dem_utilities
   from arsf_dem import dem_nav_utilities
   from arsf_dem import dem_lidar
   from arsf_dem import grass_library
   from arsf_dem import common_functions
except ImportError as err:
   print("Could not import ARSF DEM library.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)


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

Report bugs to:

https://arsf-dan.nerc.ac.uk/trac/ticket/545

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
      parser.add_argument('--keepgrassdb',
                          action='store_true',
                          help='Keep GRASS database (default=False)',
                          default=False,
                          required=False)
      args=parser.parse_args()

      # Set up list to hold temp files
      temp_file_list = []

      # Input projection for lidar files
      in_lidar_projection = args.in_projection.upper()
      
      # Set output projection - if not provided assume
      # the same as input.
      if args.out_projection is None:
         out_patched_projection = in_lidar_projection
      else:
         out_patched_projection = args.out_projection.upper()

      # Set format for input lidar data
      lidar_format = 'LAS'
      if args.ascii:
         lidar_format = 'ASCII'

      # If lidar is in UKBNG and output is not UKBNG need to apply vertical datum
      # offset.
      # If not UKBNG (likely UTM) assume no vertical shift is required
      if in_lidar_projection == 'UKBNG' and out_patched_projection != 'UKBNG':
         lidar_separation_file = dem_common.UKBNG_SEP_FILE_UKBNG
         lidar_separation_file_is_ascii = dem_common.UKBNG_SEP_FILE_UKBNG_IS_ASCII
      else:
         lidar_separation_file = None
         lidar_separation_file_is_ascii = False

      # Check if we want to patch with a DEM (default is not)
      patch_with_dem = False
   
      # ASTER DEM
      if args.aster:
         in_dem_mosaic = dem_common.ASTER_MOSAIC_FILE
         in_dem_mosaic_projection = 'WGS84LL'
         # If relative to UKBNG is required apply seperate
         # shift file equal to (EGM96 to WGS-84) - (UKBNG to WGS-84)
         if out_patched_projection == 'UKBNG':
            separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84
            ascii_separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84_IS_ASCII
         # Else shift to WGS-84 vertical datum
         else:
            separation_file = dem_common.WWGSG_FILE
            ascii_separation_file = dem_common.WWGSG_FILE_IS_ASCII
         out_res = dem_common.ASTER_RES_DEGREES
         patch_with_dem = True
      
      # NEXTMap DEM
      elif args.nextmap:
         in_dem_mosaic = dem_common.NEXTMAP_MOSAIC_FILE
         in_dem_mosaic_projection = 'UKBNG'
         # If output projection if UKBNG no vertical shift is required
         if out_patched_projection == 'UKBNG':
            separation_file = None
            ascii_separation_file = False
         # Else shift to WGS-84 vertical datum
         else:
            separation_file = dem_common.UKBNG_SEP_FILE_UKBNG
            ascii_separation_file = dem_common.UKBNG_SEP_FILE_UKBNG_IS_ASCII
         out_res = dem_common.NEXTMAP_RES_DEGREES
         patch_with_dem=True
      
      # Custom DEM
      elif args.demmosaic is not None:
         in_dem_mosaic = args.demmosaic
         in_dem_mosaic_projection = 'WGS84LL'
         separation_file = None
         ascii_separation_file = False
         out_res = None
         patch_with_dem = True

      # Check if patched DEM should be subset to navigation or based on the DEM mosaic
      subset_to_navigation = False
      if patch_with_dem:
         if (args.project != ".") or (args.nav is not None) or args.hyperspectral_bounds:
            # If any of these options are set probably want to subset to hyperspectral
            subset_to_navigation = True
         else:
            subset_to_navigation = False

      # Create temp file for DEM (if required)
      temp_mosaic_dem = tempfile.mkstemp(prefix='dem_subset',suffix='.dem', dir=dem_common.TEMP_PATH)[1]
      temp_mosaic_dem_header = os.path.splitext(temp_mosaic_dem)[0] + '.hdr'
      temp_lidar_dem = tempfile.mkstemp(prefix='lidar_dem_mosaic',suffix='.dem', dir=dem_common.TEMP_PATH)[1]
      temp_lidar_dem_header = os.path.splitext(temp_lidar_dem)[0] + '.hdr'

      temp_file_list.extend([temp_mosaic_dem, temp_mosaic_dem_header, temp_lidar_dem, temp_lidar_dem_header])

      lidar_dem_mosaic = args.outdem
      lidar_dem_mosaic_header = os.path.splitext(lidar_dem_mosaic)[0] + '.hdr'
      outdem_header = os.path.splitext(args.outdem)[0] + '.hdr'

      # If a single file is provided for the screenshot and patching with a DEM 
      # want screenshot of patched DEM not lidar.
      if not os.path.isdir(args.screenshot) and patch_with_dem:
         lidar_screenshots = None
      else:
         lidar_screenshots = args.screenshot
   
      # Create DSM from individual lidar lines and patch together
      dem_lidar.lidar_utilities.create_lidar_mosaic(args.lidarfiles,lidar_dem_mosaic,
                     out_screenshot=lidar_screenshots,
                     shaded_relief_screenshots=args.shadedrelief,
                     in_projection=args.in_projection,
                     resolution=args.resolution,
                     nodata=dem_common.NODATA_VALUE,
                     lidar_format=lidar_format,
                     raster_type='DSM',
                     fill_nulls=False)
      
      # Check if input projection is equal to output projection
      if in_lidar_projection != out_patched_projection:
         dem_utilities.call_gdalwarp(lidar_dem_mosaic, temp_lidar_dem,
                s_srs=grass_library.grass_projection_to_proj4(in_lidar_projection),
                t_srs=grass_library.grass_projection_to_proj4(out_patched_projection))

         # Check if a vertical datum shift is required.
         # At the moment only consider UKBNG to WGS84LL
         if in_lidar_projection == 'UKBNG' and out_patched_projection == 'WGS84LL':
            print('Applying vertical offset to LiDAR mosaic')
            dem_utilities.offset_null_fill_dem(temp_lidar_dem, temp_lidar_dem, 
                                                    import_to_grass=True,
                                                    separation_file=dem_common.UKBNG_SEP_FILE_WGS84,
                                                    ascii_separation_file=dem_common.UKBNG_SEP_FILE_WGS84_IS_ASCII,
                                                    fill_nulls=False,
                                                    nodata=dem_common.NODATA_VALUE,
                                                    remove_grassdb=False)
         lidar_dem_mosaic = temp_lidar_dem

      if patch_with_dem:
         print('')
         common_functions.PrintTermWidth('Patching with {}'.format(in_dem_mosaic), padding_char='*')
         print('')
         if subset_to_navigation:
            try:
               dem_nav_utilities.subset_dem_to_nav(in_dem_mosaic, 
                                 args.nav, args.project,
                                 out_demfile=temp_mosaic_dem,
                                 separation_file=separation_file,
                                 ascii_separation_file=ascii_separation_file,
                                 in_dem_projection=grass_library.grass_projection_to_proj4(in_dem_mosaic_projection),
                                 out_projection=grass_library.grass_projection_to_proj4(out_patched_projection),
                                 nodata=dem_common.NODATA_VALUE,
                                 out_res=None,
                                 remove_grassdb=True, 
                                 fill_nulls=True)        
            except Exception as err:
               common_functions.ERROR('Could not subset DEM to navigation data.\n{}.'.format(err))
               print('If the DEM is not required for use in APL, try using the "--lidar_bounds" flag')
         else:
            print('Getting bounding box from LiDAR mosaic')
            # Get bounding box from output lidar mosaic
            lidar_bb = dem_utilities.get_gdal_dataset_bb(lidar_dem_mosaic, output_ll=True)
            buffered_lidar_bb = dem_lidar.lidar_utilities.get_lidar_buffered_bb(lidar_bb)

            dem_utilities.subset_dem_to_bounding_box(in_dem_mosaic, 
                                 out_demfile=temp_mosaic_dem, 
                                 bounding_box=buffered_lidar_bb,
                                 separation_file=separation_file,
                                 ascii_separation_file=ascii_separation_file,
                                 in_dem_projection=grass_library.grass_projection_to_proj4(in_dem_mosaic_projection),
                                 out_projection=grass_library.grass_projection_to_proj4(out_patched_projection),
                                 nodata=dem_common.NODATA_VALUE,
                                 out_res=None,
                                 remove_grassdb=True, 
                                 fill_nulls=True) 

         dem_utilities.patch_files([lidar_dem_mosaic, temp_mosaic_dem], 
                     out_file=args.outdem,
                     import_to_grass=True,
                     nodata=dem_common.NODATA_VALUE,
                     projection=out_patched_projection,
                     grassdb_path=None,
                     remove_grassdb=True) 

      # Check if file was reprojected but not patched (if so need to move from temp file)
      elif in_lidar_projection != out_patched_projection:
         shutil.move(lidar_dem_mosaic,args.outdem)
         shutil.move(lidar_dem_mosaic_header,outdem_header)

      # Try to export screenshot if path or file is provided.
      # Only needed if patching with DEM, else will have been done earlier.
      if patch_with_dem:
         try:
            if (args.screenshot is not None) and not os.path.isdir(args.screenshot):
               dem_utilities.export_screenshot(args.outdem, args.screenshot,shaded_relief=args.shadedrelief)
            elif os.path.isdir(args.screenshot):
               mosaic_screenshot = dem_utilities.get_screenshot_path(args.outdem, args.screenshot)
               dem_utilities.export_screenshot(args.outdem, mosaic_screenshot, shaded_relief=args.shadedrelief)
         except TypeError:
            pass

      # Remove temp files created
      for temp_file in temp_file_list:
         if os.path.isfile(temp_file):
            os.remove(temp_file)

   except KeyboardInterrupt:
      # Remove temp files created
      for temp_file in temp_file_list:
         if os.path.isfile(temp_file):
            os.remove(temp_file)
      sys.exit(2)

   except Exception as err:
      # Remove temp files created
      for temp_file in temp_file_list:
         if os.path.isfile(temp_file):
            os.remove(temp_file)
      common_functions.ERROR(err)
      sys.exit(1)

