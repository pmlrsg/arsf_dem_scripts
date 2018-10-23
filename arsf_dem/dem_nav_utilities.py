#! /usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created on: 05 November 2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
Utilities for working with DEMs and navigation data, mostly for creating DEMs
suitible for use in APL for processing hyperspectral data.

Available Functions:

* create_apl_dem_from_mosaic - function to create DEM for use in APL using standard or custom DEM mosaic.
* subset_dem_to_nav - subset DEM to navigation data.
* subset_dem_to_apl_nav_files - subset DEM to post-processed BIL format navigation files
* get_bb_from_bil_nav_files - get bounding box from BIL format navigation files (used by subset_dem_to_apl_nav_files)
* get_min_max_from_bil_nav_files - gets minimum and maximum for each band in BIL format navigation files (used by get_bb_from_bil_nav_files)

Known issues

Functions to get a bounding box from navigation data can produce a bounding box
which is much larger than required if .sol file isn't found from project.
If this happens a warning will be printed.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import glob
import math

# Import arsf_dem files
from . import dem_common
from . import dem_utilities
from . import dem_common_functions

# Check DEM library is available
# this is only used on ARSF systems
HAVE_DEM_LIBRARY = True
try:
    import dem_library
except ImportError as err:
    HAVE_DEM_LIBRARY = False

# Try to import GDAL
HAVE_GDAL=True
try:
    from osgeo import gdal
except ImportError:
    # If can't import don't complain until GDAL is actually needed
    HAVE_GDAL=False

# Additional buffer to apply to post processed DEM files as the extent is
# smaller than the one produced by APL.
POST_PROCESSED_DEM_BUFFER = 0.03

