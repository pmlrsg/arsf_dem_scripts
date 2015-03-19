#!/usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created On: 06/10/2014

"""
A collection of utilities for working with LiDAR data.
"""
import tempfile
import os
from . import lidar_utilities
from . import grass_lidar
from . import ascii_lidar
from . import lastools_lidar
from . import spdlib_lidar
from . import laspy_lidar
from .. import dem_common
from .. import dem_utilities
from .. import dem_common_functions
from .. import grass_library

def _las_to_dem(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               demtype='DSM',
               method='GRASS'):
   """
   Helper function to generate a Digital Surface Model (DSM) or
   Digital Terrain Model (DTM) from a LAS file.

   Called by las_to_dtm or las_to_dsm.

   Utility function to call las_to_dtm / las_to_dsm from grass_lidar, lastools_lidar or
   spdlib_lidar

   When using GRASS the DTM will be created using only last returns. For SPDLib and
   LAStools methods, the data will be filtered to try and remove vegetation and buildings.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output DEM) in GRASS format (e.g., UTM30N)
   * method - GRASS, SPDLib or LAStools

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_dtm('in_las_file.las','out_dsm.dem')

   """

   # Get output type from extension (if not specified)
   out_raster_format = dem_utilities.get_gdal_type_from_path(out_raster)

   if method.upper() == 'GRASS':
      # Set projection to default if not provided
      grass_projection = projection
      if grass_projection is None:
         grass_projection = dem_common.DEFAULT_LIDAR_PROJECTION_GRASS

      if demtype.upper() == 'DSM':
         grass_lidar.las_to_dsm(in_las, out_raster,
                              bin_size=resolution,
                              projection=grass_projection,
                              out_raster_format=out_raster_format)
      elif demtype.upper() == 'DTM':
         grass_lidar.las_to_dtm(in_las, out_raster,
                              bin_size=resolution,
                              projection=grass_projection,
                              out_raster_format=out_raster_format)
      else:
         raise Exception('DEM Type not recognised - options are DSM or DTM')

   elif method.upper() == 'SPDLIB':
      # Create WKT file with projection
      if projection is not None:
         wktfile_handler, wkt_tmp = tempfile.mkstemp(suffix='.wkt', dir=dem_common.TEMP_PATH)
         grass_library.grass_projection_to_wkt(projection, wkt_tmp)
      else:
         wkt_tmp = None

      if demtype.upper() == 'DSM':
         spdlib_lidar.las_to_dsm(in_las, out_raster,
                              bin_size=resolution,
                              wkt=wkt_tmp,
                              out_raster_format=out_raster_format)
      elif demtype.upper() == 'DTM':
         spdlib_lidar.las_to_dtm(in_las, out_raster,
                              bin_size=resolution,
                              wkt=wkt_tmp,
                              out_raster_format=out_raster_format)
      else:
         raise Exception('DEM Type not recognised - options are DSM or DTM')

      if projection is not None:
         # Close and remove temp WKT file created
         os.close(wktfile_handler)
         os.remove(wkt_tmp)

   elif method.upper() == 'LASTOOLS':
      # Set resolution flag
      lastools_flags = ['-step {}'.format(float(resolution))]

      # Get projection
      try:
         if projection is not None:
            lastools_proj = lastools_lidar.grass_proj_to_lastools_flag(projection)
            lastools_flags.extend([lastools_proj])
      except Exception as err:
         dem_common_functions.WARNING('Could not convert projection to LAStools flags. {}. Will try to get projection from LAS file'.format(err))

      if demtype.upper() == 'DSM':
         lastools_lidar.las_to_dsm(in_las, out_raster, flags=lastools_flags)
      elif demtype.upper() == 'DTM':
         lastools_lidar.las_to_dtm(in_las, out_raster, flags=lastools_flags)
      else:
         raise Exception('DEM Type not recognised - options are DSM or DTM')
   else:
      raise Exception('Invalid method "{}", expected GRASS, SPDLIB or LASTOOLS'.format(method))

def las_to_dsm(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               method='GRASS'):
   """
   Helper function to generate a Digital Surface Model (DSM) from a LAS file.

   Utility function to call las_to_dsm from grass_lidar, lastools_lidar or
   spdlib_lidar

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output DEM) in GRASS format (e.g., UTM30N)
   * method - GRASS, SPDLib or LAStools

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_dsm('in_las_file.las','out_dsm.dem')

   """

   _las_to_dem(in_las, out_raster,
               resolution=resolution,
               projection=projection,
               demtype='DSM',
               method=method)

def las_to_dtm(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
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
   * projection - Projection of input LAS files (and output DEM) in GRASS format (e.g., UTM30N)
   * method - GRASS, SPDLib or LAStools

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_dtm('in_las_file.las','out_dsm.dem')

   """

   _las_to_dem(in_las, out_raster,
               resolution=resolution,
               projection=projection,
               demtype='DTM',
               method=method)
