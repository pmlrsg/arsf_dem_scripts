#Author: Dan Clewley (dac)
#Created on: 02 April 2015
"""
Functions for working with LiDAR data using points2grid:

https://github.com/CRREL/points2grid

Requires points2grid to be installed.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import tempfile
import subprocess
# Import common files
from .. import dem_common
from .. import dem_common_functions
from .. import dem_utilities

def _checkPoints2Grid():
   """
   Check if Points2Grid is installed.
   """

   try:
      dem_common_functions.CallSubprocessOn([os.path.join(dem_common.POINTS2GRID_BIN_PATH,'points2grid'),'--help'],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False

def export_ascii_raster(points2dem_outfile, out_raster,
                          output_type='mean',projection=None):
   """
   Exports raster created by points2dem

   Arguments:

   * points2dem_outfile - Output file passed to points2dem
   * out_raster - Output file (extension determines format).
   * output_type - points2dem output type (min, max, mean, idw, std, den, all)
   * projection - Proj4 string / WKT file defining projection

   """

   in_raster = points2dem_outfile + '.{}.asc'.format(output_type)

   # If ASCII output is wanted just copy file
   if os.path.splitext(out_raster)[-1] == '.asc':
      shutil.copy(in_raster, out_raster)
   # Otherwise use gdal_translate
   else:
      out_raster_format = dem_utilities.get_gdal_type_from_path(out_raster)
      gdal_translate_cmd = ['gdal_translate',
                            '-of',out_raster_format]
      if projection is not None:
         gdal_translate_cmd.extend(['-a_srs',projection])

      gdal_translate_cmd.extend([in_raster, out_raster])
      dem_common_functions.CallSubprocessOn(gdal_translate_cmd)

def las_to_dsm(in_las, out_dsm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None):
   """
   Create Digital Surface Model (DSM) from a LAS file using points2grid

   TODO: Currently doesn't drop noisy points

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * resolution - output resolution

   """
   if not _checkPoints2Grid():
      raise Exception('Could not find points2grid, checked {}'.format(dem_common.POINTS2GRID_BIN_PATH))

   outdsm_handler, dsm_tmp = tempfile.mkstemp(suffix='', dir=dem_common.TEMP_PATH)

   print('Creating surface')
   surfaceCMD = [os.path.join(dem_common.POINTS2GRID_BIN_PATH,'points2grid'),
                 '--mean','--output_file_name',dsm_tmp,
                 '--output_format','arc',
                 '--resolution',str(resolution),
                 '-i',in_las]
   dem_common_functions.CallSubprocessOn(surfaceCMD)

   print('Exporting')
   export_ascii_raster(dsm_tmp, out_dsm, projection=projection)

   os.close(outdsm_handler)
   os.remove(dsm_tmp + '.mean.asc')

   return None