def create_apl_dem_from_mosaic(outdem,
                               dem_source=None,
                               dem_mosaic=None,
                               separation_file=None,
                               project='.',
                               nav=None,
                               bil_navigation=None,
                               fill_nulls=True,
                               remove_grassdb=True,
                               grassdb_path=None):
    """
    Create DEM subset for use in APL from standard or custom DEM

    Used by script 'create_apl_dem.py'

    dem_source options are:

    * 'ASTER'
    * 'NEXTMAP'
    * 'SRTM'

    Arguments:

    * outdem - Output DEM file.
    * dem_source - Source of DEM.
    * dem_mosaic - Path to DEM if not using standard DEM.
    * separation_file - Path to separation file to use for non-standard DEM.
    * project - Base name of project (used to get navigation data).
    * nav - Path to sbet / sol navigation file.
    * bil_navigation - Directoy containing APL processed BIL format navigation files.
    * fill_nulls - fill NULL values (needed for use in APL).
    * remove_grassdb - Remove GRASS database after processing is complete.

    """
    # ASTER DEM
    if (dem_source is not None) and (dem_source.upper() == 'ASTER'):
        in_dem_mosaic = dem_common.ASTER_MOSAIC_FILE
        in_dem_projection = dem_common.WGS84_PROJ4_STRING
        separation_file = dem_common.WWGSG_FILE
        ascii_separation_file = dem_common.WWGSG_FILE_IS_ASCII
        out_res = dem_common.ASTER_RES_DEGREES

    # NEXTMap DEM
    elif (dem_source is not None) and (dem_source.upper() == 'NEXTMAP'):
        in_dem_mosaic = dem_common.NEXTMAP_MOSAIC_FILE
        in_dem_projection = dem_common.OSTN02_PROJ4_STRING
        separation_file = dem_common.UKBNG_SEP_FILE_WGS84
        ascii_separation_file = dem_common.UKBNG_SEP_FILE_WGS84_IS_ASCII
        out_res = dem_common.NEXTMAP_RES_DEGREES
        if not os.path.isfile(dem_common.OSTN02_NTV2_BIN_FILE):
            raise Exception("Could not find OSTN02 transform file.\nChecked {}".format(dem_common.OSTN02_NTV2_BIN_FILE))

    # SRTM DEM
    elif (dem_source is not None) and (dem_source.upper() == 'SRTM'):
        in_dem_mosaic = dem_common.SRTM_MOSAIC_FILE
        in_dem_projection = dem_common.WGS84_PROJ4_STRING
        separation_file = dem_common.WWGSG_FILE
        ascii_separation_file = dem_common.WWGSG_FILE_IS_ASCII
        out_res = dem_common.SRTM_RES_DEGREES

    # Custom DEM
    elif dem_mosaic is not None:
        in_dem_mosaic = dem_mosaic
        in_dem_projection = None
        if separation_file is not None and \
        (os.path.splitext(separation_file)[-1] == '.dem' or os.path.splitext(separation_file)[-1] == '.bil'):
            ascii_separation_file = False
        else:
            ascii_separation_file = True
        out_res = None
        if dem_source is None:
            dem_source = 'DEM'

    else:
        raise Exception('DEM Source not recognised and no custom DEM supplied.')

    # If a name for the output DEM is not provided and don't require the output to be
    # kept in GRASS, try to figure out standard name
    # The standard names only makes sense on ARSF systems and it depends on a
    # module which isn't part of arsf_dem.
    if outdem is None and remove_grassdb:
        if not HAVE_DEM_LIBRARY:
            raise Exception('A name for the output DEM was not supplied and' +
                        ' the dem_library could not be imported to determine the standard' +
                        ' ARSF DEM name and path from the project.\nPlease supply a name for the DEM')
        else:
            outdem = dem_library.getAplDemName(project, dem_source)
            print('Saving DEM to: {}'.format(outdem))

    if bil_navigation is not None:
        dem_common_functions.PrintTermWidth('Using post processed navigation data from {}'.format(bil_navigation))
        out_demfile, grassdb_path = subset_dem_to_apl_nav_files(in_dem_mosaic,
                                       outdem,
                                       bil_navigation,
                                       separation_file=separation_file,
                                       ascii_separation_file=ascii_separation_file,
                                       in_dem_projection=in_dem_projection,
                                       out_res=out_res,
                                       nodata=-9999,
                                       remove_grassdb=remove_grassdb,
                                       grassdb_path=grassdb_path,
                                       fill_nulls=fill_nulls)

    else:
        dem_common_functions.PrintTermWidth('Using navigation data for project {}'.format(project))
        # Set nodata to -9999 so an offset is also applied to pixels with a value of 0
        out_demfile, grassdb_path = subset_dem_to_nav(in_dem_mosaic,
                             outdem,
                             nav, project,
                             separation_file=separation_file,
                             ascii_separation_file=ascii_separation_file,
                             in_dem_projection=in_dem_projection,
                             out_res=out_res,
                             nodata=-9999,
                             remove_grassdb=remove_grassdb,
                             grassdb_path=grassdb_path,
                             fill_nulls=fill_nulls)

    # Add metadata to DEM header (if output file was requested)
    if outdem is not None:
        dem_utilities.add_dem_metadata(outdem, dem_source=dem_source,
                                       dem_filename=os.path.basename(in_dem_mosaic))

    return out_demfile, grassdb_path


