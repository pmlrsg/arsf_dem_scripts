#!/usr/bin/env python
#
# dem_common
#
# Author: Dan Clewley (dac@pml.ac.uk)
# Created on: 05 November 2014
# Licensing: 

"""
A set of common variables (default parameters, paths etc.,) for the arsf_dem module.

Reads parameter from a config file checks:

1. Current working directory for arsf_dem.cfg
2. Home folder for .arsf_dem or .arsf_dem.cfg
3. Library path for arsf_dem.cfg

These files can be changed as required to override default settings at the project, user or 
system level.

"""
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import glob
import math
try:
   import ConfigParser
except ImportError:
   import configparser as ConfigParser

def get_config_fallback(config, section, option, fallback=None):
   """
   Try to get config parameter, in case of error
   default to fallback value.

   If we move to Python3 can remove this as and just replace with get
   which will accept a fallback value
   """
   try:
      return config.get(section,option)
   except:
      return fallback

def get_config_int_fallback(config, section, option, fallback=None):
   """
   Try to get config parameter as integer, in case of error
   default to fallback value.

   If we move to Python3 can remove this as and just replace with getint
   which will accept a fallback value
   """
   try:
      return config.getint(config,section,option)
   except:
      return fallback


# Functions to try and get paths for files
def get_grass_lib_path():
   """
   Try to get GRASS path by trying common locations for Linux, OS X and 
   Windows.

   For Windows assumes installed through OSGeo4W

   Exits if path does not exist
   """
   LINUX64_GRASS_LIB_PATH = '/usr/lib64/grass'
   LINUX32_GRASS_LIB_PATH = '/usr/lib/grass'
   OSX_GRASS_LIB_PATH = '/Aplications/GRASS/'
   WIN_GRASS_LIB_PATH = 'C:/OSGeo4W/apps/grass/grass'

   if sys.platform.find('win') > -1:
      # As under Windows OSGeo4W stores with version name, run Glob to try
      # and find path from root
      grass_version_path = glob.glob(WIN_GRASS_LIB_PATH + '*')
      if (len(grass_version_path) > 0) and (os.path.isdir(grass_version_path[-1])):
         return grass_version_path[-1]
      else:
         print('Could not find GRASS library. Set in Config file using "GRASS_LIB_PATH"',file=sys.stderr)
         sys.exit(1)
   elif sys.platform.find('osx') > -1:
      if os.path.isdir(OSX_GRASS_LIB_PATH):
         return OSX_GRASS_LIB_PATH
      else:
         print('Could not find GRASS library. Set in Config file using "GRASS_LIB_PATH"',file=sys.stderr)
         sys.exit(1)
   # If its not Windows or OS X, assume Linux or something UNIX-like
   else:
      if os.path.isdir(LINUX64_GRASS_LIB_PATH):
         return LINUX64_GRASS_LIB_PATH
      elif os.path.isdir(LINUX32_GRASS_LIB_PATH):
         return LINUX32_GRASS_LIB_PATH
      else:
         print('Could not find GRASS library. Set in Config file using "GRASS_LIB_PATH"',file=sys.stderr)
         sys.exit(1)

def get_grass_python_lib_path(GRASS_LIB_PATH=get_grass_lib_path()):
   """
   Try to find GRASS Python library path. 
   If GRASS_LIB_PATH is passed in will use this, otherwise will try default
   locations.
   """
   GRASS_PYTHON_LIB_PATH = os.path.join(GRASS_LIB_PATH,'etc','python')
   
   if os.path.isdir(GRASS_PYTHON_LIB_PATH):
      return GRASS_PYTHON_LIB_PATH
   else:
      print('Could not find GRASS Python library. Was not where expected relative to "GRASS_LIB_PATH".',file=sys.stderr)
      print('You need to define in config file using "GRASS_PYTHON_LIB_PATH".',file=sys.stderr)
      sys.exit(1)

