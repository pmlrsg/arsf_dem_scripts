#Author: Dan Clewley (dac)
#Created On: 06/10/2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
General utilities for working with LiDAR data to perform common tasks.

Available functions:

* create_patched_lidar_mosaic - Create mosaic from lidar data and patch with another DEM.
* create_lidar_mosaic - Create mosaic from lidar data.
* get_lidar_buffered_bb - buffer bounding box by 'DEFAULT_LIDAR_DEM_BUFFER' or user specified buffer.
* get_lidar_outline_polygon - creates polygon with outline of lidar line.

"""
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import sys
import glob
import tempfile

from .. import dem_common
from .. import dem_utilities
from .. import dem_nav_utilities
from .. import dem_common_functions

from . import grass_lidar
from .. import grass_library

# Import GRASS
sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)
try:
    import grass.script as grass
except ImportError as err:
    raise ImportError("Could not import grass library. Try setting "
                      "'GRASS_PYTHON_LIB_PATH' environmental variable.")


def create_patched_lidar_mosaic(in_lidar,
                     outdem,
                     in_lidar_projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                     resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                     lidar_format='LAS',
                     out_projection=None,
                     screenshot=None,
                     shaded_relief_screenshots=False,
                     out_raster_type='DSM',
                     dem_source=None,
                     dem_mosaic=None,
                     project='.',
                     nav=None,
                     lidar_bounds=True,
                     fill_lidar_nulls=False):

    """
    Create patched mosaic of lidar files and optionally an additional DEM to fill
    in gaps.

    Can also take a raster mosaic of LiDAR data and patch with a DEM.

    Used by the command line script 'create_dem_from_lidar.py'

    Arguments:

    * in_lidar - list or directory of lidar files. Can also provide a gridded raster as input.
    * outdem - output DEM.
    * in_lidar_projection - projection of input lidar files.
    * resolution - resolution to use when creating rasters from lidar files.
    * lidar_format - format of lidar data (LAS / ASCII / GRIDDED).
    * out_projection - output projection of DEM.
    * screenshot - directory / file for screenshots.
    * shaded_relief_screenshots - create shaded relief (hillshade) screenshots.
    * out_raster_type - Type of raster to generate (e.g., DTM, DSM)
    * dem_source - source of DEM to patch with lidar (ASTER / NEXTMAP).
    * dem_mosaic - dem mosaic to patch with lidar (if not using standard mosaics).
    * project - project directory, used to calculated DEM bounds for APL.
    * nav - path to navigation data file.
    * lidar_bounds - create patched DEM using lidar bounds plus buffer (for when hyperspectral navigation data is not available.
    * fill_lidar_nulls - fill null values in lidar data.

    """

    # Set up list to hold temp files
    temp_file_list = []
    temp_file_handler_list = []

    try:
        # Check output directory exists. Will raise exception if not accessible
        dem_common_functions.CheckPathExistsAndIsWritable(
                                   os.path.split(os.path.abspath(outdem))[0])

        # Input projection for lidar files
        in_lidar_projection = in_lidar_projection.upper()

        # Set output projection - if not provided assume
        # the same as input.
        if out_projection is None:
            out_patched_projection = in_lidar_projection
        else:
            out_patched_projection = out_projection

        # If lidar is in UKBNG and output is not UKBNG need to apply vertical datum
        # offset.
        # If not UKBNG (likely UTM) assume no vertical shift is required
        if in_lidar_projection == 'UKBNG' and out_patched_projection != 'UKBNG':
            lidar_separation_file = dem_common.UKBNG_SEP_FILE_UKBNG
            lidar_separation_file_is_ascii = dem_common.UKBNG_SEP_FILE_UKBNG_IS_ASCII
        else:
            lidar_separation_file = None
            lidar_separation_file_is_ascii = False

        # Check if we want to patch with a DEM (default is not)
        patch_with_dem = False

        # ASTER DEM
        if (dem_source is not None) and (dem_source.upper() == 'ASTER'):
            in_dem_mosaic = dem_common.ASTER_MOSAIC_FILE
            in_dem_mosaic_projection = 'WGS84LL'
            # If relative to UKBNG is required apply seperate
            # shift file equal to (EGM96 to WGS-84) - (UKBNG to WGS-84)
            if out_patched_projection == 'UKBNG':
                separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84
                ascii_separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84_IS_ASCII
            # Else shift to WGS-84 vertical datum
            else:
                separation_file = dem_common.WWGSG_FILE
                ascii_separation_file = dem_common.WWGSG_FILE_IS_ASCII
            patch_with_dem = True

        # NEXTMap DEM
        elif (dem_source is not None) and (dem_source.upper() == 'NEXTMAP'):
            in_dem_mosaic = dem_common.NEXTMAP_MOSAIC_FILE
            in_dem_mosaic_projection = 'UKBNG'
            # If output projection if UKBNG no vertical shift is required
            if out_patched_projection == 'UKBNG':
                separation_file = None
                ascii_separation_file = False
            # Else shift to WGS-84 vertical datum
            else:
                separation_file = dem_common.UKBNG_SEP_FILE_WGS84
                ascii_separation_file = dem_common.UKBNG_SEP_FILE_WGS84_IS_ASCII
            patch_with_dem=True

        # SRTM DEM
        elif (dem_source is not None) and (dem_source.upper() == 'SRTM'):
            in_dem_mosaic = dem_common.SRTM_MOSAIC_FILE
            in_dem_mosaic_projection = 'WGS84LL'
            # If relative to UKBNG is required apply seperate
            # shift file equal to (EGM96 to WGS-84) - (UKBNG to WGS-84)
            if out_patched_projection == 'UKBNG':
                separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84
                ascii_separation_file = dem_common.EGM96_UKBNG_SEP_FILE_WGS84_IS_ASCII
            # Else shift to WGS-84 vertical datum
            else:
                separation_file = dem_common.WWGSG_FILE
                ascii_separation_file = dem_common.WWGSG_FILE_IS_ASCII
            patch_with_dem = True

        # Custom DEM
        elif dem_mosaic is not None:
            in_dem_mosaic = dem_mosaic
            in_dem_mosaic_projection = grass_library.getGRASSProjFromGDAL(dem_mosaic)
            separation_file = None
            ascii_separation_file = False
            patch_with_dem = True

        # Check if patched DEM should be subset to navigation or based on the DEM mosaic
        subset_to_navigation = False
        if patch_with_dem:
            if (project != ".") or (nav is not None) or not lidar_bounds:
                # If any of these options are set probably want to subset to hyperspectral
                subset_to_navigation = True
            else:
                subset_to_navigation = False

        # Create temp file for DEM (if required)
        tmd_fh, temp_mosaic_dem = tempfile.mkstemp(prefix='dem_subset',suffix='.dem', dir=dem_common.TEMP_PATH)
        temp_mosaic_dem_header = os.path.splitext(temp_mosaic_dem)[0] + '.hdr'
        tld_fh, temp_lidar_dem = tempfile.mkstemp(prefix='lidar_dem_mosaic',suffix='.dem', dir=dem_common.TEMP_PATH)
        temp_lidar_dem_header = os.path.splitext(temp_lidar_dem)[0] + '.hdr'

        temp_file_list.extend([temp_mosaic_dem, temp_mosaic_dem_header, temp_lidar_dem, temp_lidar_dem_header])
        temp_file_handler_list.extend([tmd_fh, tld_fh])

        lidar_dem_mosaic = outdem
        lidar_dem_mosaic_header = os.path.splitext(lidar_dem_mosaic)[0] + '.hdr'
        outdem_header = os.path.splitext(outdem)[0] + '.hdr'

        # If a single file is provided for the screenshot and patching with a DEM
        # want screenshot of patched DEM not lidar.
        if (screenshot is not None and not os.path.isdir(screenshot)) and patch_with_dem:
            lidar_screenshots = None
        else:
            lidar_screenshots = screenshot

        if patch_with_dem and out_raster_type.upper() not in ['DSM','DTM','DEM']:
            raise Exception('Output type must be DSM or DTM to patch with another DEM')

        if patch_with_dem and fill_lidar_nulls:
            dem_common_functions.WARNING('Skipping filling NULL values in LiDAR data by interpolation as patching with DEM')
            fill_lidar_nulls = False

        if lidar_format.upper() != 'GRIDDED':
            # Create DEM from individual lidar lines and patch together
            # If a string is passed in convert to a list
            if isinstance(in_lidar, str):
                in_lidar = [in_lidar]

            create_lidar_mosaic(in_lidar,lidar_dem_mosaic,
                                out_screenshot=lidar_screenshots,
                                shaded_relief_screenshots=shaded_relief_screenshots,
                                in_projection=in_lidar_projection,
                                resolution=resolution,
                                nodata=dem_common.NODATA_VALUE,
                                lidar_format=lidar_format,
                                raster_type=out_raster_type,
                                fill_nulls=fill_lidar_nulls)

        else:
            if isinstance(in_lidar, list):
                if len(in_lidar) == 1:
                    lidar_dem_mosaic = in_lidar[0]
                else:
                    raise Exception('Multiple gridded lidar files are not currently'
                                    'supported. Mosaic them first')
            else:
                lidar_dem_mosaic = in_lidar
            # Check GDAL can open dataset (will raise exception if not)
            dem_utilities.check_gdal_dataset(lidar_dem_mosaic)

            print('')
            dem_common_functions.PrintTermWidth('Using existing LiDAR mosaic',
                                                padding_char='*')
            print('')

        # Check if input projection is equal to output projection
        if in_lidar_projection != out_patched_projection:
            dem_utilities.call_gdalwarp(lidar_dem_mosaic, temp_lidar_dem,
                   s_srs=grass_library.grass_location_to_proj4(in_lidar_projection),
                   t_srs=grass_library.grass_location_to_proj4(out_patched_projection))

            # Get no data value from LiDAR
            lidar_mosaic_nodata = dem_utilities.get_nodata_value(lidar_dem_mosaic)
            if lidar_dem_mosaic is None:
                lidar_mosaic_nodata = dem_common.NODATA_VALUE
            # Check if a vertical datum shift is required.
            # At the moment only consider UKBNG to WGS84LL
            if in_lidar_projection == 'UKBNG' and out_patched_projection == 'WGS84LL':
                print('Applying vertical offset to LiDAR mosaic')
                # Get nodata value for mosaic
                # Apply offset
                dem_utilities.offset_null_fill_dem(temp_lidar_dem, temp_lidar_dem,
                                                   import_to_grass=True,
                                                   separation_file=dem_common.UKBNG_SEP_FILE_WGS84,
                                                   ascii_separation_file=dem_common.UKBNG_SEP_FILE_WGS84_IS_ASCII,
                                                   fill_nulls=False,
                                                   nodata=lidar_mosaic_nodata,
                                                   remove_grassdb=False)
            # If the LiDAR data has a different nodata value replace - save
            # using two different values for LiDAR and ASTER mosaic
            # Applying vertical offset will automatically do this.
            elif patch_with_dem and lidar_mosaic_nodata != dem_common.NODATA_VALUE:
                print('Replacing no data values of {} with '
                      '{}'.format(lidar_mosaic_nodata, dem_common.NODATA_VALUE))
                dem_utilities.replace_nodata_val(temp_lidar_dem, temp_lidar_dem,
                                                 import_to_grass=True,
                                                 innodata=lidar_mosaic_nodata,
                                                 outnodata=dem_common.NODATA_VALUE,
                                                 remove_grassdb=False)
            lidar_dem_mosaic = temp_lidar_dem

        if patch_with_dem:
            print('')
            dem_common_functions.PrintTermWidth('Patching with {}'.format(in_dem_mosaic), padding_char='*')
            print('')
            subset_to_nav_failed = False
            if subset_to_navigation:
                try:
                    # Subset DEM
                    dem_nav_utilities.subset_dem_to_nav(in_dem_mosaic, temp_mosaic_dem,
                                      nav, project,
                                      separation_file=separation_file,
                                      ascii_separation_file=ascii_separation_file,
                                      in_dem_projection=grass_library.grass_location_to_proj4(in_dem_mosaic_projection),
                                      out_projection=grass_library.grass_location_to_proj4(out_patched_projection),
                                      nodata=dem_common.NODATA_VALUE,
                                      out_res=resolution,
                                      remove_grassdb=True,
                                      fill_nulls=True)
                except Exception as err:
                    dem_common_functions.ERROR('Could not subset DEM to navigation data.\n{}.'.format(err))
                    dem_common_functions.WARNING('Will try to subset using lidar bounds, coverage of DEM might not be sufficient for hyperspectral processing')
                    subset_to_nav_failed = True

            if not subset_to_navigation or (subset_to_navigation and subset_to_nav_failed):
                print('Getting bounding box from LiDAR mosaic')
                # Get bounding box from output lidar mosaic
                lidar_bb = dem_utilities.get_gdal_dataset_bb(lidar_dem_mosaic,
                                                             output_ll=True)
                buffered_lidar_bb = get_lidar_buffered_bb(lidar_bb)

                dem_utilities.subset_dem_to_bounding_box(in_dem_mosaic,
                                     temp_mosaic_dem,
                                     bounding_box=buffered_lidar_bb,
                                     separation_file=separation_file,
                                     ascii_separation_file=ascii_separation_file,
                                     in_dem_projection=grass_library.grass_location_to_proj4(in_dem_mosaic_projection),
                                     out_projection=grass_library.grass_location_to_proj4(out_patched_projection),
                                     nodata=dem_common.NODATA_VALUE,
                                     out_res=resolution,
                                     remove_grassdb=True,
                                     fill_nulls=True)

            dem_utilities.patch_files([lidar_dem_mosaic, temp_mosaic_dem],
                        out_file=outdem,
                        import_to_grass=True,
                        nodata=dem_common.NODATA_VALUE,
                        projection=out_patched_projection,
                        grassdb_path=None,
                        remove_grassdb=True)

        # Check if file was reprojected but not patched (if so need to move from temp file)
        elif in_lidar_projection != out_patched_projection:
            shutil.move(lidar_dem_mosaic,outdem)
            shutil.move(lidar_dem_mosaic_header,outdem_header)

        # Try to export screenshot if path or file is provided.
        # Only needed if patching with DEM, else will have been done earlier.
        if patch_with_dem:
            try:
                if (screenshot is not None) and not os.path.isdir(screenshot):
                    dem_utilities.export_screenshot(outdem, screenshot,shaded_relief=shaded_relief_screenshots)
                elif os.path.isdir(screenshot):
                    mosaic_screenshot = dem_utilities.get_screenshot_path(outdem, screenshot)
                    dem_utilities.export_screenshot(outdem, mosaic_screenshot, shaded_relief=shaded_relief_screenshots)
            except TypeError:
                pass

        # Add metadata to DEM header
        patched_dem_source = 'LiDAR'

        if patch_with_dem:
            patched_dem_source = 'LiDAR/{}'.format(dem_source)

        dem_utilities.add_dem_metadata(outdem, dem_source=patched_dem_source,
                                       other_items={'Type' : out_raster_type})

        # Remove temp files created
        for temp_handler in temp_file_handler_list:
            os.close(temp_handler)
        for temp_file in temp_file_list:
            if os.path.isfile(temp_file):
                os.remove(temp_file)

    except KeyboardInterrupt:
        # Remove temp files created
        for temp_handler in temp_file_handler_list:
            os.close(temp_handler)
        for temp_file in temp_file_list:
            if os.path.isfile(temp_file):
                os.remove(temp_file)
        raise

    except Exception as err:
        # Remove temp files created
        for temp_handler in temp_file_handler_list:
            os.close(temp_handler)
        for temp_file in temp_file_list:
            if os.path.isfile(temp_file):
                os.remove(temp_file)
        raise

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
       * INTENSITY - Intensity image.

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
            dem_common_functions.WARNING('Creating shaded relief screenshots makes no sense with intensity images. Ignoring')
            shaded_relief_screenshots = False
    else:
        raise Exception('raster_type "{}" was not recognised'.format(raster_type))

    # Set output type and data format for output rasters
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
                              os.path.join(in_lidar_files[0],'*[Ll][Aa][Ss]'))
            in_lidar_files_list.extend(glob.glob(
                              os.path.join(in_lidar_files[0],'*[Ll][Aa][Zz]')))

        # If ASCII format or not las files found check for txt files
        if lidar_format.upper() == 'ASCII' or len(in_lidar_files_list) == 0:
            in_lidar_files_list = glob.glob(
                              os.path.join(in_lidar_files[0],'*txt'))
            if len(in_lidar_files_list) != 0:
                lidar_format = 'ASCII'
    # Check if wild character has been passed in which wasn't expanded (e.g., on windows)
    # or no matching files were found (which will raise exception later).
    elif in_lidar_files[0].find('*') > -1:
        in_lidar_files_list = glob.glob(in_lidar_files[0])
    else:
        in_lidar_files_list = in_lidar_files
        if os.path.splitext(in_lidar_files_list[0])[-1].lower() != '.las' \
          and os.path.splitext(in_lidar_files_list[0])[-1].lower() != '.laz':
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
        dem_common_functions.PrintTermWidth('Creating LiDAR Mosaic from {} lines'.format(len(in_lidar_files_list)),padding_char='*')
    else:
        dem_common_functions.PrintTermWidth('Creating LiDAR raster for a single line',padding_char='*')
    print('')

    for in_lidar_file in in_lidar_files_list:
        dem_common_functions.PrintTermWidth('Creating {0} raster from "{1}" ({2}/{3})'.format(raster_type,os.path.split(in_lidar_file)[-1],linenum, totlines))
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
                                       out_raster_type=out_raster_type,
                                       projection=in_projection,
                                       grassdb_path=grassdb_path,
                                       remove_grassdb=False)
        print('Tiles patched OK')
    else:
        patched_name = raster_names[0]

    # Fill null values
    if fill_nulls:
        patched_name, grassdb_path = dem_utilities.offset_null_fill_dem(patched_name, out_mosaic,
                                      import_to_grass=False,
                                      separation_file=None,
                                      ascii_separation_file=False,
                                      fill_nulls=fill_nulls,
                                      nodata=nodata,
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

def get_lidar_outline_polygon(in_lidar_file,
                              out_polygon,
                              in_lidar_projection=dem_common.DEFAULT_LIDAR_PROJECTION_GRASS,
                              resolution=100,
                              lidar_format='LAS',
                              out_format='GeoJSON'):
    """
    Creates a polygon representing the outline of a LiDAR point cloud file.

    Grids LiDAR file, converts to mask and then generates a polygon from this.
    The polygon is smoothed using 'v.generalize'.

    Arguments:

    * in_lidar_file - Input LiDAR file
    * out_polygon - Output polygon
    * in_lidar_projection - Projection of LiDAR file
    * resolution - Resolution to grid LiDAR using
    * lidar_format - format of lidar data (LAS / ASCII).
    * out_format - OGR format for output polygon (e.g., KML, ESRI Shapefile)

    """

    mask_name = 'lidar_mask'
    vector_name = 'ldar_mask_poly'
    smoothed_vector_name = 'lidar_mask_poly_smooth'

    # Rasterise LiDAR file
    if lidar_format.upper() == 'LAS':
        out_raster_name, grassdb_path = grass_lidar.las_to_raster(
                 in_lidar_file,
                 out_raster=None,
                 remove_grassdb=False,
                 projection=in_lidar_projection,
                 bin_size=resolution)
    elif lidar_format.upper() == 'ASCII':
        out_raster_name, grassdb_path = grass_lidar.ascii_to_raster(
                 in_lidar_file,
                 out_raster=None,
                 remove_grassdb=False,
                 projection=in_lidar_projection,
                 bin_size=resolution)
    else:
        raise Exception('Input LiDAR format not recognised')

    # Convert  to mask
    grass.mapcalc('{mask}=if({lidar} != {nodata}'
                  ',1,0)'.format(mask=mask_name, lidar=out_raster_name,
                                 nodata=dem_common.NODATA_VALUE))

    if not grass_library.checkFileExists(mask_name):
        raise Exception('Could not create mask')

    # Convert to polygon
    grass.run_command('r.to.vect',
                      input=mask_name,
                      output=vector_name,
                      feature='area')

    # Smooth polygon
    grass.run_command('v.generalize',
                      input=vector_name,
                      output=smoothed_vector_name,
                      method='snakes', threshold=1000)

    # Export
    grass.run_command('v.out.ogr',
                      input=smoothed_vector_name,
                      dsn=out_polygon,
                      type='area',
                      format=out_format)

    if not os.path.isfile(out_polygon):
        raise Exception('Could not create output polygon')

    shutil.rmtree(grassdb_path)
