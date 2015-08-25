#Author: Dan Clewley (dac)
#Created on: 02 April 2015
"""
Functions for working with LiDAR data using points2grid:

https://github.com/CRREL/points2grid

Requires the development version of points2grid to be installed which
has filters for LAS points.

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

def _las_to_dem(in_las, out_dem,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               demtype='DSM',
               grid_method='mean',
               quiet=True):
   """
   Create Digital Elevation Model (DEM) from a LAS file using points2grid
   Called by las_to_dtm or las_to_dem

   Arguments:

   * in_las - Input LAS File
   * out_dem - Output DTM file
   * resolution - output resolution
   * demtype - DSM / DTM
   * grid_method - points2grid output type (min, max, mean, idw or std)
   * quiet - don't print output from points2grid command

   """
   if not _checkPoints2Grid():
      raise Exception('Could not find points2grid, checked {}'.format(dem_common.POINTS2GRID_BIN_PATH))

   outdem_handler, dem_tmp = tempfile.mkstemp(suffix='', dir=dem_common.TEMP_PATH)

   print('Creating surface')
   surfaceCMD = [os.path.join(dem_common.POINTS2GRID_BIN_PATH,'points2grid'),
                 '--exclude_class', '7',
                 '--output_file_name',dem_tmp,
                 '--output_format','arc',
                 '--resolution',str(resolution)]

   if grid_method.lower() == 'min':
      surfaceCMD.extend(['--min'])
   elif grid_method.lower() == 'max':
      surfaceCMD.extend(['--max'])
   elif grid_method.lower() == 'mean':
      surfaceCMD.extend(['--mean'])
   elif grid_method.lower() == 'idw':
      surfaceCMD.extend(['--idw'])
   elif grid_method.lower() == 'std':
      surfaceCMD.extend(['--std'])

   if demtype.upper() == 'DSM':
      surfaceCMD.extend(['--first_return_only'])
   elif demtype.upper() == 'DTM':
      surfaceCMD.extend(['--last_return_only'])
   else:
      raise Exception('DEM Type must be "DSM" or "DTM"')

   surfaceCMD.extend(['-i',in_las])
   dem_common_functions.CallSubprocessOn(surfaceCMD, redirect=quiet)

   print('Exporting')
   export_ascii_raster(dem_tmp, out_dem, projection=projection,
                                          output_type=grid_method.lower())

   os.close(outdem_handler)
   os.remove(dem_tmp + '.{}.asc'.format(grid_method.lower()))

   return None

def las_to_dsm(in_las, out_dsm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               grid_method='mean',
               quiet=True):
   """
   Create Digital Surface Model (DSM) from a LAS file using points2grid

   Arguments:

   * in_las - Input LAS File
   * out_dsm - Output DTM file
   * resolution - output resolution
   * grid_method - points2grid output type (min, max, mean, idw or std)
   * quiet - don't print output from points2grid command

   """
   _las_to_dem(in_las, out_dsm,
               resolution=resolution,
               projection=projection,
               demtype='DSM',
               grid_method=grid_method,
               quiet=quiet)

   return None

def las_to_dtm(in_las, out_dtm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               grid_method='mean',
               quiet=True):
   """
   Create Digital Terrain Model (DSM) from a LAS file using points2grid

   The DTM is created using only last returns, therefore is not a true DTM as
   not all last returns will be from the ground.

   Arguments:

   * in_las - Input LAS File
   * out_dtm - Output DTM file
   * resolution - output resolution
   * grid_method - points2grid output type (min, max, mean, idw or std)
   * quiet - don't print output from points2grid command

   """
   _las_to_dem(in_las, out_dtm,
               resolution=resolution,
               projection=projection,
               demtype='DTM',
               grid_method=grid_method,
               quiet=quiet)

   return None