def get_temp_path():
   """Function to get temp path by trying
   common environmental variables.

   Defaults to /tmp/
   """
   TEMP_PATH = None

   temp_env_vars = ['TMPDIR','TEMP']

   for temp_var in temp_env_vars:

      try:
         TEMP_PATH = os.environ[temp_var]
      except KeyError:
         pass

   if TEMP_PATH is None:
      TEMP_PATH = '/tmp'

   return TEMP_PATH

def get_lastools_path():
   """
   Function to get path to LAStools

   Under Linux / OS X assumes they are added to $PATH so 
   don't need to pass in full path and returns empty string.

   Under Windows assume LAStools has been installed to 
   'C:\LAStools'
   """

   if sys.platform.find('win') > -1:
      win_lastools_path = os.path.join('C:\LAStools','bin')
      if os.path.isdir(win_lastools_path):
         return win_lastools_path
      else:
         print('Could not find LAStools bin directory.\nChecked {}\n'.format(win_lastools_path),file=sys.stderr)
         print('If you want to use LAS format files you need to define the path in the config file using "LASTOOLS_FREE_BIN_PATH" and "LASTOOLS_NONFREE_BIN_PATH"',file=sys.stderr)
   else:
      return ''

# Read in config parser file
config_current_dir = os.path.join(os.path.abspath('.'),'arsf_dem.cfg')
config_home_dir = os.path.join(os.path.expanduser('~'),'.arsf_dem')
config_home_dir_ext = os.path.join(os.path.expanduser('~'),'.arsf_dem.cfg')
config_lib_dir = os.path.join(os.path.split(__file__)[0],'arsf_dem.cfg')

#: List of locations for config file, will read from first found.
config_file_locations = [config_current_dir, config_home_dir, config_home_dir_ext, config_lib_dir]

config = ConfigParser.ConfigParser()
read_config = False

# Itterate through config file locations until one is found 
# which can be read.
for config_file in config_file_locations:
   if os.path.isfile(config_file):
      try:
         config.read(config_file)
         read_config = True
         break
      except Exception:
         pass

if not read_config:
   raise Exception('Could not find config file with paths needed by library. Try reinstalling arsf_dem')

#: Temporary path
TEMP_PATH = get_config_fallback(config,'system','TEMP_PATH',fallback=get_temp_path())

#: Path for GRASS Library
GRASS_LIB_PATH = get_config_fallback(config,'grass','GRASS_LIB_PATH',fallback=get_grass_lib_path())

#: Path for GRASS Python library
GRASS_PYTHON_LIB_PATH = get_config_fallback(config,'grass','GRASS_PYTHON_LIB_PATH',
                           fallback=get_grass_python_lib_path(GRASS_LIB_PATH))

# Set environmental variable for GRASS lib
os.environ['GISBASE'] = GRASS_LIB_PATH

#: Path for GRASS database template
GRASS_DATABASE_TEMPLATE = get_config_fallback(config,'grass','GRASS_DATABASE_TEMPLATE',
                           fallback='/users/rsg/arsf/usr/share/grass_db_template/')

# Set some common options for raster creation

#: Default method for interpolation when resampling
RESAMPLE_METHOD = get_config_fallback(config,'rastercreation','RESAMPLE_METHOD',fallback='near')
#: Default GDAL output format
GDAL_OUTFILE_FORMAT = get_config_fallback(config,'rastercreation','GDAL_OUTFILE_FORMAT',fallback='ENVI')
#: Default GDAL output data type
GDAL_OUTFILE_DATATYPE = get_config_fallback(config,'rastercreation','GDAL_OUTFILE_DATATYPE',fallback='Float32')
#: Default GDAL creation options
GDAL_CREATION_OPTIONS = get_config_fallback(config,'rastercreation','GDAL_CREATION_OPTIONS',fallback='"INTERLEAVE=BIL"')
#: Default nodata value
NODATA_VALUE = get_config_int_fallback(config,'rastercreation','NODATA_VALUE',fallback=0)

