#!/usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created On: 06/10/2014

"""
A collection of utilities for working with LiDAR data.
"""
from . import lidar_utilities
from . import grass_lidar
from . import ascii_lidar
from . import lastools_lidar
from . import spdlib_lidar
from . import laspy_lidar
from .. import dem_common
from .. import dem_utilities

def las_to_dsm(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               method='GRASS'):
   """
   Helper function to generate a Digital Surface Model (DSM) from a LAS file.

   Utility function to call las_to_dsm from grass_lidar, lastools_lidar or
   spdlib_lidar

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * method - GRASS, SPDLIB or LASTOOLS

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_dsm('in_las_file.las','out_dsm.dem')

   """

   # Get output type from extension (if not specified)
   out_raster_format = dem_utilities.get_gdal_type_from_path(out_raster)

   if method.upper() == 'GRASS':
      grass_lidar.las_to_dsm(in_las, out_raster,
                              bin_size=resolution,
                              out_raster_format=out_raster_format)
   elif method.upper() == 'SPDLIB':
      spdlib_lidar.las_to_dsm(in_las, out_raster,
                              bin_size=resolution,
                              out_raster_format=out_raster_format)
   elif method.upper() == 'LASTOOLS':
      lastools_lidar.las_to_dsm(in_las, out_raster)
   else:
      raise Exception('Invalid method "{}", expected GRASS, SPDLIB or LASTOOLS'.format(method))

def las_to_dtm(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               method='GRASS'):
   """
   Helper function to generate a Digital Terrain Model (DTM) from a LAS file.

   Utility function to call las_to_dtm from grass_lidar, lastools_lidar or
   spdlib_lidar

   When using GRASS the DTM will be created using only last returns. For SPDLib and
   LAStools methods, the data will be filtered to try and remove vegetation and buildings.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * method - GRASS, SPDLIB or LASTOOLS

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_dtm('in_las_file.las','out_dsm.dem')

   """

   # Get output type from extension (if not specified)
   out_raster_format = dem_utilities.get_gdal_type_from_path(out_raster)

   if method.upper() == 'GRASS':
      grass_lidar.las_to_dtm(in_las, out_raster,
                              bin_size=resolution,
                              out_raster_format=out_raster_format)
   elif method.upper() == 'SPDLIB':
      spdlib_lidar.las_to_dtm(in_las, out_raster,
                              bin_size=resolution,
                              out_raster_format=out_raster_format)
   elif method.upper() == 'LASTOOLS':
      lastools_lidar.las_to_dtm(in_las, out_raster)
   else:
      raise Exception('Invalid method "{}", expected GRASS, SPDLIB or LASTOOLS'.format(method))
