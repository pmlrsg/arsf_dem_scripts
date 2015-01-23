#Author: Dan Clewley (dac)
#Created on: 05 November 2014
#Licensing: Uses SPDLib, subject to GNU GPL.
"""
Functions for working with LiDAR data using SPDLib (http://spdlib.org/)

Requires SPDLib to be installed.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import tempfile
# Import common files
from .. import dem_common
from .. import dem_common_functions

def checkSPDLib():
   """Check if SPDLib is installed."""

   try:
      dem_common_functions.CallSubprocessOn([os.path.join(dem_common.SPDLIB_BIN_PATH,'spdtranslate')],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False

def convert_las_to_spd(in_las,out_spd,wkt=None,
                  bin_size=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Convert LAS file to spatially indexed SPD file by calling
   spdtranslate.

   Indexes using last return
   Uses temp files for conversion process.

   Arguments:

   * in_las - Input LAS file
   * out_spd - Output SPD file
   * wkt - WKT file defining projection (will obtain from LAS if not provided)
   * bin_size - Bin size for spatial indexing

   Returns:

   * None

   """

   if not checkSPDLib():
      raise Exception('Could not find SPDLib')

   temp_dir = tempfile.mkdtemp(dir=dem_common.TEMP_PATH)
   spdtmppath = os.path.join(temp_dir, 'spd_tmp')

   spdCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdtranslate'),
               '--if','LAS','--of','SPD',
               '-b',str(bin_size),
               '-x','LAST_RETURN',
               '--temppath',spdtmppath,
               '-i',in_las,'-o',out_spd]
   if wkt is not None:
      spdCMD = spdCMD + ['--input_proj',wkt, '--output_proj', wkt]

   dem_common_functions.CallSubprocessOn(spdCMD)

   # Remove temp files
   shutil.rmtree(temp_dir)

def classify_ground_spd(in_spd,out_spd,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Classify ground returns in an SPD file using a
   Progressive Morphology filter.

   Calls the spdpmfgrd tool.

   Arguments:

   * in_spd - Input SPD File
   * out_spd - Output SPD file
   * bin_size - Bin size for spatial indexing

   Returns:

   * None

    """
   if not checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   pmfCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdpmfgrd'),
            '-b',str(bin_size),
            '-r','50',
            '--overlap','10',
            '--maxfilter','14',
            '-i',in_spd,'-o',out_spd]

   dem_common_functions.CallSubprocessOn(pmfCMD)

def spd_to_dsm(in_spd, out_dsm, interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Create a Digital Surface Model (DSM) from an SPD file

   Calls the spdinterp tool.

   Arguments:

   * in_spd - Input SPD File
   * out_dsm - Output DSM file
   * interpolation - Interpolation method
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * bin_size - Bin size for spatial indexing

   Returns:

   * None

   """
   if not checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   dsmCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdinterp'),
       '--dsm','--topo',
       '--in',interpolation,
       '-f',out_raster_format,
       '-b',str(bin_size),
       '-i',in_spd,'-o',out_dsm]

   dem_common_functions.CallSubprocessOn(dsmCMD)

def spd_to_dtm(in_spd, out_dtm, interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               keep_spd=False):
   """
   Create a Digital Surface Model (DTM) from an SPD file

   First classifies ground returns using a Progressive Morphology
   filter (spdpmfgrd) then calls the spdinterp tool.

   Arguments:

   * in_spd - Input SPD File
   * out_dtm - Output DTM file
   * interpolation - Interpolation method
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * bin_size - Bin size for spatial indexing
   * keep_spd - Keep ground classified SPD file and return path (default is to remove)

   Returns:

   * Path to ground classified SPD file

   """
   if not checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   spdfile_grd_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)[1]

   print('Classifying ground returns')
   classify_ground_spd(in_spd, spdfile_grd_tmp)

   print('Creating DTM')
   dtmCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdinterp'),
       '--dtm','--topo',
       '--in',interpolation,
       '-f',out_raster_format,
       '-b',str(bin_size),
       '-i',spdfile_grd_tmp,'-o',out_dtm]

   dem_common_functions.CallSubprocessOn(dtmCMD)

   if keep_spd:
      return spdfile_grd_tmp
   else:
      os.remove(spdfile_grd_tmp)
      return None

def las_to_dsm(in_las, out_dsm,
               interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               keep_spd=False):
   """
   Create Digital Surface Model (DSM) from a LAS file using SPDLib

   Utility function to convert LAS to SPD and call
   'spd_to_dsm'.

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * interpolation - Interpolation method
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * bin_size - Bin size for spatial indexing
   * keep_spd - Keep SPD file and return path (default is to remove)

   Returns:

   * Path to SPD file

   """

   spdfile_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)[1]

   convert_las_to_spd(in_las, spdfile_tmp,bin_size=bin_size)
   spd_to_dsm(spdfile_tmp, out_dsm,
               interpolation=interpolation,
               out_raster_format=out_raster_format,
               bin_size=bin_size)

   if keep_spd:
      return spdfile_tmp
   else:
      os.remove(spdfile_tmp)
      return None

def las_to_dtm(in_las, out_dtm,
               interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               keep_spd=False):
   """
   Create Digital Terrain Model (DTM) from a LAS file using SPDLib

   Utility function to convert LAS to SPD and call
   'spd_to_dtm'.

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * interpolation - Interpolation method
   * out_raster_format - GDAL format name for output raster (e.g., ENVI)
   * bin_size - Bin size for spatial indexing
   * keep_spd - Keep SPD file and return path (default is to remove).

   Returns:

   * Path to ground classified SPD file

   """

   spdfile_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)[1]

   convert_las_to_spd(in_las, spdfile_tmp,bin_size=bin_size)
   spdfile_grd_tmp = spd_to_dtm(spdfile_tmp, out_dtm,
               interpolation=interpolation,
               out_raster_format=out_raster_format,
               bin_size=bin_size,
               keep_spd=True)

   os.remove(spdfile_tmp)

   if keep_spd:
      return spdfile_grd_tmp
   else:
      os.remove(spdfile_grd_tmp)
      return None