# Set options for lidar
#: Default lidar resolution (in metres)
DEFAULT_LIDAR_RES_METRES = get_config_int_fallback(config,'lidar','DEFAULT_LIDAR_RES_METRES',fallback=2)
#: Default lidar projection for grass
DEFAULT_LIDAR_PROJECTION_GRASS = get_config_fallback(config,'lidar','DEFAULT_LIDAR_PROJECTION_GRASS,',fallback='UKBNG')

#: Default buffer, in metres, to be used when patching lidar with other data
DEFAULT_LIDAR_DEM_BUFFER = {'N' : 2000,
                            'E' : 2000,
                            'S' : 2000,
                            'W' : 2000}

#: Order of columns in ASCII format lidar data 
LIDAR_ASCII_ORDER = {'time':1,
                     'x':2,'y':3,'z':4,
                     'intensity':5,
                     'classification':6,
                     'returnnumber':7,
                     'numberofreturns':8,
                     'scanangle':9}

#: Default buffer for APL DEM (in degrees)
DEFAULT_APL_DEM_BUFFER = {'N' : 0.05,
                          'E' : 0.05,
                          'S' : 0.05,
                          'W' : 0.05}

# Set locations and resolution of standard DEM mosaics

#: Default location of ASTER DEM mosaic
ASTER_MOSAIC_FILE = get_config_fallback(config,'dems','ASTER_MOSAIC_FILE',
            fallback='/users/rsg/arsf/aster/aster_15m_dem_mosaic.vrt')
#: Resolution of ASTER DEM (in degrees)
ASTER_RES_DEGREES = (0.000277777777778,-0.000277777777778)
#: Resolution of ASTER DEM (in metres)
ASTER_RES_METRES = (15,-15)

#: Default location of NextMap DEM mosaic 
NEXTMAP_MOSAIC_FILE = get_config_fallback(config,'dems','NEXTMAP_MOSAIC_FILE',
            fallback='/users/rsg/arsf/nextmap/neodc/nextmap_dsm_mosaic_bng.vrt')
#: Resolution of NextMap DEM (in degrees)
NEXTMAP_RES_DEGREES = (0.0000554040,-0.0000554040)
#: Resolution of NextMap DEM (in metres)
NEXTMAP_RES_METRES = (5,-5)

#: Default location of SRTM Mosaic
SRTM_MOSAIC_FILE = get_config_fallback(config,'dems','SRTM_MOSAIC_FILE',
            fallback='/users/rsg/arsf/scratch_space/SRTM/srtm_global_mosaic_90m.tif')
#: Resolution of SRTM DEM (in degrees)
SRTM_RES_DEGREES = (0.000833333333333,-0.000833333333333)
#: Resolution of SRTM DEM (in metres)
SRTM_RES_METRES = (90,-90)

                     
# Set locations of separation files
#: Default location of vertical separation file between Newlyn and WGS-84 datum (WGS84LL projection)
UKBNG_SEP_FILE_WGS84  = get_config_fallback(config,'separationfiles','UKBNG_SEP_FILE_WGS84',
                  fallback='/users/rsg/arsf/dems/aster/separation_files/uk_separation_file_WGS84LL.dem')
#: If UKBNG_SEP_FILE_WGS84 is ASCII format
UKBNG_SEP_FILE_WGS84_IS_ASCII = False
                     
#: Default location of vertical separation file between Newlyn and WGS-84 datum (UKBNG projection)
UKBNG_SEP_FILE_UKBNG = get_config_fallback(config,'separationfiles','UKBNG_SEP_FILE_UKBNG',
                  fallback='/users/rsg/arsf/dems/aster/separation_files/uk_separation_file_UKBNG.dem')
#: If UKBNG_SEP_FILE_UKBNG is ASCII format
UKBNG_SEP_FILE_UKBNG_IS_ASCII = False

#: Default location of vertical separation file between geoid and WGS-84 datum.
WWGSG_FILE = get_config_fallback(config,'separationfiles','WWGSG_FILE',
                  fallback='/users/rsg/arsf/dems/geoid-spheroid/ww15mgh.grd')
#: If WWGSG_FILE is ASCII
WWGSG_FILE_IS_ASCII = True

