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
import subprocess
import tempfile
# Import common files
from .. import dem_common
from .. import dem_common_functions

def _checkSPDLib():
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

   Known Issues: If LAS file isn't sorted SPDLib will print lots of warnings
   about writing incomplete pulses (1 for each pulse in the worst case), which
   seems to cause problems for CallSubprocessOn. Better LAS reading for SPDLib
   is currently in-progress.

   Arguments:

   * in_las - Input LAS file
   * out_spd - Output SPD file
   * wkt - WKT file defining projection (will obtain from LAS if not provided)
   * bin_size - Bin size for spatial indexing

   Returns:

   * None

   """

   if not _checkSPDLib():
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

   subprocess.check_call(spdCMD)

   # Remove temp files
   shutil.rmtree(temp_dir)

def classify_ground_spd(in_spd,out_spd,
                        bin_size=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Classify ground returns in an SPD file using a progressive morphology
   filter for the initial classification and a combination of two algorithms:

   1. Progressive Morphology Filter (PMF; Zhang et al., 2003): spdpmfgrd.
   2. Multi-Scale Curvature algorithm (MCC; Evans and Hudak, 2007): spdmccgrd

   Arguments:

   * in_spd - Input SPD File
   * out_spd - Output SPD file
   * bin_size - Bin size for spatial indexing

   Returns:

   * None

    """
   if not _checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   spdfile_handler, spdfile_grd_tmp = tempfile.mkstemp(suffix='.spd',
                                                       dir=dem_common.TEMP_PATH)

   # 1. PMF Filter
   pmfCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdpmfgrd'),
             '-b',str(bin_size),
             '--grd', '1',
             '-i',in_spd,'-o',spdfile_grd_tmp]

   subprocess.check_call(pmfCMD)

   # 2. MCC applied to ground classified returns.
   mccCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdmccgrd'),
             '-b',str(bin_size),
             '--class', '3',
             '--initcurvetol', '1',
             '-i',spdfile_grd_tmp,'-o',out_spd]

   subprocess.check_call(mccCMD)

   os.close(spdfile_handler)
   os.remove(spdfile_grd_tmp)


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
   if not _checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   dsmCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdinterp'),
       '--dsm','--topo',
       '--in',interpolation,
       '-f',out_raster_format,
       '-b',str(bin_size),
       '-i',in_spd,'-o',out_dsm]

   subprocess.check_call(dsmCMD)

def spd_to_dtm(in_spd, out_dtm, interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               keep_spd=False):
   """
   Create a Digital Surface Model (DTM) from an SPD file

   First classifies ground returns using a combination of ia Progressive
   Morphology filter and the Multi-scale Curvature algorithm
   then calls the spdinterp tool.

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
   if not _checkSPDLib():
      raise Exception('Could not find SPDLib')

   if not os.path.isfile(in_spd):
      raise Exception('Input SPD file "{}" does not exist'.format(in_spd))

   spdfile_handler, spdfile_grd_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)

   print('Classifying ground returns')
   classify_ground_spd(in_spd, spdfile_grd_tmp)

   print('Creating DTM')
   dtmCMD = [os.path.join(dem_common.SPDLIB_BIN_PATH,'spdinterp'),
       '--dtm','--topo',
       '--in',interpolation,
       '-f',out_raster_format,
       '-b',str(bin_size),
       '-i',spdfile_grd_tmp,'-o',out_dtm]

   subprocess.check_call(dtmCMD)

   os.close(spdfile_handler)
   if keep_spd:
      return spdfile_grd_tmp
   else:
      os.remove(spdfile_grd_tmp)
      return None

def las_to_dsm(in_las, out_dsm,
               interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               wkt=None,
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
   * wkt - WKT file defining projection (will obtain from LAS if not provided)
   * keep_spd - Keep SPD file and return path (default is to remove)

   Returns:

   * Path to SPD file

   """

   spdfile_handler, spdfile_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)

   convert_las_to_spd(in_las, spdfile_tmp,bin_size=bin_size, wkt=wkt)
   spd_to_dsm(spdfile_tmp, out_dsm,
               interpolation=interpolation,
               out_raster_format=out_raster_format,
               bin_size=bin_size)

   os.close(spdfile_handler)
   if keep_spd:
      return spdfile_tmp
   else:
      os.remove(spdfile_tmp)
      return None

def las_to_dtm(in_las, out_dtm,
               interpolation=dem_common.SPD_DEFAULT_INTERPOLATION,
               out_raster_format=dem_common.GDAL_OUTFILE_FORMAT,
               bin_size=dem_common.DEFAULT_LIDAR_RES_METRES,
               wkt=None,
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
   * wkt - WKT file defining projection (will obtain from LAS if not provided)
   * keep_spd - Keep SPD file and return path (default is to remove).

   Returns:

   * Path to ground classified SPD file

   """

   spdfile_handler, spdfile_tmp = tempfile.mkstemp(suffix='.spd', dir=dem_common.TEMP_PATH)

   convert_las_to_spd(in_las, spdfile_tmp,bin_size=bin_size, wkt=wkt)
   spdfile_grd_tmp = spd_to_dtm(spdfile_tmp, out_dtm,
               interpolation=interpolation,
               out_raster_format=out_raster_format,
               bin_size=bin_size,
               keep_spd=keep_spd)

   os.close(spdfile_handler)
   os.remove(spdfile_tmp)

   if keep_spd:
      return spdfile_grd_tmp
   else:
      return None
