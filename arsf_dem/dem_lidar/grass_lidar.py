#!/usr/bin/env python
#
# grass_lidar
#
# Author: Dan Clewley (dac@pml.ac.uk)
# Created on: 05 November 2014
# Licensing: Uses GRASS GIS Python scripting library, subject to GNU GPL.

"""
Functions for working with LiDAR data using GRASS

Available Functions:

* las_to_dsm - Create DSM from LAS file.
* las_to_dtm - Create last-returns DTM from LAS file.
* las_to_intensity - Create intensity image from LAS file.
* las_to_raster - Convert lidar data in LAS format to raster.
* ascii_to_raster - Convert lidar data in ASCII format to raster.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import shutil
import tempfile
# Import common files
from .. import dem_common
from .. import dem_utilities
from . import laspy_lidar
from . import lastools_lidar
from . import ascii_lidar
from .. import grass_library
from .. import dem_common_functions

# Import GRASS
sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)
try:
   import grass.script as grass
except ImportError as err:
   print("Could not import grass library. Try setting 'GRASS_PYTHON_LIB_PATH' environmental variable.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

def ascii_to_raster(in_ascii,out_raster=None,
                     remove_grassdb=True,
                     grassdb_path=None,
                     xyz_bounds=None,
                     val_field='z',
                     drop_class=None,
                     keep_class=None,
                     returns='all',
                     projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
                     out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                     out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE):
   """
   Create raster from lidar data in ASCII format using GRASS.

   The pixel values are the mean 'val_field' of all points within a pixel.
   Default is to use the elevation and create a DSM.
   To create a DTM classify ground returns in LAS file and only export these
   to the ASCII file.

   Intensity images can be created by setting the value field to 'intensity'

   If an existing grass db is provided will add DSM to this,
   else will create one.

   Default is to leave raster in GRASS database rather than exporting.

   Arguments:

   * in_ascii - Input ASCII file.
   * out_raster - Output raster (set to None to leave in GRASS database.
   * remove_grassdb - Remove GRASS database after processing is complete.
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
   * val_field - Value field to use for raster, default is 'z' (elevation).
   * drop_class - Class to drop from input lidar file (default = None, assume classes are dropped prior to input).
   * keep_class - Class to keep from input lidar file (default = None).
   * returns - Returns to keep from input lidar file. Options are 'all' (Default), 'first' and 'last'.
   * projection - Projection of lidar data (e.g., UKBNG).
   * bin_size - Resolution to use for output raster.
   * out_raster_format - GDAL format name for output raster (e.g., ENVI).
   * out_raster_type - GDAL datatype for output raster (e.g., Float32).

   Returns:

   * out_raster path / out_raster name in GRASS database.
   * path to GRASS database / None.

   """

   try:
      dem_common.LIDAR_ASCII_ORDER[val_field]
   except KeyError:
      raise Exception('Could not find field "{}"'.format(val_field))

   if out_raster is not None:
      out_raster_name = os.path.basename(out_raster).replace("-","_")
   else:
      out_raster_name = os.path.basename(in_ascii).replace("-","_")
      out_raster_name = os.path.splitext(out_raster_name)[0] + '.dem'

   # Check if all returns are needed or only first / last
   first_only = False
   last_only = False

   if returns.lower() == 'first':
      first_only = True
   elif returns.lower() == 'last':
      last_only = True

   # Create copy of ASCII file, if needed
   if (drop_class is not None) or (keep_class is not None) or first_only or last_only:
      tmp_ascii_fh, in_ascii_drop = tempfile.mkstemp(suffix='.txt', prefix='lidar_',dir=dem_common.TEMP_PATH)
      grass_library.removeASCIIClass(in_ascii, in_ascii_drop,drop_class=drop_class, first_only=first_only, last_only=last_only)
   else:
      in_ascii_drop = in_ascii

   # Get bounds from ASCII (if not passed in)
   bounding_box = {}
   if xyz_bounds is None or xyz_bounds[0][0] is None:
      xyz_bounds = ascii_lidar.get_ascii_bounds(in_ascii_drop)

   bounding_box['w'] = xyz_bounds[0][0]
   bounding_box['e'] = xyz_bounds[0][1]
   bounding_box['s'] = xyz_bounds[1][0]
   bounding_box['n'] = xyz_bounds[1][1]

   # If GRASS database has not been passed in
   # need to create one and initialise
   if grassdb_path is None:
      grassdb_path = grass_library.grassDBsetup()
      grass_library.setLocation(projection)
   else:
      location = projection
      mapset = 'PERMANENT'
      grass.setup.init(dem_common.GRASS_LIB_PATH,
                  grassdb_path,
                  location,
                  mapset)

   # Set extent
   grass_library.SetRegion(bounds=bounding_box,res=bin_size)

   # Import lidar into GRASS and create DEM
   print('Importing {} to GRASS'.format(in_ascii_drop))
   grass.run_command('r.in.xyz',
                      input=in_ascii_drop,
                      output=out_raster_name,
                      method='mean',
                      fs=' ',
                      x=dem_common.LIDAR_ASCII_ORDER['x'],
                      y=dem_common.LIDAR_ASCII_ORDER['y'],
                      z=dem_common.LIDAR_ASCII_ORDER[val_field],
                      overwrite = True)

   if not grass_library.checkFileExists(out_raster_name):
      raise Exception('Could not create output raster')

   if out_raster is not None:
      print('Exporting')
      grass.run_command('r.out.gdal',
                     format=out_raster_format,
                     type=out_raster_type,
                     input=out_raster_name,
                     output=out_raster,
                     nodata=dem_common.NODATA_VALUE,
                     overwrite=True)

      dem_utilities.remove_gdal_aux_file(out_raster)

   if (drop_class is not None) or (keep_class is not None) or first_only or last_only:
      os.close(tmp_ascii_fh)
      os.remove(in_ascii_drop)

   # Remove GRASS database if requested.
   if remove_grassdb:
      shutil.rmtree(grassdb_path)
      return out_raster, None
   else:
      return out_raster_name, grassdb_path

def las_to_raster(in_las,out_raster=None,
                     remove_grassdb=True,
                     grassdb_path=None,
                     val_field='z',
                     drop_class=7,
                     keep_class=None,
                     las2txt_flags=None,
                     projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
                     out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                     out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE):
   """
   Create a raster from lidar data in LAS format using GRASS.

   The pixel values are the mean 'val_field' of all points within a pixel.
   Default is to use the elevation ('z') and create a DSM.
   To create a DTM classify ground returns in LAS file and select non-ground
   classes to be dropped using 'drop_class'.

   Intensity images can be created by setting the value field to 'intensity'

   Currently a wrapper for ascii_to_raster which converts LAS to ASCII before
   running.

   In GRASS 7 native LAS support should be possible.

   If an existing grass db is provided will add raster to this,
   else will create one.

   Default is to leave raster in GRASS database rather than exporting.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster (set to None to leave in GRASS database.
   * remove_grassdb - Remove GRASS database after processing is complete.
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
   * val_field - Value field to use for raster, default is 'z' (elevation).
   * drop_class - Class / list of classes to drop when converting to ASCII (default = 7).
   * keep_class - Class / list of classes to keep when converting to ASCII.
   * las2txt_flags - Additional flags passed to las2txt when converting LAS to ASCII.
   * projection - Projection of lidar data (e.g., UKBNG).
   * bin_size - Resolution to use for output raster.
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * out_raster_type - GDAL datatype for output raster (e.g., Float32)

   Returns:

   * out_raster path / out_raster name in GRASS database
   * path to GRASS database / None"

   """

   tmp_ascii_fh, ascii_file_tmp = tempfile.mkstemp(suffix='.txt', prefix='lidar_',dir=dem_common.TEMP_PATH)

   if out_raster is not None:
      out_raster_name = os.path.basename(out_raster).replace("-","_")
   else:
      out_raster_name = os.path.basename(in_las).replace("-","_")
      out_raster_name = os.path.splitext(out_raster_name)[0] + '.dem'

   # Try to get bounds of LAS file if laspy library is available
   xyz_bounds = None
   if laspy_lidar.HAVE_LASPY:
      try:
         xyz_bounds = laspy_lidar.get_las_bounds(in_las,
                                                 from_header=True)
      except Exception as err:
         dem_common_functions.WARNING('Could not get bounds from LAS file ({}). Will try from ASCII'.format(err))

   # Convert LAS to ASCII
   print('Converting LAS file to ASCII')

   lastools_lidar.convert_las_to_ascii(in_las,ascii_file_tmp,
                                       drop_class=drop_class,
                                       keep_class=keep_class,
                                       flags=las2txt_flags)

   # Create raster from ASCII
   try:
      out_raster_name, grassdb_path = ascii_to_raster(ascii_file_tmp,out_raster,
                                       remove_grassdb=remove_grassdb,
                                       grassdb_path=grassdb_path,
                                       xyz_bounds=xyz_bounds,
                                       val_field=val_field,
                                       projection=projection,
                                       bin_size=bin_size,
                                       out_raster_format=out_raster_format,
                                       out_raster_type=out_raster_type)

   except Exception as err:
      os.close(tmp_ascii_fh)
      os.remove(ascii_file_tmp)
      raise

   # Remove ASCII file created
   os.close(tmp_ascii_fh)
   os.remove(ascii_file_tmp)

   return out_raster_name, grassdb_path

def las_to_dsm(in_las,out_raster=None,
                     remove_grassdb=True,
                     grassdb_path=None,
                     projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
                     out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                     out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE):
   """
   Helper function to generate a Digital Surface Model (DSM) from a LAS file using
   GRASS.

   The DSM is created using only first returns.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster (set to None to leave in GRASS database).
   * remove_grassdb - Remove GRASS database after processing is complete.
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
   * projection - Projection of lidar data (e.g., UKBNG).
   * bin_size - Resolution to use for output raster.
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * out_raster_type - GDAL datatype for output raster (e.g., Float32)

   Returns:

   * out_raster path / out_raster name in GRASS database
   * path to GRASS database / None"

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.grass_lidar.las_to_dsm('in_las_file.las','out_dsm.dem')


   """

   out_raster_name, grassdb_path = las_to_raster(in_las,out_raster=out_raster,
                     remove_grassdb=remove_grassdb,
                     grassdb_path=grassdb_path,
                     val_field='z',
                     drop_class=7,
                     las2txt_flags='-first_only',
                     projection=projection,
                     bin_size=bin_size,
                     out_raster_format=out_raster_format,
                     out_raster_type=out_raster_type)

   return out_raster_name, grassdb_path

def las_to_dtm(in_las,out_raster=None,
                     remove_grassdb=True,
                     grassdb_path=None,
                     projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
                     out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                     out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE):
   """
   Helper function to generate a Digital Terrain Model (DTM) from a LAS file using
   GRASS.

   The DTM is created using only last returns, therefore is not a true DTM.

   To improve the quality of the DTM classification of ground returns is required.
   If a ground classified LAS file is available a better DTM can be created using
   'las_to_raster' and setting 'keep_class=2'.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster (set to None to leave in GRASS database).
   * remove_grassdb - Remove GRASS database after processing is complete.
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
   * projection - Projection of lidar data (e.g., UKBNG).
   * bin_size - Resolution to use for output raster.
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * out_raster_type - GDAL datatype for output raster (e.g., Float32)

   Returns:

   * out_raster path / out_raster name in GRASS database
   * path to GRASS database / None"

   Example::

      from arsf_dem import dem_lidar
      dem_lidar.grass_lidar.las_to_dtm('in_las_file.las','out_dtm.dem')

    """

   out_raster_name, grassdb_path = las_to_raster(in_las,out_raster=out_raster,
                     remove_grassdb=remove_grassdb,
                     grassdb_path=grassdb_path,
                     val_field='z',
                     drop_class=7,
                     las2txt_flags='-last_only',
                     projection=projection,
                     bin_size=bin_size,
                     out_raster_format=out_raster_format,
                     out_raster_type=out_raster_type)

   return out_raster_name, grassdb_path

def las_to_intensity(in_las,out_raster=None,
                     remove_grassdb=True,
                     grassdb_path=None,
                     projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
                     out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                     out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE):
   """
   Helper function to generate an intensity image from a LAS file using
   GRASS.

   Arguments:

   * in_las - Input LAS file.
   * out_raster - Output raster (set to None to leave in GRASS database).
   * remove_grassdb - Remove GRASS database after processing is complete.
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
   * projection - Projection of lidar data (e.g., UKBNG).
   * bin_size - Resolution to use for output raster.
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * out_raster_type - GDAL datatype for output raster (e.g., Float32)

   Returns:

   * out_raster path / out_raster name in GRASS database
   * path to GRASS database / None"

   """

   # If JPEG output call export screenshot after to scale image
   if out_raster_format == 'JPEG' and out_raster is not None:
      out_raster_name, grassdb_path = las_to_raster(in_las,out_raster=None,
                        remove_grassdb=False,
                        grassdb_path=grassdb_path,
                        val_field='intensity',
                        drop_class=7,
                        las2txt_flags='-last_only',
                        projection=projection,
                        bin_size=bin_size,
                        out_raster_format=out_raster_format,
                        out_raster_type=out_raster_type)


      out_raster_type, grassdb_path = dem_utilities.export_screenshot(out_raster_name,
                     out_raster,
                     import_to_grass=False,
                     projection=projection,
                     grassdb_path=grassdb_path,
                     remove_grassdb=remove_grassdb)

   else:
      out_raster_name, grassdb_path = las_to_raster(in_las,out_raster=out_raster,
                        remove_grassdb=remove_grassdb,
                        grassdb_path=grassdb_path,
                        val_field='intensity',
                        drop_class=7,
                        las2txt_flags='-last_only',
                        projection=projection,
                        bin_size=bin_size,
                        out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
                        out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE)

   return out_raster_name, grassdb_path