#: Default location of vertical separation file between EGM96 and Newlyn vertical datum (UKBNG projection). 
EGM96_UKBNG_SEP_FILE_WGS84 = get_config_fallback(config,'separationfiles','EGM96_UKBNG_SEP_FILE_WGS84',
                  fallback='/users/rsg/arsf/dems/aster/separation_files/ww15mgh_minus_uk_separation_file_WGS84LL.dem')
#: If EMG96_UKBNG_SEP_FILE_UKBNG is ASCII format
EGM96_UKBNG_SEP_FILE_WGS84_IS_ASCII = False

#: Default location of vertical separation file between EGM96 and Newlyn vertical datum (UKBNG projection). 
EGM96_UKBNG_SEP_FILE_UKBNG = get_config_fallback(config,'separationfiles','EGM96_UKBNG_SEP_FILE_UKBNG',
                  fallback='/users/rsg/arsf/dems/aster/separation_files/ww15mgh_minus_uk_separation_file_UKBNG.dem')
#: If EMG96_UKBNG_SEP_FILE_UKBNG is ASCII format
EGM96_UKBNG_SEP_FILE_UKBNG_IS_ASCII = False

#: Location of OSTN02 transform file
OSTN02_NTV2_BIN_FILE = get_config_fallback(config,'projection','OSTN02_NTV2_BIN_FILE',
                  fallback=None)

#: Default Proj4 string for UKBNG 
if OSTN02_NTV2_BIN_FILE is not None:
   OSTN02_PROJ4_STRING = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.999601 +x_0=400000 +y_0=-100000 +ellps=airy +units=m +no_defs +nadgrids={}'.format(OSTN02_NTV2_BIN_FILE)
else:
   print('WARNING: OSTN02_NTV2_BIN_FILE was not set, any transforms to/from UKBNG will be inaccurate!')
   OSTN02_PROJ4_STRING = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.999601 +x_0=400000 +y_0=-100000 +ellps=airy +units=m +no_defs'

#: Default Proj4 string for WGS84LL
WGS84_PROJ4_STRING = '+proj=longlat +datum=WGS84 +no_defs'

# Set so variables for APL
#: Suffix for navigation data exported by aplnav
APL_POST_PROCESSED_NAV_SUFFIX = '_nav_post_processed.bil'

#: Order of bands in BIL file exported by aplnav
APL_POST_PROCESSED_NAV_BANDS = {'Time' : 1,
                                'Latitude' : 2,
                                'Longitude': 3,
                                'Altitude': 4,
                                'Roll' : 5,
                                'Pitch' : 6,
                                'Heading' : 7}

#: Default sensor to get view vectors for when calculating DEM size.
DEFAULT_SENSOR_VIEW_VECTORS = get_config_fallback(config, 'hyperspectral','DEFAULT_SENSOR_VIEW_VECTORS',fallback='eagle')

#: Maximum view vector (in degrees) for hyperspectral data. Value from Eagle (2013).
HYPERSPECTRAL_VIEW_ANGLE_MAX = float(get_config_fallback(config, 'hyperspectral', 'HYPERSPECTRAL_VIEW_ANGLE_MAX',fallback=18.6))

# Set paths for other libraries
#: Path to SPDLib binaries
SPDLIB_BIN_PATH = get_config_fallback(config,'spdlib','SPDLIB_BIN_PATH',fallback='')
#: Default interpolation used by SPDLib
SPD_DEFAULT_INTERPOLATION = get_config_fallback(config,'spdlib','SPD_DEFAULT_INTERPOLATION',
                     fallback='NATURAL_NEIGHBOR')

#: Path to open source LAStools binaries
LASTOOLS_FREE_BIN_PATH = get_config_fallback(config,'lastools','LASTOOLS_FREE_BIN_PATH',fallback=get_lastools_path())
#: Path to commercial LAStools binaries
LASTOOLS_NONFREE_BIN_PATH = get_config_fallback(config,'lastools','LASTOOLS_NONFREE_BIN_PATH',fallback=get_lastools_path())