def subset_dem_to_nav(in_dem_mosaic, out_demfile,
                      nav_file, project_dir,
                      max_view_angle=dem_common.HYPERSPECTRAL_VIEW_ANGLE_MAX,
                      sensor=None,
                      separation_file=None,
                      ascii_separation_file=False,
                      in_dem_projection=None,
                      out_projection=None,
                      out_res=None,
                      nodata=dem_common.NODATA_VALUE,
                      remove_grassdb=True,
                      grassdb_path=None,
                      fill_nulls=True):
    """
    Subsets DEM to bounding box obtained from navigation data
    to produce a DEM for use in aplcorr by calling:

    dem_utilities.subset_dem_to_bounding_box

    Can also supply output projection for patching with another DEM (e.g., from LiDAR).
    Note, supplying an output projection will make the resulting DEM incompatible with
    APL.

    If projections are supplied must use Proj4 format, can convert
    between GRASS style (e.g., UKBNG) using::

       grass_library.grass_location_to_proj4('UKBNG')

    The navigation data to use is determined from the project directory, and the maximum
    bounding box over all lines is taken.
    The swath width is determined using either a maximum view angle (max_view_angle) or by
    reading in the most recent view vectors for a provided sensor and taking the maximum value.

    Arguments:

    * in_dem_mosaic - Mosaic of large DEM to subset, can be anything GDAL can read (including a virtual raster file).
    * out_demfile - Output DEM.
    * nav_file - Navigation file (.sbet).
    * project_dir - Directory of project.
    * max_view_angle - Maximum view angle of sensor, used for calculating DEM size from navigation data.
    * sensor - Sensor to take view vectors from and calculate maximum view angle.
    * separation_file - Datum offset fill to add to heights.
    * ascii_separation_file - Bool to specify is separation file is ASCII format.
    * in_dem_projection - Input projection of DEM mosaic (Proj4 format)
    * out_projection - Output projection if not WGS84LL. Warning setting this will make the DEM incompatible with APL.
    * out_res - Out resolution e.g., (0.002,0.002) if not supplied gdalwarp will determine based on input resolution.
    * nodata - No data value.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one.
    * fill_nulls - fill null values.

    Returns:

    * out_demfile
    * grassdb_path (None if remove_grassdb = True)

    """
    if not HAVE_DEM_LIBRARY:
        raise ImportError('Could not import dem_library. If this is an ARSF computer check "PYTHONPATH".\n' +
                          'If not try using "subset_dem_to_apl_nav_files" as this uses bil files with processed navigation data ' +
                          ' and does not require the dem_library')

    # Get bounding box from navigation data
    print('Getting bounding box from navigation data')

    nav_bb, project_info_used = dem_library.getAplCal(project_dir, nav_file,
                                                      max_view_angle=max_view_angle,
                                                      sensor=sensor)

    # Calculate difference between selected buffer and one already applied in
    # dem_library
    nav_bb[0] = nav_bb[0] - (dem_common.DEFAULT_APL_DEM_BUFFER['S'] - dem_library.getDemCalBuffer())
    nav_bb[1] = nav_bb[1] + (dem_common.DEFAULT_APL_DEM_BUFFER['N'] - dem_library.getDemCalBuffer())
    nav_bb[2] = nav_bb[2] - (dem_common.DEFAULT_APL_DEM_BUFFER['W'] - dem_library.getDemCalBuffer())
    nav_bb[3] = nav_bb[3] + (dem_common.DEFAULT_APL_DEM_BUFFER['E'] - dem_library.getDemCalBuffer())

    if not project_info_used:
        dem_common_functions.WARNING('Could not find project from directory "{}".'.format(os.path.abspath(project_dir)))
        if nav_file is None:
            raise Exception('Could not find project and no navigiation data supplied')
        else:
            dem_common_functions.WARNING('Will subset DEM to bounds of "{}"'.format(nav_file))
            dem_common_functions.WARNING('This could result in a DEM which is much larger than required.')

    out_demfile, grassdb_path = dem_utilities.subset_dem_to_bounding_box(
                                           in_dem_mosaic,
                                           out_demfile,
                                           nav_bb,
                                           separation_file=separation_file,
                                           ascii_separation_file=ascii_separation_file,
                                           in_dem_projection=in_dem_projection,
                                           out_projection=out_projection,
                                           out_res=out_res,
                                           nodata=nodata,
                                           remove_grassdb=remove_grassdb,
                                           grassdb_path=grassdb_path,
                                           fill_nulls=fill_nulls)

    return out_demfile, grassdb_path

