#!/usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created On: 06/10/2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
A collection of utilities for working with LiDAR data.

Two high level functions las_to_dsm and las_dtm are included which are used
to create a Digital Surface Model (DSM) and Digital Terrain Model (DTM) from
LAS files.

You can use these Python fuctions to look through all LAS files in an directory
and create a DSM / DTM for each.

For example::

   import os
   import glob
   from arsf_dem import dem_lidar

   # Search current directory for all files ending matching '*.LAS'
   in_las_list = glob.glob('*.[Ll][Aa][Ss]')

   # Iterate through list of files found to create a raster for each line
   for in_las in in_las_list:
      # Set name of output DEM as the same as LAS file
      # but with '_dsm.tif' suffix
      out_dem_basename = os.path.splitext(os.path.split(in_las)[-1])[0]
      out_dsm = os.path.join(out_dir, out_dem_basename + '_dsm.tif')
      out_dtm = os.path.join(out_dir, out_dem_basename + '_dtm.tif')

      # Run function to create DSM
      dem_lidar.las_to_dsm(in_las,out_dsm, method='GRASS')

      # Run function to create DTM
      dem_lidar.las_to_dtm(in_las,out_dtm, method='GRASS')

"""
import tempfile
import os
from . import lidar_utilities
from . import grass_lidar
from . import ascii_lidar
from . import lastools_lidar
from . import spdlib_lidar
from . import fusion_lidar
from . import points2grid_lidar
from . import laspy_lidar
from .. import dem_common
from .. import dem_utilities
from .. import dem_common_functions
from .. import grass_library

#: Methods which can create a DEM from LAS files
LAS_TO_DEM_METHODS = ['GRASS','SPDLib','LAStools','FUSION','points2grid']
#: Methods which can create an intensity image from LAS files
LAS_TO_INTENSITY_METHODS = ['GRASS', 'LAStools']
#: Methods which can't filter out noisy points in LAS files and require these to be removed first
METHODS_REQUIRE_LAS_NOISE_REMOVAL = ['SPDLib']

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

   * in_las - Input LAS file or list of LAS files
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output DEM) as GRASS location format (e.g., UTM30N).
   * method - GRASS, SPDLib, LAStools, FUSION or points2grid

   Returns:

   None

   """
   # Check output path exists and can be written to
   # (will raise exception if it doesn't)
   dem_common_functions.CheckPathExistsAndIsWritable(os.path.split(
                                          os.path.abspath(out_raster))[0])

   tmp_las_handler, tmp_las_file = tempfile.mkstemp(suffix='.las')

   # If a list is passed in merge to a single LAS file
   if isinstance(in_las, list):
      # Check if there is only one item in the list (will get this from
      # argparse).
      if len(in_las) == 1:
         if not os.path.isfile(in_las[0]):
            raise Exception('The file "{}" does not exist'.format(in_las[0]))
         elif method.upper() in [s.upper() for s in METHODS_REQUIRE_LAS_NOISE_REMOVAL]:
            # If method can't filter LAS files do this first
            # use merge_las function.
            print('Creating LAS file with noise points removed.'
                  ' Required for {}'.format(method))
            lastools_lidar.merge_las(in_las, tmp_las_file, drop_class=7)
            in_las_merged = tmp_las_file
         else:
            in_las_merged = in_las[0]
      else:
         print('Multiple LAS files have been passed in - merging')
         lastools_lidar.merge_las(in_las, tmp_las_file, drop_class=7)
         in_las_merged = tmp_las_file
   else:
      in_las_merged = in_las

   # Get output type from extension (if not specified)
   out_raster_format = dem_utilities.get_gdal_type_from_path(out_raster)

   if method.upper() == 'GRASS':
      # Set projection to default if not provided
      grass_location = projection
      if grass_location is None:
         grass_location = dem_common.DEFAULT_LIDAR_PROJECTION_GRASS

      if demtype.upper() == 'DSM':
         grass_lidar.las_to_dsm(in_las_merged, out_raster,
                                bin_size=resolution,
                                projection=grass_location)
      elif demtype.upper() == 'DTM':
         grass_lidar.las_to_dtm(in_las_merged, out_raster,
                                bin_size=resolution,
                                projection=grass_location)
      elif demtype.upper() == 'INTENSITY':
         grass_lidar.las_to_intensity(in_las_merged, out_raster,
                                      bin_size=resolution,
                                      projection=grass_location)
      else:
         raise Exception('DEM Type not recognised - options are DSM, DTM or Intensity')

   elif method.upper() == 'SPDLIB':
      # Create WKT file with projection
      if projection is not None:
         wktfile_handler, wkt_tmp = tempfile.mkstemp(suffix='.wkt', dir=dem_common.TEMP_PATH)
         grass_library.grass_location_to_wkt(projection, wkt_tmp)
      else:
         wkt_tmp = None

      if demtype.upper() == 'DSM':
         spdlib_lidar.las_to_dsm(in_las_merged, out_raster,
                              bin_size=resolution,
                              wkt=wkt_tmp,
                              out_raster_format=out_raster_format)
      elif demtype.upper() == 'DTM':
         spdlib_lidar.las_to_dtm(in_las_merged, out_raster,
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
         lastools_lidar.las_to_dsm(in_las_merged, out_raster, flags=lastools_flags)
      elif demtype.upper() == 'DTM':
         lastools_lidar.las_to_dtm(in_las_merged, out_raster, flags=lastools_flags)
      elif demtype.upper() == 'INTENSITY':
         lastools_lidar.las_to_intensity(in_las_merged, out_raster, flags=lastools_flags)
      else:
         raise Exception('DEM Type not recognised - options are DSM, DTM or Intensity')

   elif method.upper() == 'FUSION':
      if demtype.upper() == 'DSM':
         fusion_lidar.las_to_dsm(in_las_merged, out_raster, resolution=resolution)
      elif demtype.upper() == 'DTM':
         fusion_lidar.las_to_dtm(in_las_merged, out_raster, resolution=resolution)
      else:
         raise Exception('DEM Type not recognised - options are DSM or DTM')

   elif method.upper() == 'POINTS2GRID':
      # Create WKT file with projection
      if projection is not None:
         wktfile_handler, wkt_tmp = tempfile.mkstemp(suffix='.wkt', dir=dem_common.TEMP_PATH)
         grass_library.grass_location_to_wkt(projection, wkt_tmp)
      else:
         wkt_tmp = None

      # Create surface. Use IDW interpolation
      if demtype.upper() == 'DSM':
         points2grid_lidar.las_to_dsm(in_las_merged, out_raster,
                              resolution=resolution,
                              projection=wkt_tmp,
                              grid_method='idw',
                              fill_window_size=7)
      elif demtype.upper() == 'DTM':
         points2grid_lidar.las_to_dtm(in_las_merged, out_raster,
                              resolution=resolution,
                              projection=wkt_tmp,
                              grid_method='idw',
                              fill_window_size=7)
      else:
         raise Exception('DEM Type not recognised - options are DSM or DTM')

      if projection is not None:
         # Close and remove temp WKT file created
         os.close(wktfile_handler)
         os.remove(wkt_tmp)
   else:
      raise Exception('Invalid method "{}", expected GRASS, SPDLIB or LASTOOLS'.format(method))

   # If an ENVI file remove .aux.xml file GDAL creates. This function will copy
   # any relevant parameters (e.g., no data value) to the .hdr file
   if out_raster_format == 'ENVI':
      dem_utilities.remove_gdal_aux_file(out_raster)

   os.close(tmp_las_handler)
   os.remove(tmp_las_file)

def las_to_dsm(in_las,out_raster,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               method='GRASS'):
   """
   Helper function to generate a Digital Surface Model (DSM) from a LAS file.

   Utility function to call las_to_dsm from grass_lidar, lastools_lidar or
   spdlib_lidar

   Arguments:

   * in_las - Input LAS file or list of LAS files
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output DEM) as GRASS location format (e.g., UTM30N).
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

   * in_las - Input LAS file or list of LAS files
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output DEM) as GRASS location format (e.g., UTM30N).
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

def las_to_intensity(in_las,out_raster,
                     resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                     projection=None,
                     method='GRASS'):
   """
   Helper function to generate an Intensity image from a LAS file.

   Utility function to call las_to_intensity from grass_lidar or lastools_lidar

   Arguments:

   * in_las - Input LAS file or list of LAS files
   * out_raster - Output raster
   * resolution - Resolution to use for output raster.
   * projection - Projection of input LAS files (and output raster) as GRASS location format (e.g., UTM30N).
   * method - GRASS or LAStools

   Returns:

   None

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.las_to_intensity('in_las_file.las','out_intensity.tif')

   """

   _las_to_dem(in_las, out_raster,
               resolution=resolution,
               projection=projection,
               demtype='INTENSITY',
               method=method)


