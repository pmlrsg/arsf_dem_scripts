#Author: Dan Clewley (dac)
#Created On: 06/10/2014
"""
General utilities for working with LiDAR data to perform common tasks. 

Available functions:

* create_lidar_mosaic - Create mosaic from lidar data.
* get_lidar_buffered_bb - buffer bounding box by 'DEFAULT_LIDAR_DEM_BUFFER' or user specified buffer.

"""
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import glob
import tempfile

from .. import dem_common
from .. import dem_utilities
from .. import common_functions

from . import grass_lidar
from . import lastools_lidar
from . import spdlib_lidar
from . import laspy_lidar
from .. import grass_library

try:
   import grass.script as grass
   import grass.script.setup as gsetup
except ImportError as err:
   print("Could not import grass library. Try setting 'GRASS_PYTHON_LIB_PATH' environmental variable.", file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

def create_lidar_mosaic(in_lidar_files, out_mosaic, 
                     out_screenshot=None,
                     shaded_relief_screenshots=False,
                     in_projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                     nodata=dem_common.NODATA_VALUE,
                     lidar_format='LAS',
                     raster_type='DSM',
                     fill_nulls=False,
                     remove_grassdb=True,
                     grassdb_path=None):
   """
   Create raster mosaic from lidar files using GRASS by binning 
   to 'resolution' and taking the mean point attribute within each pixel.
   
   Default is to use first returns to create a DSM but can create
   intensity image by setting 'raster_type' to 'INTENSITY'.

   Accepts lidar data in 'LAS' or 'ASCII' format, set using 'lidar_format'.

   Can export screenshots / quicklooks for each file or just the mosaic in JPEG format if
   'out_screenshots' is supplied.

   Arguments:

   * in_lidar_files - List of input lidar files in ASCII or LAS format (must all be the same format), directory containing files or path to a single file.
   * out_mosaic - Output mosaic, extension of mosaic determines filetype (e.g., .tif for GeoTIFF).
   * out_screenshot - Out screenshot file for mosaic / directory for all files
   * in_projection - Input projection of lidar data (e.g., UKBNG).
   * resolution - Resolution in units of input projection for output mosaic (normally metres).
   * nodata - No data value.
   * lidar_format - LAS or ASCII.
   * raster_type - Type of output raster:

      * DSM (Digital Surface Model) - Uses first returns, each pixel represents the top of canopy / buildings.
      * DTM (Digital Terrain Model) - Uses last returns, each pixel represents the ground. In reality this isn't a true DTM as it will depend on where the last return was from.
      * DEM (Digital Elevation Model) - Uses all returns.
      * UNFILTEREDDEM - Uses all returns, keeps points classified as noise.
      * Intensity - Intensity image.

   * fill_nulls - Null fill values
   * remove_grassdb - Remove GRASS database after processing is complete
   * grassdb_path - Input path to GRASS database, if not supplied will create one.
          
   Returns:
   
   * out_mosaic path / out_mosaic name in GRASS database
   * path to GRASS database / None
                             
   """
   drop_class = None
   keep_class = None
   las2txt_flags = None
   returns_to_keep = 'all'

   # Set options for raster type to be exported
   # DSM - first returns (top of canopy)
   if raster_type.upper() == 'DSM':   
      val_field = 'z'
      drop_class = 7
      las2txt_flags = '-first_only'
      returns_to_keep = 'first'
   # DSM - last returns (ground surface)
   elif raster_type.upper() == 'DTM':
      val_field = 'z'
      drop_class = 7
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
      drop_class = 7
      if shaded_relief_screenshots:
         common_functions.WARNING('Creating shaded relief screenshots makes no sense with intensity images. Ignoring')
         shaded_relief_screenshots = False
   else:
      raise Exception('raster_type "{}" was not recognised'.format(raster_type))

   # Set output type and data format for output rasters
   out_raster_format = dem_utilities.get_gdal_type_from_path(out_mosaic)
   out_raster_type = dem_common.GDAL_OUTFILE_DATATYPE

   # Sort out input lidar files

   # Expect a list of files, if passed in string
   # create list.
   if isinstance(in_lidar_files,str):
      in_lidar_files = [in_lidar_files]
   
   # If a directory, look for files
   if os.path.isdir(in_lidar_files[0]):
      if lidar_format.upper() == 'LAS':
         in_lidar_files_list = glob.glob(
                           os.path.join(in_lidar_files[0],'*LAS'))
         in_lidar_files_list.extend(glob.glob(
                           os.path.join(in_lidar_files[0],'*las')))

      # If ASCII format or not las files found check for txt files
      if lidar_format.upper() == 'ASCII' or len(in_lidar_files_list) == 0:
         in_lidar_files_list = glob.glob(
                           os.path.join(in_lidar_files[0],'*txt'))
         if len(in_lidar_files_list) != 0:
            lidar_format = 'ASCII'
   else:
      in_lidar_files_list = in_lidar_files
      if os.path.splitext(in_lidar_files_list[0])[-1].lower() != '.las':
         lidar_format = 'ASCII' 

   if len(in_lidar_files_list) == 0:
      raise Exception('No lidar files were passed in or found from path provided')
   
   out_screenshots_dir = None
   try:
      if os.path.isdir(out_screenshot):
         out_screenshots_dir = out_screenshot 
   except TypeError:
      pass

   # Create variable for GRASS path
   raster_names = []
   
   # Create raster from point cloud files
   linenum = 1
   totlines = len(in_lidar_files_list)

   # If there is only one line and it's not being null filled
   # need to export raster.
   out_single_raster = None
   if totlines == 1 and not fill_nulls:
      out_single_raster = out_mosaic

   # Create mosaic from lidar files
   print('')
   if len(in_lidar_files_list) > 1:
      common_functions.PrintTermWidth('Creating LiDAR Mosaic from {} lines'.format(len(in_lidar_files_list)),padding_char='*')
   else:
      common_functions.PrintTermWidth('Creating LiDAR raster for a single line',padding_char='*')
   print('')

   for in_lidar_file in in_lidar_files_list:
      common_functions.PrintTermWidth('Creating {0} raster from "{1}" ({2}/{3})'.format(raster_type,os.path.split(in_lidar_file)[-1],linenum, totlines))
      # Check file exists
      if not os.path.isfile(in_lidar_file):
         raise Exception('Could not open "{}"'.format(in_lidar_file))

      if lidar_format.upper() == 'LAS':
         out_raster_name, grassdb_path = grass_lidar.las_to_raster(in_lidar_file,out_raster=out_single_raster, 
                  remove_grassdb=False,
                  grassdb_path=grassdb_path,
                  val_field=val_field,
                  drop_class=drop_class,
                  keep_class=keep_class,
                  las2txt_flags=las2txt_flags,
                  projection=in_projection,
                  bin_size=resolution,
                  out_raster_format=out_raster_format,
                  out_raster_type=out_raster_type)
      elif lidar_format.upper() == 'ASCII':
         out_raster_name, grassdb_path = grass_lidar.ascii_to_raster(in_lidar_file,out_raster=out_single_raster, 
                  remove_grassdb=False,
                  grassdb_path=grassdb_path,
                  val_field=val_field,
                  drop_class=drop_class,
                  keep_class=keep_class,
                  returns=returns_to_keep,
                  projection=in_projection,
                  bin_size=resolution,
                  out_raster_format=out_raster_format,
                  out_raster_type=out_raster_type)

      raster_names.append(out_raster_name)

      # Export screenshot (if requested)
      if out_screenshots_dir is not None:
         screenshot_file = dem_utilities.get_screenshot_path(in_lidar_file, out_screenshots_dir)
         print(' Saving screenshot to {}'.format(screenshot_file))
         dem_utilities.export_screenshot(out_raster_name, screenshot_file,
                                    import_to_grass=False,
                                    shaded_relief=shaded_relief_screenshots,
                                    projection=in_projection,
                                    grassdb_path=grassdb_path,
                                    remove_grassdb=False)
      
      linenum += 1

   if not fill_nulls:
      out_patched_file = out_mosaic
   else:
      out_patched_file = None

   if len(raster_names) > 1:
      patched_name, grassdb_path = dem_utilities.patch_files(raster_names, 
                                     out_file=out_patched_file,
                                     import_to_grass=False,
                                     nodata=nodata,
                                     out_raster_format=out_raster_format,
                                     out_raster_type=out_raster_type,
                                     projection=in_projection,
                                     grassdb_path=grassdb_path,
                                     remove_grassdb=False)
   else:
      patched_name = raster_names[0] 

   print('Tiles patched OK')
   # Fill null values
   if fill_nulls:
      patched_name, grassdb_path = dem_utilities.offset_null_fill_dem(patched_name, out_mosaic, 
                                    import_to_grass=False,
                                    separation_file=None,
                                    ascii_separation_file=False,
                                    fill_nulls=fill_nulls,
                                    nodata=nodata,
                                    out_raster_format=out_raster_format,
                                    out_raster_type=out_raster_type,
                                    projection=in_projection,
                                    grassdb_path=grassdb_path,
                                    remove_grassdb=False)

   # If a file rather than a directory was passed in for screenshots, assume only require
   # for mosaic.
   if (out_screenshots_dir is not None or out_screenshot is not None) and len(raster_names) > 1:
      if out_screenshots_dir is not None:
         if out_mosaic is not None:
            screenshot_file = dem_utilities.get_screenshot_path(out_mosaic,out_screenshots_dir)
         else:
            screenshot_file = os.path.join(out_screenshots_dir,'{}_mosaic.jpg'.format(raster_type.lower()))
      else:
         screenshot_file = out_screenshot
      dem_utilities.export_screenshot(patched_name, screenshot_file,
                                       import_to_grass=False,
                                       shaded_relief=shaded_relief_screenshots,
                                       projection=in_projection,
                                       grassdb_path=grassdb_path,
                                       remove_grassdb=False)

  # Remove GRASS database created
   if remove_grassdb:
      shutil.rmtree(grassdb_path)
      return out_mosaic, None
   else:
      print(patched_name)
      return patched_name, grassdb_path

def get_lidar_buffered_bb(in_bounding_box, bb_buffer=dem_common.DEFAULT_LIDAR_DEM_BUFFER):
   """
   Buffer a bounding box (in degrees) by the standard lidar buffer size (in m)

   Arguments:

   * in_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]
   * bb_buffer - Dictionary of values in metres e.g., {'N' : 2000, 'E' : 2000, 'S' : 2000, 'W' : 2000} 

   Returns:

   * out_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]

   """

   # Get latitude
   lat = (in_bounding_box[0] + in_bounding_box[1]) / 2.0

   # Convert default lidar buffer (in degrees)
   east_buffer, north_buffer = dem_utilities.m_to_deg(lat, 
                                                bb_buffer['E'], 
                                                bb_buffer['N'])
   west_buffer, south_buffer = dem_utilities.m_to_deg(lat, 
                                                bb_buffer['W'], 
                                                bb_buffer['S'])

   out_bounding_box = [0,0,0,0]

   out_bounding_box[0] = in_bounding_box[0] - south_buffer
   out_bounding_box[1] = in_bounding_box[1] + north_buffer
   out_bounding_box[2] = in_bounding_box[2] - west_buffer
   out_bounding_box[3] = in_bounding_box[3] + east_buffer

   return out_bounding_box