def subset_dem_to_apl_nav_files(in_dem_mosaic,
                                out_demfile,
                                nav_files,
                                separation_file=None,
                                ascii_separation_file=False,
                                in_dem_projection=None,
                                out_projection=None,
                                out_res=None,
                                nodata=dem_common.NODATA_VALUE,
                                remove_grassdb=True,
                                grassdb_path=None,
                                fill_nulls=True):
    """
    Subsets DEM to bounding box obtained from navigation files produced by aplnav
    to produce a DEM for use in aplcorr by calling:

    dem_utilities.subset_dem_to_bounding_box

    If projections are supplied must use Proj4 format, can convert
    between GRASS location style (e.g., UKBNG) using::

       grass_library.grass_location_to_proj4('UKBNG')

    For ARSF internal processing subset_dem_to_nav should generally be used as
    a) the DEM needs to be created before any APL commands are run
    b) raw navigation data is available

    For creating a DEM for delivered data where BIL format post processed navigation files are
    available this function should be used.

    Arguments:

    * in_dem_mosaic - Mosaic of large DEM to subset, can be anything GDAL can read (including a virtual raster file).
    * out_demfile - Output file.
    * nav_files - Single navigation file, list of navigation files or directory containing navigation data (.bil format)
    * separation_file - Datum offset fill to add to heights.
    * ascii_separation_file - Bool to specify is separation file is ASCII format.
    * in_dem_projection - Input projection of DEM mosaic (Proj4 format)
    * out_projection - Output projection if not WGS84LL. Warning setting this will make the DEM incompatible with APL.
    * out_res - Out resolution e.g., (0.002,0.002) if not supplied gdalwarp will determine based on input resolution.
    * nodata - No data value.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one.
    * fill_nulls - fill null values.

    Returns:

    * out_demfile
    * grassdb_path (None if remove_grassdb = True)

    """

    # Get bounding box from navigation data
    print('Getting bounding box from navigation data')

    nav_bb = get_bb_from_bil_nav_files(nav_files)

    out_demfile, grassdb_path = dem_utilities.subset_dem_to_bounding_box(
                                           in_dem_mosaic,
                                           out_demfile,
                                           nav_bb,
                                           separation_file=separation_file,
                                           ascii_separation_file=ascii_separation_file,
                                           in_dem_projection=in_dem_projection,
                                           out_projection=out_projection,
                                           out_res=out_res,
                                           nodata=nodata,
                                           remove_grassdb=remove_grassdb,
                                           grassdb_path=grassdb_path,
                                           fill_nulls=fill_nulls)

    return out_demfile, grassdb_path

def get_bb_from_bil_nav_files(nav_files):
    """
    Gets bounding box from bil format navigation files

    Arguments:

    * nav_files - input navigation file / list of files / directory

    Returns:

    * bounding box - [minY, maxY, minX, maxX]

    """

    nav_stats = get_min_max_from_bil_nav_files(nav_files)

    # Get swath width
    pos_swath_buffer = nav_stats['altitude']['max'] * \
                         math.tan(math.radians(nav_stats['roll']['max'] + dem_common.HYPERSPECTRAL_VIEW_ANGLE_MAX))
    neg_swath_buffer = nav_stats['altitude']['max'] * \
                         math.tan(math.radians(nav_stats['roll']['min'] + dem_common.HYPERSPECTRAL_VIEW_ANGLE_MAX))

    swath_buffer = pos_swath_buffer + neg_swath_buffer

    # Get latitude to use for metres to degrees conversion
    latitude = (nav_stats['latitude']['min'] + nav_stats['latitude']['max']) / 2.0

    swath_buffer_degrees = dem_utilities.m_to_deg(latitude, swath_buffer, swath_buffer)

    buffered_bb = []
    buffered_bb.append(nav_stats['latitude']['min'] - swath_buffer_degrees[1] \
                       - dem_common.DEFAULT_APL_DEM_BUFFER['S'] \
                       - POST_PROCESSED_DEM_BUFFER)
    buffered_bb.append(nav_stats['latitude']['max'] + swath_buffer_degrees[1] \
                       + dem_common.DEFAULT_APL_DEM_BUFFER['N'] \
                       + POST_PROCESSED_DEM_BUFFER)
    buffered_bb.append(nav_stats['longitude']['min'] - swath_buffer_degrees[0] \
                       - dem_common.DEFAULT_APL_DEM_BUFFER['W'] \
                       - POST_PROCESSED_DEM_BUFFER)
    buffered_bb.append(nav_stats['longitude']['max'] + swath_buffer_degrees[0] \
                       + dem_common.DEFAULT_APL_DEM_BUFFER['E'] \
                       + POST_PROCESSED_DEM_BUFFER)

    return buffered_bb

