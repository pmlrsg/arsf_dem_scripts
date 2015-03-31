#Author: Dan Clewley (dac)
#Created on: 31 March 2015
"""
Functions for working with LiDAR data using FUSION (http://forsys.cfr.washington.edu/fusion/fusion_overview.html)

Requires FUSION to be installed.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import tempfile
# Import common files
from .. import dem_common
from .. import dem_common_functions

def _checkFUSION():
   """Check if FUSION is installed."""

   try:
      dem_common_functions.CallSubprocessOn([os.path.join(dem_common.FUSION_BIN_PATH,'groundfilter.exe')],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False

def _set_windows_path(in_path):
   """
   Replace all '/' in paths with double backslash
   """
   out_path = in_path.replace('/','\\')
   return out_path

def classify_ground_las(in_las,out_las,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Classify ground returns in a LAS/LDA file using a

   Calls the groundfilter.exe tool.

   Arguments:

   * in_spd - Input LAS/LDA file
   * out_las - Output LAS file
   * resolution - Resolution used

   Returns:

   * None

    """
   if not _checkFUSION():
      raise Exception('Could not find FUSION')

   if not os.path.isfile(in_las):
      raise Exception('Input file "{}" does not exist'.format(in_spd))

   groundCMD = [os.path.join(dem_common.FUSION_BIN_PATH,'groundfilter.exe'),
                _set_windows_path(out_las), str(resolution),
                _set_windows_path(in_las)]
   dem_common_functions.CallSubprocessOn(groundCMD)

def export_dtm_raster(in_dtm, out_raster):
   """
   Export FUSION DTM format raster to ENVI or Geotiff

   Arguments:

   * in_dtm - Input DTM in Fusion DTM format
   * out_raster - Output file in GeoTiff (.tif extension) or ENVI (all other extensions) format.

   """

   convertCMD = [os.path.join(dem_common.FUSION_BIN_PATH,'DTM2ENVI.exe')]

   # If a tiff is requested use seperate command, else assume ENVI format
   if os.path.splitext(out_raster)[-1].lower() == '.tif' or os.path.splitext(out_raster)[-1].lower() == '.tiff':
      convertCMD = [os.path.join(dem_common.FUSION_BIN_PATH,'DTM2TIF.exe')]

   convertCMD.extend([_set_windows_path(in_dtm), _set_windows_path(out_raster)])
   dem_common_functions.CallSubprocessOn(convertCMD)


def las_to_dsm(in_las, out_dsm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Create Digital Surface Model (DSM) from a LAS file using FUSION

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * resolution - output resolution


   """
   outdtm_handler, dtm_tmp = tempfile.mkstemp(suffix='.dtm', dir=dem_common.TEMP_PATH)

   print('Creating surface')
   surfaceCMD = [os.path.join(dem_common.FUSION_BIN_PATH,'canopymodel.exe'),
                 _set_windows_path(dtm_tmp),
                 str(resolution), 'M', 'M', '0','0','0','0',
                 _set_windows_path(in_las)]
   dem_common_functions.CallSubprocessOn(surfaceCMD)

   print('Exporting')
   export_dtm_raster(dtm_tmp, out_dsm)

   os.close(outdtm_handler)
   os.remove(dtm_tmp)

   return None

def las_to_dtm(in_las, out_dtm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES):
   """
   Create Digital Terrain Model (DTM) from a LAS file using FUSION

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * resolution - output resolution

   """
   outlas_handler, las_tmp = tempfile.mkstemp(suffix='.las', dir=dem_common.TEMP_PATH)
   outdtm_handler, dtm_tmp = tempfile.mkstemp(suffix='.dtm', dir=dem_common.TEMP_PATH)

   print('Classifying ground returns')
   classify_ground_las(in_las, las_tmp, resolution=resolution)

   print('Creating surface')
   surfaceCMD = [os.path.join(dem_common.FUSION_BIN_PATH,'GridSurfaceCreate.exe'),
                 _set_windows_path(dtm_tmp),
                 str(resolution), 'M', 'M', '0','0','0','0',
                 _set_windows_path(las_tmp)]
   dem_common_functions.CallSubprocessOn(surfaceCMD)

   print('Exporting')
   export_dtm_raster(dtm_tmp, out_dtm)

   os.close(outlas_handler)
   os.close(outdtm_handler)

   os.remove(las_tmp)
   os.remove(dtm_tmp)

   return None
