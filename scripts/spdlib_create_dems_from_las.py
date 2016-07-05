#!/usr/bin/env python
#Description: A script to generate DTM, DSM and CHM from LAS files using SPDLib
"""
Author: Dan Clewley (dac)

Generates a DTM, DSM and optionally CHM from LAS files using SPDLib

Created on: 09 May 2016

"""
from __future__ import print_function
import argparse
import os
import shutil
import sys
import tempfile

from arsf_dem import dem_common
from arsf_dem import dem_lidar
from arsf_dem import dem_common_functions
from arsf_dem import grass_library

#: Debug mode
DEBUG = dem_common.DEBUG

#: Set interpolation method to use
interpolation = dem_common.SPD_DEFAULT_INTERPOLATION

def create_directory(directory_name):
   """
   Check if a directory exists and create if it doesn't
   """
   if not os.path.isdir(directory_name):
      os.makedirs(directory_name)


if __name__ == '__main__':
   description_str = '''Create a Digital Terrain Model (DTM), Digital Surface
 Model (DSM) and optionally Canopy Height Model (CHM) from LAS file(s). Uses
 SPDLib.

SPDLib is available under a GPLv3 license. For more details see:

http://spdlib.org/

Bunting, P., Armston, J., Clewley, D., & Lucas, R. M. (2013). Sorted pulse data
 (SPD) library-Part II: A processing framework for LiDAR data from pulsed laser
 systems in terrestrial environments. Computers and Geosciences, 56, 207-215.
 doi:10.1016/j.cageo.2013.01.010

'spdlib_create_dems_from_las' was created by ARSF-DAN at Plymouth Marine
 Laboratory (PML) and is made available under the terms of the GPLv3 license.

'''


   temp_dir = tempfile.mkdtemp(dir=dem_common.TEMP_PATH)
   try:
      parser = argparse.ArgumentParser(description=description_str)
      parser.add_argument("lasfile", nargs='+', type=str,
                          help="Input LAS file")
      parser.add_argument('-o', '--out_dir',
                          help ='Base output directory. '
                                'Will create subdirectories for "dsm", "dtm" '
                                'and "chm" within this',
                          required=True)
      parser.add_argument('-r', '--resolution',
                          help ='Resolution for output DEM (Default={})'
                                ''.format(dem_common.DEFAULT_LIDAR_RES_METRES),
                          default=dem_common.DEFAULT_LIDAR_RES_METRES,
                          required=False)
      parser.add_argument('--projection',
                          help ='Input projection (e.g., UTM30N)',
                          default=None,
                          required=True)
      parser.add_argument('--chm',
                          help='Export raster Canopy Height Model (CHM)',
                          default=False,
                          action='store_true',
                          required=False)
      args=parser.parse_args()

      base_out_dir = os.path.abspath(args.out_dir)

      out_dtm_dir = os.path.join(base_out_dir, 'dtm')
      out_dsm_dir = os.path.join(base_out_dir, 'dsm')
      out_chm_dir = os.path.join(base_out_dir, 'chm')

      # Create output directories if they don't exist
      create_directory(out_dtm_dir)
      create_directory(out_dsm_dir)
      if args.chm:
         create_directory(out_chm_dir)

      las_basename = os.path.basename(args.lasfile[0])
      las_basename = os.path.splitext(las_basename)[0]

      if len(args.lasfile) > 0:
         las_basename = '{}_merged'.format(las_basename)

      out_dtm = os.path.join(out_dtm_dir, '{}_dtm.dem'.format(las_basename))
      out_dsm = os.path.join(out_dsm_dir, '{}_dsm.dem'.format(las_basename))
      out_chm = os.path.join(out_chm_dir, '{}_chm.dem'.format(las_basename))

      # Tempory LAS file (with class 7 dropped)
      tmp_las_file = os.path.join(temp_dir, 'merged_las.las')
      # Tempory SPD file (if classifying ground returns)
      spd_convert_out = os.path.join(temp_dir, 'merged_las2spd.spd')

      # WKT file containing projection (required by SPDLib)
      wkt_tmp = os.path.join(temp_dir,
                             '{}.wkt'.format(args.projection.lower()))
      grass_library.grass_location_to_wkt(args.projection, wkt_tmp)
      # Merge LAS files (if multiple are passed in) and drop
      # class 7
      # SPDLib doesn't ignore points flagged as noise so
      # need to create LAS file without class 7 anyway - merge command is
      # easiest way to do this.
      args.lasfile = [os.path.abspath(f) for f in args.lasfile]
      dem_lidar.lastools_lidar.merge_las(args.lasfile,
                                         tmp_las_file,
                                         drop_class=7)

      # Create DTM - keep SPD file
      grd_spd = dem_lidar.spdlib_lidar.las_to_dtm(tmp_las_file, out_dtm,
                                                  interpolation=interpolation,
                                                  out_raster_format='ENVI',
                                                  bin_size=args.resolution,
                                                  wkt=wkt_tmp,
                                                  keep_spd=True)

      # Generate DSM from existing SPD file
      dem_lidar.spdlib_lidar.spd_to_dsm(grd_spd, out_dsm,
                                        interpolation=interpolation,
                                        out_raster_format='ENVI',
                                        bin_size=args.resolution)

      # If a CHM is requested generate this from existing SPD file
      if args.chm:
         dem_lidar.spdlib_lidar.spd_to_chm(grd_spd, out_chm,
                                           interpolation=interpolation,
                                           out_raster_format='ENVI',
                                           bin_size=args.resolution)

      # Remove all temp files
      shutil.rmtree(temp_dir)

   except KeyboardInterrupt:
      shutil.rmtree(temp_dir)
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      shutil.rmtree(temp_dir)
      dem_common_functions.ERROR(err)
      sys.exit(1)