def get_min_max_from_bil_nav_files(nav_files):
    """
    Gets minimum and maximum values for single bil format navigation file or a list
    of bil format navigation files.

    Arguments:

    * nav_files - input navigation file / list of files / directory

    Returns:

    * dictionary with min / max for each parameter.

    """

    # GDAL is used for this function rather than the 'aplnavfiles' library as
    # it is expected this function will be largely used by ARSF users, as for internal use
    # the raw navigation data will be available.
    # Using GDAL reduces the ARSF specific dependencies required for the library.
    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL, check it is installed and available within PYTHONPATH')

    # If it's a string should a path or directory
    if isinstance(nav_files,str):
        if os.path.isfile(nav_files):
            nav_file_list = [nav_files]
        elif os.path.isdir(nav_files):
            nav_file_list = glob.glob(os.path.join(nav_files, '*' + dem_common.APL_POST_PROCESSED_NAV_SUFFIX))
            if len(nav_file_list) == 0:
                raise Exception('Could not find any files in "{}" matching "*{}"'.format(nav_files, dem_common.APL_POST_PROCESSED_NAV_SUFFIX))
        else:
            raise Exception('Could not find "{}". It is not an existing file or directory'.format(nav_files))

    # If it's a list, assume list of files
    elif isinstance(nav_files, list):
        nav_file_list = nav_files
        if len(nav_file_list) == 0:
            raise Exception('The list passed in was empty')
    else:
        raise Exception('Did not understand input, expected string or list')

    # Set up dictionary for output stats
    nav_stats = {}
    nav_stats['time'] = {'min' : None, 'max' : None}
    nav_stats['latitude'] = {'min' : None, 'max' : None}
    nav_stats['longitude'] = {'min' : None, 'max' : None}
    nav_stats['altitude'] = {'min' : None, 'max' : None}
    nav_stats['roll'] = {'min' : None, 'max' : None}
    nav_stats['pitch'] = {'min' : None, 'max' : None}
    nav_stats['heading'] = {'min' : None, 'max' : None}

    for nav_bil in nav_file_list:
        try:
            print('Reading {}'.format(nav_bil))
            dataset = gdal.Open(nav_bil, gdal.GA_ReadOnly)

            # Set up GDAL bands for each band
            time_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Time'])
            latitude_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Latitude'])
            longitude_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Longitude'])
            altitude_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Altitude'])
            roll_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Roll'])
            pitch_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Pitch'])
            heading_band = dataset.GetRasterBand(dem_common.APL_POST_PROCESSED_NAV_BANDS['Heading'])

            # Read to NumPy arrays, only dealing with small datasets
            # so loading all the bands to memory at once shouldn't cause any problems
            time = time_band.ReadAsArray()
            latitude = latitude_band.ReadAsArray()
            longitude = longitude_band.ReadAsArray()
            altitude = altitude_band.ReadAsArray()
            roll = roll_band.ReadAsArray()
            pitch = pitch_band.ReadAsArray()
            heading = heading_band.ReadAsArray()

            # Set up dictionary of numpy arrays
            # Use same keys as stats
            nav_data = {'time' : time,
                        'latitude' : latitude,
                        'longitude' : longitude,
                        'altitude' : altitude,
                        'roll' : roll,
                        'pitch' : pitch,
                        'heading' : heading}

            for key in nav_stats.keys():
                if nav_stats[key]['min'] is None:
                    nav_stats[key]['min'] = nav_data[key].min()
                elif nav_data[key].min() < nav_stats[key]['min']:
                    nav_stats[key]['min'] = nav_data[key].min()
                if nav_stats[key]['max'] is None:
                    nav_stats[key]['max'] = nav_data[key].max()
                elif nav_data[key].max() > nav_stats[key]['max']:
                    nav_stats[key]['max'] = nav_data[key].max()

            dataset = None

        except Exception as err:
            dem_common_functions.WARNING('Could not get bounds for {}\n{}'.format(nav_bil,err))

    return nav_stats
