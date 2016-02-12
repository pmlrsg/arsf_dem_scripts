#!/usr/bin/env python
#Description: A script to create a DSM from as LAS file.
"""
Load LiDAR data in LAS or ASCII format to GRASS for further processing.

Author: Dan Clewley (dac)

Created on: 10 Febuary 2016

"""
# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

from __future__ import print_function
import glob
import os
import sys
import argparse
# Import DEM library
try:
   from arsf_dem import dem_common
   from arsf_dem.dem_lidar import grass_lidar
   from arsf_dem import dem_common_functions
except ImportError as err:
   print("Could not import ARSF DEM library.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

#: Debug mode
DEBUG = True

def load_files_to_grass(in_lidar_files,
                        in_projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                        resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                        lidar_format='LAS',
                        raster_type='DSM',
                        drop_noise=True,
                        load_as_vector=False):

   drop_class = None
   keep_class = None
   las2txt_flags = None
   returns_to_keep = 'all'

   # Set options for raster type to be exported
   # DSM - first returns (top of canopy)
   if raster_type.upper() == 'DSM':
      val_field = 'z'
      las2txt_flags = '-first_only'
      returns_to_keep = 'first'
   # DSM - last returns (ground surface)
   elif raster_type.upper() == 'DTM':
      val_field = 'z'
      las2txt_flags = '-last_only'
      returns_to_keep = 'last'
   # DEM - general term (all returns)
   elif raster_type.upper() == 'DEM':
      val_field = 'z'
      drop_class = 7
      returns_to_keep = 'all'
   # UNFILTEREDDEM - keep all values
   elif raster_type.upper() == 'UNFILTEREDDEM':
      val_field = 'z'
   elif raster_type.upper() == 'INTENSITY':
      val_field = 'intensity'
   else:
      raise Exception('raster_type "{}" was not recognised'.format(raster_type))

   if drop_noise:
      drop_class = 7

   # Expect a list of files, if passed in string
   # create list.
   if isinstance(in_lidar_files,str):
      in_lidar_files = [in_lidar_files]

   # If a directory, look for files
   if os.path.isdir(in_lidar_files[0]):
      if lidar_format.upper() == 'LAS':
         in_lidar_files_list = glob.glob(
                           os.path.join(in_lidar_files[0],'*[Ll][Aa][Ss]'))
         in_lidar_files_list.extend(glob.glob(
                           os.path.join(in_lidar_files[0],'*[Ll][Aa][Zz]')))

      # If ASCII format or not las files found check for txt files
      if lidar_format.upper() == 'ASCII' or len(in_lidar_files_list) == 0:
         in_lidar_files_list = glob.glob(
                           os.path.join(in_lidar_files[0],'*txt'))
         if len(in_lidar_files_list) != 0:
            lidar_format = 'ASCII'

   # Check if wild character has been passed in which wasn't expanded (e.g., on windows)
   # or no matching files were found (which will raise exception later).
   elif in_lidar_files[0].find('*') > -1:
      in_lidar_files_list = glob.glob(in_lidar_files[0])
   else:
      in_lidar_files_list = in_lidar_files
      if os.path.splitext(in_lidar_files_list[0])[-1].lower() != '.las' \
        and os.path.splitext(in_lidar_files_list[0])[-1].lower() != '.laz':
         lidar_format = 'ASCII'

   if len(in_lidar_files_list) == 0:
      raise Exception('No lidar files were passed in or found from path provided')

   # Create variable for GRASS path
   grassdb_path = None
   grass_dataset_names = []

   # Create raster from point cloud files
   totlines = len(in_lidar_files_list)

   for linenum,in_lidar_file in enumerate(in_lidar_files_list):
      dem_common_functions.PrintTermWidth('Loading "{0}" to GRASS ({1}/{2})'.format(os.path.split(in_lidar_file)[-1],linenum+1, totlines))
      # Check file exists
      if not os.path.isfile(in_lidar_file):
         raise Exception('Could not open "{}"'.format(in_lidar_file))

      if lidar_format.upper() == 'LAS' and not load_as_vector:
         out_grass_name, grassdb_path = \
           grass_lidar.las_to_raster(in_lidar_file,
                                     out_raster=None,
                                     remove_grassdb=False,
                                     grassdb_path=grassdb_path,
                                     val_field=val_field,
                                     drop_class=drop_class,
                                     keep_class=keep_class,
                                     las2txt_flags=las2txt_flags,
                                     projection=in_projection,
                                     bin_size=resolution,
                                     out_raster_type=raster_type)
      elif lidar_format.upper() == 'LAS' and load_as_vector:
         out_grass_name, grassdb_path = \
           grass_lidar.las_to_vector(in_lidar_file,
                                     grassdb_path=grassdb_path,
                                     drop_class=drop_class,
                                     keep_class=keep_class,
                                     las2txt_flags=las2txt_flags,
                                     projection=in_projection)
      elif lidar_format.upper() == 'ASCII' and not load_as_vector:
         out_grass_name, grassdb_path = \
            grass_lidar.ascii_to_raster(in_lidar_file,
                                        out_raster=None,
                                        remove_grassdb=False,
                                        grassdb_path=grassdb_path,
                                        val_field=val_field,
                                        drop_class=drop_class,
                                        keep_class=keep_class,
                                        returns=returns_to_keep,
                                        projection=in_projection,
                                        bin_size=resolution,
                                        out_raster_type=raster_type)
      elif lidar_format.upper() == 'ASCII' and load_as_vector:
         out_grass_name, grassdb_path = \
            grass_lidar.ascii_to_vector(in_lidar_file,
                                        grassdb_path=grassdb_path,
                                        drop_class=drop_class,
                                        keep_class=keep_class,
                                        returns=returns_to_keep,
                                        projection=in_projection)

      grass_dataset_names.append(out_grass_name)

   print('Loaded the following files:')
   for grass_dataset in grass_dataset_names:
      print(' {}'.format(grass_dataset))
   print('To GRASS database: {0}/{1}/PERMANENT'.format(grassdb_path,
                                                       in_projection))

if __name__ == '__main__':
   description_str = '''Load LiDAR files into GRASS for further processing.

For LAS files converts to ASCII first using las2txt.

Points flagged as noise (class 7) are dropped before being added.

Performs the following steps:

1. Sets up GRASS database in the required projection
2. Loads converted files using r.in.xyz

Then returns the path of the database which can be opened using:

   grass PATH_TO_DATABASE

For examples of futher processing see:

https://grasswiki.osgeo.org/wiki/LIDAR

Created by ARSF-DAN at Plymouth Marine Laboratory (PML)
and is made available under the terms of the GPLv3 license.

'''

   try:
      parser = argparse.ArgumentParser(description=description_str,formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument("lidarfiles", nargs='+',type=str,
                          help="List or directory containing input LiDAR files")
      parser.add_argument('-r', '--resolution',
                          metavar='Resolution',
                          help='Resolution for output DEM (default={})'.format(dem_common.DEFAULT_LIDAR_RES_METRES),
                          default=dem_common.DEFAULT_LIDAR_RES_METRES,
                          required=False)
      parser.add_argument('--projection',
                          metavar='In Projection',
                          help='Input projection (e.g., UTM30N)',
                          default=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                          required=False)
      parser.add_argument('-t', '--rastertype',
                          metavar='Output raster type',
                          help='Raster type - determines the lidar returns to'
                               ' load into GRASS. For all select DEM (default),'
                               ' for first only select DSM,'
                               ' for last only select DTM.',
                          default='DEM',
                          required=False)
      parser.add_argument('--vector',
                          action='store_true',
                          default=False,
                          help='Load points as vector.'
                               ' WARNING - this can require a lot of memory'
                               ' ensure sufficient RAM is available before '
                               ' using this options',
                          required=False)
      args=parser.parse_args()

      load_files_to_grass(args.lidarfiles,
                          in_projection=args.projection,
                          resolution=args.resolution,
                          lidar_format='LAS',
                          raster_type=args.rastertype,
                          load_as_vector=args.vector,
                          drop_noise=True)

   except KeyboardInterrupt:
      sys.exit(2)
   except Exception as err:
      if DEBUG:
         raise
      dem_common_functions.ERROR(err)
      sys.exit(1)
