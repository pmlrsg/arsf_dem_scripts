#!/usr/bin/env python
#
# dem_utilities
#
# Author: Dan Clewley (dac@pml.ac.uk)
# Created on: 05 November 2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
General DEM utility scripts. Most are built on GRASS but are designed to be used with an existing GRASS database (if data has already been imported) or independently and will import data as required.

Available functions:

* subset_dem_to_bounding_box - subsets DEM to bounding box, applies offset and fills null values.
* patch_files - patches files together.
* offset_null_fill_dem - apply elevation offset and fill null values in DEM.
* export_screenshot - exports JPEG format screenshot.
* get_gdal_dataset_bb - gets bounding box of GDAL readable dataset.
* buffer_bounding_box_proportion - buffer bounding box by proportion of extent.
* reproject_bounding_box - reprojects bounding box.
* call_gdaldem - calls gdaldem command.
* call_gdalwarp - calls gdalwarp command.
* reproject_bng_to_wgs84 - reprojects raster from UKBNG to WGS84LL.
* reproject_wgs84_to_bng - reprojects raster from WGS84LL to UKBNG.
* subset_to_bb - subsets raster to bounding box
* deg_to_m - converts pixel sizes / distances in degrees to metres.
* m_to_deg - converts pixel sizes in metres to degrees.
* get_screenshot_path - creates filename for screenshot.
* remove_gdal_aux_file - removes '.aux.xml' file created by GDAL.
* get_gdal_type_from_path - gets GDAL format string from file name.
* add_dem_metadata - adds metadata to DEM.
* check_gdal_dataset - checks a dataset can be opened using GDAL.
* get_nodata_value - gets the nodata value for a GDAL dataset
* set_nodata_value - sets the nodata value for a GDAL dataset

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import shutil
import subprocess
import tempfile
import numpy

# Import common files
from . import dem_common
from . import dem_common_functions
from . import grass_library
from . import get_gdal_drivers

# Import GRASS
sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)
try:
    import grass.script as grass
except ImportError as err:
    raise ImportError("Could not import grass library. "
                      "Try setting 'GRASS_PYTHON_LIB_PATH' environmental variable."
                      "\n{}".format(err))

# Try to import GDAL
HAVE_GDAL=True
try:
    from osgeo import gdal
    from osgeo import osr
except ImportError:
    # If can't import don't complain until GDAL is actually needed
    HAVE_GDAL=False

def offset_null_fill_dem(in_demfile, out_demfile=None,
                         import_to_grass=True,
                         separation_file=None,
                         ascii_separation_file=False,
                         subtract_seperation=False,
                         fill_nulls=False,
                         nodata=dem_common.NODATA_VALUE,
                         out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE,
                         projection=None,
                         remove_grassdb=True,
                         grassdb_path=None):
    """
    Applies elevation offset to DEM and/or fills null values
    using GRASS.

    Seperation file ('separation_file') is supplied as a GDAL
    or GRASS ASCII file in the same projection is 'in_demfile'.
    If the separation file is ASCII set 'ascii_separation_file'
    to True.

    Arguments:

    * in_demfile - Input DEM.
    * out_demfile - Output DEM, if 'None', won't export from GRASS
                    database.
    * separation_file - Datum offset fill to add to heights.
    * ascii_separation_file - Bool to specify is separation file is ASCII format.
    * subtract_seperation - subtract seperation file (default is to add).
    * fill_nulls - Null fill values
    * nodata - No data value
    * out_raster_type - GDAL datatype for output raster (e.g., Float32)
    * projection - Projection to use (e.g., UKBNG) if not supplied will get from 'in_demfile'.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one.

    Returns:

    * out_demfile path / out_demfile name in GRASS database
    * path to GRASS database / None

    Examples:

    1) Change vertical datum from EGM96 to WGS-84 for DEM in WGS84LL horizontal projection::

    from arsf_dem import dem_common
    from arsf_dem import dem_utilities

    in_dem = 'srtm_plymouth.dem'
    out_dem = 'srtm_plymouth_wgs84.dem'

    dem_utilities.offset_null_fill_dem(in_dem, out_dem,
                            separation_file=dem_common.WWGSG_FILE,
                            ascii_separation_file=dem_common.WWGSG_FILE_IS_ASCII)

    2) Change vertical datum from OSGB Newlyn to WGS84 for DEM in WGS84LL horizontal projection::

    from arsf_dem import dem_common
    from arsf_dem import dem_utilities

    in_dem = 'nextmap_plymouth_wgs84_newlyn.dem'
    out_dem = 'nextmap_plymouth_wgs84.dem'

    dem_utilities.offset_null_fill_dem(in_dem, out_dem,
                            separation_file=dem_common.UKBNG_SEP_FILE_WGS84)

    Note if the DEM needs horizontal and vertical reprojection can use the function reproject_bng_to_wgs84
    and set 'vertical_reproject=True'

    """

    # Set projection based on input file
    in_proj = None
    if projection is None:
        # If not importing to grass only a list of
        # names, not files.
        if import_to_grass:
            in_proj = grass_library.getGRASSProjFromGDAL(in_demfile)
        if in_proj is None:
            dem_common_functions.WARNING('No projection supplied and could not determine projection from any input files.')
            dem_common_functions.WARNING('Assuming "WGS84LL".')
            in_proj = 'WGS84LL'
    else:
        in_proj = projection

    # Get output format from file extension
    if out_demfile is not None:
        out_raster_format = get_gdal_type_from_path(out_demfile)
    else:
        out_raster_format = dem_common.GDAL_OUTFILE_FORMAT

    if grassdb_path is None and not import_to_grass:
        raise Exception('No "grassdb_path" supplied but "import_to_grass" set to False.' +
                          'If file is already in GRASS supply path, else set "import_to_grass" to True')

    # Set up grass path
    if grassdb_path is None:
        grassdb_path = grass_library.grassDBsetup()
    else:
        location = projection
        mapset   = 'PERMANENT'
        grass.setup.init(dem_common.GRASS_LIB_PATH,
                    grassdb_path,
                    location,
                    mapset)

    grass_library.setLocation(in_proj)

    # Import DEM into GRASS
    demname = os.path.basename(in_demfile).replace("-","_")

    print('Importing DEM')
    if import_to_grass:
        grass.run_command('r.external',
                    input = in_demfile,
                    output=demname,
                    flags='e',
                    overwrite=True)

    else:
        demname = in_demfile

    # Check file exists
    if not grass_library.checkFileExists(demname):
        raise Exception('Could not find {} in GRASS database'.format(demname))

    # Set region
    grass_library.SetRegion(rast=demname)

    # Import separation file
    if separation_file is not None:
        print('Importing separation file')
        separation_name = os.path.split(separation_file)[-1]
        print('Using separation file: {}'.format(separation_file))
        if ascii_separation_file:
            grass.run_command('r.in.ascii',
                        input=separation_file,
                        output=separation_name,
                        overwrite=True)
        else:
            grass.run_command('r.external',
                  input=separation_file,
                  output=separation_name,
                  overwrite=True)

        if not grass_library.checkFileExists(separation_name):
            raise Exception('Could not import {}'.format(separation_file))

        # Add offset
        elevated_name = 'patched_elevated'
        if subtract_seperation:
            print('Subtracting offset')
            grass.mapcalc('{0}=if({1} != {3},{1}-{2},0)'.format(elevated_name,demname,separation_name,nodata),
                                 overwrite=True)

        else:
            print('Adding offset')
            grass.mapcalc('{0}=if({1} != {3},{1}+{2},0)'.format(elevated_name,demname,separation_name, nodata),
                                 overwrite=True)

        if not grass_library.checkFileExists(elevated_name):
            raise Exception('Could not apply offset to DEM')
    else:
        elevated_name = demname

    if fill_nulls:
        # Fill Null values
        print('Filling Null values')
        null_filled_name = 'patched_elevated_filled'
        grass.run_command('r.fillnulls',
                          input=elevated_name,
                          output=null_filled_name,
                          tension=40,
                          smooth=0.1,
                          overwrite=True)

        # Check file exists (to confirm command has run correctly
        if not grass_library.checkFileExists(null_filled_name):
            dem_common_functions.WARNING('Could not NULL fill DEM, possibly there are no NULL values to fill')
            null_filled_name = elevated_name

        # Smooth
        print('Smoothing')
        smoothed_name = 'patched_elevated_filled_smoothed'
        grass.run_command('r.neighbors',
                          input=null_filled_name,
                          output=smoothed_name,
                          overwrite=True)
        if not grass_library.checkFileExists(smoothed_name):
            raise Exception('Could not smooth file')
    else:
        smoothed_name=elevated_name

    # Export
    if out_demfile is not None:
        print('Exporting')
        grass.run_command('r.out.gdal',
                          format=out_raster_format,
                          type=out_raster_type,
                          input=smoothed_name,
                          output=out_demfile,
                          nodata=nodata,
                          overwrite=True)
        remove_gdal_aux_file(out_demfile)

    # Remove GRASS database created
    if remove_grassdb:
        shutil.rmtree(grassdb_path)
        return out_demfile, None
    else:
        return smoothed_name, grassdb_path


def patch_files(in_file_list,
                out_file=None,
                import_to_grass=True,
                nodata=dem_common.NODATA_VALUE,
                out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE,
                projection=None,
                grassdb_path=None,
                remove_grassdb=True):

    """
    Patches files together.

    Can be used to create a mosaic from adjacent tiles
    or replace nodata values with data values from another dataset.

    For example to fill in nodata areas::

       patch_files(['lidar_dem_with_no_data.dem','aster_dem.dem'],
                   'patched_dem.dem')

    Uses the following GRASS tool:

    http://grass.osgeo.org/grass64/manuals/r.patch.html

    If no output file is set returns name of patched file in GRASS database.

    If no projection is supplied, tries to get the projection from input files.

    Arguments:

    * in_file_list - List of input files
    * out_file - Output mosaic, if None will leave in GRASS database
    * import_to_grass - Should files be imported to GRASS, if False assumes in_file_list is a list of names within existing GRASS database.
    * nodata=No data value
    * out_raster_type - GDAL datatype for output raster (e.g., Float32)
    * projection - Projection to use (e.g., UKBNG) if not supplied will get from first input file.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one. Required if import_to_grass=False

    Returns:

    * out_file path / out_file name in GRASS database
    * path to GRASS database / None

    """
    # Set projection based on first file
    in_proj = None
    if projection is None:
        # If not importing to grass only a list of
        # names, not files.
        if import_to_grass:
            for in_file in in_file_list:
                while in_proj is not None:
                    in_proj = grass_library.getGRASSProjFromGDAL(in_file)
        if in_proj is None:
            dem_common_functions.WARNING('No projection supplied and could not determine projection from any input files.')
            dem_common_functions.WARNING('Assuming "WGS84LL".')
            in_proj = 'WGS84LL'
    else:
        in_proj = projection

    # Get output format from file extension
    if out_file is not None:
        out_raster_format = get_gdal_type_from_path(out_file)
    else:
        out_raster_format = dem_common.GDAL_OUTFILE_FORMAT

    if grassdb_path is None and not import_to_grass:
        raise Exception('No "grassdb_path" supplied but "import_to_grass" set to False.' +
                          'If files are already in GRASS supply path, else set "import_to_grass" to True')

    # Set up grass path
    if grassdb_path is None:
        grassdb_path = grass_library.grassDBsetup()
    else:
        location = in_proj
        mapset   = 'PERMANENT'
        grass.setup.init(dem_common.GRASS_LIB_PATH,
                    grassdb_path,
                    location,
                    mapset)

    grass_library.setLocation(in_proj)

    r_external_flags = 'e'

    if projection is not None:
        r_external_flags += 'o'

    # Import files (if needed)
    file_names_list = []
    if import_to_grass:
        for in_file in in_file_list:
            file_name=os.path.basename(in_file)
            # Externally link files rather than importing
            grass.run_command('r.external',
                              input=in_file,
                              output=file_name,
                              overwrite=True,
                              flags=r_external_flags,
                              quiet=False)

            if grass_library.checkFileExists(file_name):
                file_names_list.append(file_name)
            else:
                dem_common_functions.ERROR('The file "{}" could not be imported'.format(in_file))

    # Otherwise check they exist
    else:
        for file_name in in_file_list:
            if grass_library.checkFileExists(file_name):
                file_names_list.append(file_name)
            else:
                dem_common_functions.ERROR('The file "{}" does not exist in the supplied GRASS database'.format(file_name))

    # Check if at lest one file was imported / exists
    if len(file_names_list) == 0:
        raise Exception('None of the files in the list provided could be imported')

    # Set region to extent of input files
    grass_library.SetRegion(rast=file_names_list)

    # Patch files together
    patched_name = 'patched_tiles'
    grass.run_command("r.patch",
                      input=file_names_list,
                      output=patched_name,
                      overwrite=True,
                      flags="z")

    # Export file
    if out_file is not None:
        print('Exporting GDAL image')
        grass.run_command('r.out.gdal',
                     format=out_raster_format,
                     type=out_raster_type,
                     input=patched_name,
                     output=out_file,
                     nodata=nodata,
                     flags='f',
                     overwrite=True)
        remove_gdal_aux_file(out_file)

    # Remove GRASS database created
    if remove_grassdb:
        shutil.rmtree(grassdb_path)
        return out_file, None
    else:
        return patched_name, grassdb_path

def replace_nodata_val(in_demfile, out_demfile=None,
                       import_to_grass=True,
                       innodata=-9999,
                       outnodata=dem_common.NODATA_VALUE,
                       out_raster_type=dem_common.GDAL_OUTFILE_DATATYPE,
                       projection=None,
                       remove_grassdb=True,
                       grassdb_path=None):
    """
    Replaces nodata value in image with another value

    Arguments:

    * in_demfile - Input DEM.
    * out_demfile - Output DEM, if 'None', won't export from GRASS
                    database.
    * innodata - Input no data value
    * outnodata - No data value
    * out_raster_type - GDAL datatype for output raster (e.g., Float32)
    * projection - Projection to use (e.g., UKBNG) if not supplied will get from 'in_demfile'.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one.

    Returns:

    * out_demfile path / out_demfile name in GRASS database
    * path to GRASS database / None

    """

    # Set projection based on input file
    in_proj = None
    if projection is None:
        # If not importing to grass only a list of
        # names, not files.
        if import_to_grass:
            in_proj = grass_library.getGRASSProjFromGDAL(in_demfile)
        if in_proj is None:
            dem_common_functions.WARNING('No projection supplied and could not determine projection from any input files.')
            dem_common_functions.WARNING('Assuming "WGS84LL".')
            in_proj = 'WGS84LL'
    else:
        in_proj = projection

    # Get output format from file extension
    if out_demfile is not None:
        out_raster_format = get_gdal_type_from_path(out_demfile)
    else:
        out_raster_format = dem_common.GDAL_OUTFILE_FORMAT

    if grassdb_path is None and not import_to_grass:
        raise Exception('No "grassdb_path" supplied but "import_to_grass" set to False.' +
                          'If file is already in GRASS supply path, else set "import_to_grass" to True')

    # Set up grass path
    if grassdb_path is None:
        grassdb_path = grass_library.grassDBsetup()
    else:
        location = projection
        mapset   = 'PERMANENT'
        grass.setup.init(dem_common.GRASS_LIB_PATH,
                         grassdb_path,
                         location,
                         mapset)

    grass_library.setLocation(in_proj)

    # Import DEM into GRASS
    demname = os.path.basename(in_demfile).replace("-","_")

    print('Importing DEM')
    if import_to_grass:
        grass.run_command('r.external',
                          input = in_demfile,
                          output=demname,
                          flags='e',
                          overwrite=True)

    else:
        demname = in_demfile

    # Check file exists
    if not grass_library.checkFileExists(demname):
        raise Exception('Could not find {} in GRASS database'.format(demname))

    # Set region
    grass_library.SetRegion(rast=demname)

    replace_nodata_name = 'nodata_replace'

    # Replace no-data values
    grass.mapcalc('{0}=if({1} == {2},{3},{1})'.format(replace_nodata_name,
                                                      demname,
                                                      innodata,
                                                      outnodata),
                  overwrite=True)
    # Export
    if out_demfile is not None:
        print('Exporting')
        grass.run_command('r.out.gdal',
                          format=out_raster_format,
                          type=out_raster_type,
                          input=replace_nodata_name,
                          output=out_demfile,
                          nodata=outnodata,
                          overwrite=True)
        remove_gdal_aux_file(out_demfile)

    # Remove GRASS database created
    if remove_grassdb:
        shutil.rmtree(grassdb_path)
        return out_demfile, None
    else:
        return replace_nodata_name, grassdb_path


def subset_dem_to_bounding_box(in_dem_mosaic,
                     out_demfile,
                     bounding_box,
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
    Subsets DEM to bounding box to produce a DEM for use in APL. Can also supply output projection
    for patching with another DEM (e.g., from LiDAR). Note, supplying
    an output projection will make the resulting DEM incompatible with
    APL.

    If projections are supplied must use Proj4 format, can convert
    between GRASS style (e.g., UKBNG) using::

       grass_library.grass_location_to_proj4('UKBNG')


    Arguments:

    * in_dem_mosaic - Mosaic of large DEM to subset, can be anything GDAL can read (including a virtual raster file).
    * out_demfile - Output file.
    * bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]. Values are lat/long in degrees, if required will be reprojected within the function.
    * separation_file - Datum offset fill to add to heights.
    * ascii_separation_file - Bool to specify is separation file is ASCII format.
    * in_dem_projection - Input projection of DEM mosaic (Proj4 format)
    * out_projection - Output projection if not WGS84LL. Warning setting this will make the DEM incompatible with APL.
    * out_res - Out resolution e.g., (0.002,0.002) if not supplied gdalwarp will determine based on input resolution.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one.
    * fill_nulls - Null fill values

    Returns:

    * out_demfile
    * grassdb_path (None if remove_grassdb = True)

    """
    out_dem_name = None

    if out_demfile is None:
        # If an output isn't supplied this is OK, as long as it's being kept in GRASS
        if remove_grassdb:
            raise Exception('No out_demfile specified and remove_grassdb set to True. This would produce no output')
        tmp_outdem_fh, tmp_out_dem_name = tempfile.mkstemp(prefix='dem_subset',suffix='.dem', dir=dem_common.TEMP_PATH)
        tmp_out_dem_header = os.path.splitext(tmp_out_dem_name)[0] + '.hdr'
    else:
        tmp_out_dem_name = out_demfile

    # Subset DEM to navigation bounding box
    dem_common_functions.PrintTermWidth('Subsetting DEM to bounding box')
    # When subsetting perform horizontal reprojection
    # If output projection is not WGS84LL need to reproject bounding box
    if out_projection is not None and grass_library.proj4_to_grass_location(out_projection) != 'WGS84LL':
        tm_fh, temp_mosaic_dem = tempfile.mkstemp(prefix='dem_subset',suffix='.dem', dir=dem_common.TEMP_PATH)
        temp_mosaic_dem_header = os.path.splitext(temp_mosaic_dem)[0] + '.hdr'

        bounding_box_reproj = reproject_bounding_box(bounding_box,
                                               dem_common.WGS84_PROJ4_STRING,
                                               out_projection)

        # If DEM is WGS84LL, could be larger than bounds of output coordinate system (e.g., UKBNG) which
        # will cause problems.
        # Therefore, need to subset first (using a buffered bounding box) and then reproject.
        # A buffered bounding box is used on the initial subset to ensure full coverage.
        if grass_library.proj4_to_grass_location(in_dem_projection) == 'WGS84LL':
            subset_to_bb(in_dem_mosaic, temp_mosaic_dem,
                                       buffer_bounding_box_proportion(bounding_box),
                                       in_projection=in_dem_projection,
                                       out_projection=in_dem_projection)

            if separation_file is not None or fill_nulls:
                out_dem_name, grassdb_path = offset_null_fill_dem(
                                                temp_mosaic_dem,
                                                temp_mosaic_dem,
                                                separation_file=separation_file,
                                                ascii_separation_file=ascii_separation_file,
                                                nodata=-9999,
                                                remove_grassdb=remove_grassdb,
                                                grassdb_path=grassdb_path,
                                                fill_nulls=fill_nulls)

            subset_to_bb(temp_mosaic_dem, tmp_out_dem_name, bounding_box_reproj,
                                           in_projection=in_dem_projection,
                                           out_projection=out_projection,
                                           out_res=out_res)

            os.close(tm_fh)
            if os.path.isfile(temp_mosaic_dem):
                os.remove(temp_mosaic_dem)
            if os.path.isfile(temp_mosaic_dem_header):
                os.remove(temp_mosaic_dem_header)

        else:
            subset_to_bb(in_dem_mosaic, tmp_out_dem_name, bounding_box_reproj,
                                        in_projection=in_dem_projection,
                                        out_projection=out_projection,
                                        out_res=out_res)

    else:
        subset_to_bb(in_dem_mosaic, tmp_out_dem_name, bounding_box,
                                    in_projection=in_dem_projection,
                                    out_res=out_res)

        # Apply datum height offset and fill null values.
        if separation_file is not None or fill_nulls:
            out_dem_name, grassdb_path = offset_null_fill_dem(tmp_out_dem_name,
                                           tmp_out_dem_name,
                                           separation_file=separation_file,
                                           ascii_separation_file=ascii_separation_file,
                                           nodata=nodata,
                                           remove_grassdb=remove_grassdb,
                                           grassdb_path=grassdb_path,
                                           fill_nulls=fill_nulls)

    # If a temporary output file was created remove it
    if out_demfile is None:
        os.close(tmp_outdem_fh)
        if os.path.isfile(tmp_out_dem_name):
            os.remove(tmp_out_dem_name)
        if os.path.isfile(tmp_out_dem_header):
            os.remove(tmp_out_dem_header)

    if not remove_grassdb:
        return out_dem_name, grassdb_path
    else:
        return out_demfile, None

def get_screenshot_path(in_file,out_screenshots_dir):
    """
    Gets filepath for screenshot file.

    Arguments:

    * in_file - full path of file to use as base for name
    * screenshot_dir - directory to save screenshots to

    Returns:

    * file path for screenshot in the form:
                         screenshot_dir + in_file_base + '.jpg'

    """
    out_file_base = os.path.split(in_file)[-1]
    out_file_base = os.path.splitext(out_file_base)[0]
    screenshot_file = os.path.join(out_screenshots_dir, out_file_base + '.jpg')

    return screenshot_file

def export_screenshot(in_file, out_file,
                     import_to_grass=True,
                     shaded_relief=False,
                     projection=None,
                     grassdb_path=None,
                     remove_grassdb=True):
    """
    Export a screenshot in JPEG format with pixel values rescaled using
    histogram equalisation or as a shaded relief (hillshade) image.

    Arguments:

    * in_file - Input file in any GDAL format.
    * out_file - Output screenshot file (.jpg)
    * import_to_grass - Should file be imported to GRASS, if False assumes 'in_file' is the name of a raster within an existing GRASS database.
    * hillshade - Export shaded relief image instead of rescaled image (for DEMs).
    * projection - Projection to use (e.g., UKBNG) if not supplied will get from 'in_file'.
    * remove_grassdb - Remove GRASS database after processing is complete.
    * grassdb_path - Input path to GRASS database, if not supplied will create one. Required if import_to_grass=False

      Returns:

    * out_file path / rescaled file name in GRASS database
    * path to GRASS database / None

     """

    # Set projection based on input file
    in_proj = None
    if projection is None:
        # If not importing to grass only a name, not file path
        if import_to_grass:
            in_proj = grass_library.getGRASSProjFromGDAL(in_file)
        if in_proj is None:
            raise Exception('No projection supplied and could not determine projection from any input files.')
    else:
        in_proj = projection

    if grassdb_path is None and not import_to_grass:
        raise Exception('No "grassdb_path" supplied but "import_to_grass" set to False.' +
                          'If file is already in GRASS supply path, else set "import_to_grass" to True')

    # Set up grass path
    if grassdb_path is None:
        grassdb_path = grass_library.grassDBsetup()
    else:
        location = projection
        mapset   = 'PERMANENT'
        grass.setup.init(dem_common.GRASS_LIB_PATH,
                    grassdb_path,
                    location,
                    mapset)

    grass_location = grass_library.setLocation(in_proj)

    if import_to_grass:
        print('Importing file to GRASS')
        # Import File into GRASS
        file_name = os.path.basename(in_file).replace("-","_")
        grass.run_command('r.external',
                    input=in_file,
                    output=file_name,
                    flags='e',
                    overwrite=True)
    else:
        file_name = in_file

    # Check file exists
    if not grass_library.checkFileExists(file_name):
        raise Exception('Could not find {} in GRASS database'.format(file_name))

    # Set region
    grass_library.SetRegion(rast=file_name)

    rescaled_name=os.path.splitext(file_name)[0] + 'rescaled'

    # Create shaded relief image or rescale
    if shaded_relief:
        shaded_name=os.path.splitext(file_name)[0] + '_relief'
        grass.run_command('r.shaded.relief',
                          map=file_name,
                          shadedmap=shaded_name)

        if not grass_library.checkFileExists(shaded_name):
            raise Exception('Could not find create shaded relief image')

        file_name=shaded_name

    # Rescale from 1 to 255 (reserve 0 for no data)
    grass.run_command('r.rescale.eq',
                      input=file_name,
                      output=rescaled_name,
                      to='1,255',
                      flags='q',
                   overwrite=True)
    if not grass_library.checkFileExists(rescaled_name):
        raise Exception('Could not rescale image')

    # Export as JPEG
    # Use function in grass_library which will ensure
    # image is not larger than maximum number of pixels.
    grass_library.outputToGDAL(rescaled_name,out_file,
                               imtype='JPEG',
                               nodata=0,
                               datatype='Byte',
                               setregiontoimage=True,
                               resolution=None,tidyup=False)
    remove_gdal_aux_file(out_file)

    # Remove GRASS database created
    if remove_grassdb:
        shutil.rmtree(grassdb_path)
        return out_file, None
    else:
        return rescaled_name, grassdb_path

def subset_to_bb(in_dem_mosaic, out_demfile, bounding_box,
                     in_projection=None,
                     out_projection=dem_common.WGS84_PROJ4_STRING,
                     out_res=None):
    """
    Subset a raster to a bounding box using gdalwarp, if reprojection is also required or gdal_translate
    if bounding_box and input DEM have the same projection.

    Takes and exports raster in any projection, can supply WKT file or Proj4 string using
    'in_projection' and 'out_projection'.

    Arguments:

    * in_dem_mosaic - Mosaic of large DEM to subset, can be anything GDAL can read (including a virtual raster file).
    * out_demfile - Output file.
    * bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]
    * in_projection - Projection of input mosaic as EPSG code, Proj4 string or WKT file. If not supplied will read from file.
    * out_projection - Projection of output mosaic, must be the same as bounding box.
    * out_res - Out resolution e.g., (10,-10)

    Returns:

    * None

    """

    if len(bounding_box) != 4:
        raise Exception('Expected four values for bounding box')

    # If input and output projections are the same then calling gdalwarp will regrid
    # to align with bounding box. Can use gdaltranslate with 'projwin' instead.
    if in_projection == out_projection:
        gdal_translate_cmd = ['gdal_translate', '-projwin',str(bounding_box[2]),
                                                str(bounding_box[1]),
                                                str(bounding_box[3]),
                                                str(bounding_box[0])]
        gdal_translate_cmd.extend(['-of',dem_common.GDAL_OUTFILE_FORMAT])
        gdal_translate_cmd.extend(['-ot',dem_common.GDAL_OUTFILE_DATATYPE])
        gdal_translate_cmd.extend(['-co',dem_common.GDAL_CREATION_OPTIONS])
        gdal_translate_cmd.extend([in_dem_mosaic, out_demfile])
        dem_common_functions.CallSubprocessOn(gdal_translate_cmd)
    else:
        call_gdalwarp(in_dem_mosaic, out_demfile,
                       s_srs=in_projection,
                       t_srs=out_projection,
                       of=dem_common.GDAL_OUTFILE_FORMAT,
                       ot=dem_common.GDAL_OUTFILE_DATATYPE,
                       co=dem_common.GDAL_CREATION_OPTIONS,
                       r=dem_common.RESAMPLE_METHOD,
                       out_extent=bounding_box,
                       target_res=out_res)


def reproject_bng_to_wgs84(in_file, out_file, vertical_reproject=False):
    """
    Re-project DEM from British National grid to WGS-84
    lat-long.

    Uses Ordnance Survey OSTN02 transform file

    Arguments:

    * in_file (UKBNG projection)
    * out_file (WGS84LL projection)
    * vertical_reproject - apply vertical offset to heights so they are relative to WGS-84 elipsoid rather then Newlyn datum

    Returns:

    * out_file

    Example::

    dem_utilities.reproject_bng_to_wgs84('nextmap_plymouth_bng.dem','nextmap_plymouth_wgs84.dem',vertical_reproject=True)


    """

    if not os.path.isfile(dem_common.OSTN02_NTV2_BIN_FILE):
        raise Exception("Could not find OSTN02 transform file.\nChecked {}".format(dem_common.OSTN02_NTV2_BIN_FILE))

    if vertical_reproject:
        if not os.path.isfile(dem_common.UKBNG_SEP_FILE_WGS84):
            raise Exception('Could not find UKBNG seperation file in speficied location:'
                              ' "{}"'.format(dem_common.UKBNG_SEP_FILE_WGS84))

        tr_fh, temp_reproject_dem = tempfile.mkstemp(prefix='reproject_dem',suffix='.dem', dir=dem_common.TEMP_PATH)
        temp_reproject_dem_header = os.path.splitext(temp_reproject_dem)[0] + '.hdr'
        temp_file_list = [temp_reproject_dem, temp_reproject_dem_header]

        gdalout = call_gdalwarp(in_file, temp_reproject_dem,
                       s_srs=dem_common.OSTN02_PROJ4_STRING,
                       t_srs=dem_common.WGS84_PROJ4_STRING)

        if gdalout != 0:
            raise Exception('Problem running gdalwarp command')

        try:
            offset_null_fill_dem(temp_reproject_dem, out_file,
                               separation_file=dem_common.UKBNG_SEP_FILE_WGS84,
                               ascii_separation_file=dem_common.UKBNG_SEP_FILE_WGS84_IS_ASCII)

        except Exception as err:
            dem_common_functions.ERROR('Error adding seperation file:\n{}'.format(err))
            for temp_file in temp_file_list:
                if os.path.isfile(temp_file):
                    os.remove(temp_file)
            return None

        os.close(tr_fh)
        for temp_file in temp_file_list:
            if os.path.isfile(temp_file):
                os.remove(temp_file)

    else:
        gdalout = call_gdalwarp(in_file, out_file,
                       s_srs=dem_common.OSTN02_PROJ4_STRING,
                       t_srs=dem_common.WGS84_PROJ4_STRING)
        if gdalout != 0:
            return None

    return out_file

def reproject_wgs84_to_bng(in_file, out_file, vertical_reproject=False):
    """
    Re-project WGS-84 lat-long to British
    National Grid.

    Uses Ordnance Survey OSTN02 transform file

    Arguments:

    * in_file (WGS84LL projection)
    * out_file (UKBNG projection)

    Returns:

    * None

    Example::

    dem_utilities.reproject_wgs84_to_bng('aster_plymouth_wgs84.dem','aster_plymouth_bng.dem',vertical_reproject=True)

    """

    if not os.path.isfile(dem_common.OSTN02_NTV2_BIN_FILE):
        raise Exception("Could not find OSTN02 transform file.\nChecked {}".format(dem_common.OSTN02_NTV2_BIN_FILE))

    if vertical_reproject:
        temp_reproject_dem = tempfile.mkstemp(prefix='reproject_dem',suffix='.dem', dir=dem_common.TEMP_PATH)[1]
        temp_reproject_dem_header = os.path.splitext(temp_reproject_dem)[0] + '.hdr'
        temp_file_list = [temp_reproject_dem, temp_reproject_dem_header]

        gdalout = call_gdalwarp(in_file, temp_reproject_dem,
                          s_srs=dem_common.WGS84_PROJ4_STRING,
                          t_srs=dem_common.OSTN02_PROJ4_STRING)
        if gdalout != 0:
            raise Exception('Problem running gdalwarp command')

        if vertical_reproject:
            if not os.path.isfile(dem_common.UKBNG_SEP_FILE_UKBNG):
                raise Exception('Could not find UKBNG seperation file in speficied location:'
                               ' "{}"'.format(dem_common.UKBNG_SEP_FILE_UKBNG))
            try:
                offset_null_fill_dem(temp_reproject_dem, out_file,
                                   separation_file=dem_common.UKBNG_SEP_FILE_UKBNG,
                                   ascii_separation_file=dem_common.UKBNG_SEP_FILE_UKBNG_IS_ASCII,
                                   subtract_seperation=True)

            except Exception as err:
                dem_common_functions.ERROR('Error subtracting seperation file:\n{}'.format(err))
                for temp_file in temp_file_list:
                    if os.path.isfile(temp_file):
                        os.remove(temp_file)
                return None

        for temp_file in temp_file_list:
            if os.path.isfile(temp_file):
                os.remove(temp_file)
    else:
        gdalout = call_gdalwarp(in_file, out_file,
                       s_srs=dem_common.WGS84_PROJ4_STRING,
                       t_srs=dem_common.OSTN02_PROJ4_STRING)
        if gdalout != 0:
            return None

    return out_file

def call_gdalwarp(in_file, out_file, s_srs=None, t_srs=dem_common.WGS84_PROJ4_STRING,
                     of=dem_common.GDAL_OUTFILE_FORMAT,
                     ot=dem_common.GDAL_OUTFILE_DATATYPE,
                     co=dem_common.GDAL_CREATION_OPTIONS,
                     r=dem_common.RESAMPLE_METHOD,
                     srcnodata=None,
                     dstnodata=None,
                     target_res=None,
                     out_extent=None,
                     overwrite=True):

    """
    Python utility to call gdalwarp

    http://www.gdal.org/gdalwarp.html

    Parameters map onto those required by gdalwarp
    command line tool.

    Note to get correct projection to/from BNG need to use
    OSTN02 transform file. This is passed in as part of Proj4 string.

    TODO: Update to use Python functions.
    Needs some work as there isn't a Python equivalent of gdalwarp.
    Currently has to call subprocess using shell=True so creation options are
    passed in correctly.

    Arguments:

    * in_file - input file.
    * out_file - output file.
    * s_srs - projection of input_file (Proj4 string). If not supplied will determine from image.
    * t_srs - target projection (default is WGS84).
    * of - GDAL name for output image format (e.g., ENVI).
    * ot - GDAL name for output image type (e.g., Float32).
    * co - creation options.
    * r - resample method (near, bilinear, cubic).
    * srcnodata - nodata value for in_file.
    * dstnodata - nodata value for out_file.
    * target_res - resulution of output image (will determine from in_file if not supplied).
    * out_extent - extent of output image (in t_srs projection).
    * overwrite - overwrite existing image if it exists.

    Returns:

    * Command return status.

    """

    # Construct GDAL command
    gdalwarp_cmd = ['gdalwarp']

    if overwrite:
        gdalwarp_cmd.extend(['-overwrite'])

    # Add output extent if provided
    if out_extent is not None:
        if len(out_extent) != 4:
            raise Exception('Expected four values for extent')
        gdalwarp_cmd.extend(['-te',str(out_extent[2]),
                                   str(out_extent[0]),
                                   str(out_extent[3]),
                                   str(out_extent[1])])

    if target_res is not None:
        if isinstance(target_res, list):
            # If a list has been passed in use different values for x and y
            gdalwarp_cmd.extend(['-tr',str(target_res[0]),
                                 str(target_res[1])])
        else:
            gdalwarp_cmd.extend(['-tr',str(target_res),
                                 str(target_res)])
    if s_srs is not None:
        gdalwarp_cmd.extend(['-s_srs','"{}"'.format(s_srs)])

    if srcnodata is not None:
        gdalwarp_cmd.extend(['-srcnodata',str(srcnodata)])

    if dstnodata is not None:
        gdalwarp_cmd.extend(['-dstnodata',str(dstnodata)])

    gdalwarp_cmd.extend(['-t_srs','"{}"'.format(t_srs)])
    gdalwarp_cmd.extend(['-of',of,'-ot',ot,
                         '-co','"{}"'.format(co)])
    gdalwarp_cmd.extend(['-r',r])
    gdalwarp_cmd.extend([in_file, out_file])

    cmd_str = ""

    for option in gdalwarp_cmd:
        cmd_str += option + " "

    print('Attempting to run command:' ,cmd_str)
    cmdOut = subprocess.call(cmd_str,shell=True)
    remove_gdal_aux_file(out_file)

    return cmdOut


def call_gdaldem(in_file, out_file, dem_product='hillshade',
                              of=dem_common.GDAL_OUTFILE_FORMAT):
    """
    Calls gdaldem command to produce derived products from DEM.
    Options are:

    * hillshade (default)
    * slope
    * aspect
    * TRI
    * TPI
    * roughnness

    For more information see:
    http://www.gdal.org/gdaldem.html
    """

    gdaldem_cmd = ['gdaldem',dem_product,
                   '-of',of,
                   in_file, out_file]
    dem_common_functions.CallSubprocessOn(gdaldem_cmd)
    remove_gdal_aux_file(out_file)

def get_gdal_dataset_bb(in_file, output_ll=False):
    """
    Get bounding box from GDAL dataset by reading
    extent from header.

    Arguments:

    * in_file - input file
    * output_ll - return bounding box as lat/long

    Returns:

    * bounding box as [min_y,max_y, min_x,max_x]

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    # Get information from image
    dataset = gdal.Open(in_file, gdal.GA_ReadOnly)
    if dataset is None:
        raise IOError('Could not open "{}" using GDAL'.format(in_file))
    projection = dataset.GetProjectionRef()
    geotransform = dataset.GetGeoTransform()
    x_size = dataset.RasterXSize
    y_size = dataset.RasterYSize

    # Get bounding box
    min_x = geotransform[0]
    max_y = geotransform[3]
    pixel_size_x = geotransform[1]
    pixel_size_y = geotransform[5]
    max_x = min_x + (x_size * pixel_size_x)
    min_y = max_y + (y_size * pixel_size_y)

    bounding_box = [min_y,max_y, min_x,max_x]

    # Import projections to SpatialReference class
    image_spatial_ref = osr.SpatialReference()
    image_spatial_ref.ImportFromWkt(projection)
    image_proj = image_spatial_ref.ExportToProj4()

    out_proj = dem_common.WGS84_PROJ4_STRING
    out_spatial_ref = osr.SpatialReference()
    out_spatial_ref.ImportFromProj4(out_proj)

    # Check if output in WGS84LL has been selected and the input coordinate
    # system is projected (in m)
    if output_ll and image_spatial_ref.IsProjected():

        if image_proj == '':
            raise Exception('The file "{}" contains no '
                            'projection information'.format(in_file))

        reprojected_bb = reproject_bounding_box(bounding_box,
                                                image_proj,
                                                out_proj)

        # Check the reprojected bounding box is a sensible size.
        # Do this by converting y-size of bounding box (in m) to degrees
        # at equator.
        # Must use equator as latitude is what we want to check - also for
        # latitude makes no difference.
        in_x_size_m = max_x - min_x
        in_y_size_m = max_y - min_y
        out_y_size_deg = reprojected_bb[1] - reprojected_bb[0]

        check_x_size_deg, check_y_size_deg = m_to_deg(0, in_x_size_m,
                                                      in_y_size_m)

        # Can't do exact comparison as 'm_to_deg' is less accurate but if
        # the difference is more than 50 % is very likely to be a problem
        if out_y_size_deg > (check_y_size_deg * 1.5) or \
           out_y_size_deg < (check_y_size_deg * 0.5):
            print('Input bounding box (from image):')
            print(bounding_box)
            print('Output bounding box (reprojected):')
            print(reprojected_bb)
            raise Exception('Reprojected bounding box is larger than expected.\n'
                            'Check correct projection has been provided')

        bounding_box = reprojected_bb

    # Close dataset
    dataset = None

    return bounding_box

def remove_gdal_aux_file(in_file):
    """
    Removes the .aux.xml file created by GDAL

    Arguments:

    * Raster name.

    Returns:

    * None

    """
    aux_file = in_file + '.aux.xml'

    # If there is no .aux.xml file, can just return
    if not os.path.isfile(aux_file):
        return None

    # For ENVI files make sure relevant data (e.g., nodata values)
    # are copied to header file
    if get_gdal_type_from_path(in_file) == 'ENVI':
        no_data_val = get_nodata_value(in_file)

        if no_data_val is not None:
            in_file_ds  = gdal.Open(in_file, gdal.GA_ReadOnly)
            if in_file_ds is None:
                raise Exception('Could not open {} using GDAL'.format(in_file))
            in_file_header = None
            for component_file in in_file_ds.GetFileList():
                if component_file.endswith('.hdr'):
                    in_file_header = component_file
            if in_file_header is None:
                raise Exception('Could not find header for {}'.format(in_file))
            in_file_ds = None

            # Open header and append text to bottom
            with open(in_file_header,'a') as f:
                f.write('data ignore value = {}\n'.format(no_data_val))

    os.remove(aux_file)

def reproject_bounding_box(in_bounding_box,
                           in_projection,
                           out_projection):
    """
    Reproject coordinates of bounding box

    Arguments:

    * in_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]
    * in_projection - Proj4 string of input projection.
    * out_projection - Proj4 string of output projection.

    Returns:

    * out_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]

    """
    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    in_srs = osr.SpatialReference()
    out_srs = osr.SpatialReference()

    # Check if Proj4 string is within quotes
    # remove if so.
    if in_projection[0] == '"' or in_projection[0] == '\'':
        in_projection = in_projection[1:-1]

    if out_projection[0] == '"' or out_projection[0] == '\'':
        out_projection = out_projection[1:-1]

    in_srs.ImportFromProj4(in_projection)
    out_srs.ImportFromProj4(out_projection)

    minX = in_bounding_box[2]
    maxX = in_bounding_box[3]
    minY = in_bounding_box[0]
    maxY = in_bounding_box[1]

    min_in_coords = [(minX, minY)]
    max_in_coords = [(maxX, maxY)]

    ctr = osr.CoordinateTransformation(in_srs, out_srs)

    min_out_coords = ctr.TransformPoints(min_in_coords)[0]
    max_out_coords = ctr.TransformPoints(max_in_coords)[0]

    return [min_out_coords[1],max_out_coords[1],
            min_out_coords[0],max_out_coords[0]]

def buffer_bounding_box_proportion(in_bounding_box, buffer_proportion=0.1):
    """
    Buffer bounding box by a proportion of the box size

    Arguments:

    * in_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]
    * buffer_proportion - Proportion of box size to buffer (default=0.1)

    Returns:

    * out_bounding_box - List of 4 values providing the bounding box of the format: [MinY, MaxY, MinX, MaxX]

    """

    out_bounding_box = in_bounding_box
    height = in_bounding_box[1] - in_bounding_box[0]
    width = in_bounding_box[3] - in_bounding_box[2]

    out_bounding_box[0] = in_bounding_box[0] - height*(buffer_proportion/2.0)
    out_bounding_box[1] = in_bounding_box[1] + height*(buffer_proportion/2.0)
    out_bounding_box[2] = in_bounding_box[2] - width*(buffer_proportion/2.0)
    out_bounding_box[3] = in_bounding_box[3] + width*(buffer_proportion/2.0)

    return out_bounding_box

def deg_to_m(lat, lonsize, latsize):
    """
    Get the pixel size (in m) based on latitude and
    pixel size in degrees.

    Function taken from:
    https://github.com/MiXIL/calcSlopeDegrees/
    MIT license

    Arguments:

    * lat - latitude
    * lonsize - numpy array of x pixel sizes (degrees)
    * latsize - numpy array of y pixel sizes (degrees)

    Returns:

    * xsize - numpy array of x pixel sizes (m)
    * ysize - numpy array of y pixel sizes (m)

    """

    # Set up parameters for ellipse
    # Semi-major and semi-minor for WGS-84 ellipse
    ellipse = [6378137.0, 6356752.314245]

    radlat = numpy.deg2rad(lat)

    Rsq = (ellipse[0]*numpy.cos(radlat))**2+(ellipse[1]*numpy.sin(radlat))**2
    Mlat = (ellipse[0]*ellipse[1])**2/(Rsq**1.5)
    Nlon = ellipse[0]**2/numpy.sqrt(Rsq)
    xsize = numpy.pi/180*numpy.cos(radlat)*Nlon*lonsize
    ysize = numpy.pi/180*Mlat*latsize

    return xsize, ysize

def m_to_deg(lat, xsize, ysize):
    """
    Get the pixel size (in degrees) based on latitude and
    pixel size in metres.

    Function modified from:
    https://github.com/MiXIL/calcSlopeDegrees/
    MIT license

    Arguments:

    * lat - latitude
    * xsize - numpy array of x pixel sizes (m)
    * ysize - numpy array of y pixel sizes (m)

    Returns:

    * lonsize - numpy array of x pixel sizes (degrees)
    * latsize - numpy array of y pixel sizes (degrees)

    """

    # Set up parameters for ellipse
    # Semi-major and semi-minor for WGS-84 ellipse
    ellipse = [6378137.0, 6356752.314245]

    radlat = numpy.deg2rad(lat)

    Rsq = (ellipse[0]*numpy.cos(radlat))**2+(ellipse[1]*numpy.sin(radlat))**2
    Mlat = (ellipse[0]*ellipse[1])**2/(Rsq**1.5)
    Nlon = ellipse[0]**2/numpy.sqrt(Rsq)
    lonsize = xsize / (numpy.pi/180*numpy.cos(radlat)*Nlon)
    latsize = ysize / (numpy.pi/180*Mlat)

    return lonsize, latsize

def get_gdal_type_from_path(file_name):
    """
    Get GDAL format, based on filename

    Arguments:

    * file_name - name of output file (can be full path)

    Returns:

    * GDAL format string of data type.

    """
    # If filename is none, return default output format.
    if file_name is None:
        return dem_common.GDAL_OUTFILE_FORMAT

    gdal_str = None
    extension = os.path.splitext(file_name)[-1].lower()

    try:
        gdal_str = get_gdal_drivers.GDALDrivers().get_driver_from_ext(extension)
    except KeyError:
        # If the extension isn't recognised go with ENVI.
        gdal_str = 'ENVI'

    return gdal_str

def add_dem_metadata(dem_name, dem_source=None, dem_filename=None,
                               other_items=None):
    """
    Adds metadata to DEM with original DEM source

    Arguments:

    * dem_name - Name of DEM file
    * dem_source (e.g., ASTER)
    * dem_filename (name of mosaic DEM was derived from)
    """
    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    # If ENVI dataset, write key to header file
    if get_gdal_type_from_path(dem_name) == 'ENVI':
        # Get ENVI header (using GDAL filelist function)
        dem_dataset  = gdal.Open(dem_name, gdal.GA_ReadOnly)
        if dem_dataset is None:
            raise Exception('Could not open {}'.format(dem_name))
        dem_header = dem_dataset.GetFileList()[1]
        dem_dataset = None

        # Open header and append text to bottom
        with open(dem_header,'a') as f:
            if dem_source is not None:
                f.write(';DEM Source={}\n'.format(dem_source))
            if dem_filename is not None:
                f.write(';Original DEM filename={}\n'.format(dem_filename))
            if other_items is not None:
                if type(other_items) is not dict:
                    raise TypeError('"other_items" must be a dictionary')
                for key in other_items.keys():
                    f.write(';{}={}\n'.format(key, other_items[key]))

    # If not try to write using GDAL metadata function.
    else:
        dem_dataset  = gdal.Open(dem_name, gdal.GA_Update)
        if dem_dataset is None:
            raise Exception('Could not open {} using GDAL to write metadata to'.format(dem_name))

        metadata = dem_dataset.GetMetadata()

        if dem_source is not None:
            metadata['DEM Source'] = dem_source
        if dem_filename is not None:
            metadata['Original DEM filename'] = dem_filename
        if other_items is not None:
            if type(other_items) is not dict:
                raise TypeError('"other_items" must be a dictionary')
            metadata.update(other_items)

        # Save updated metadata dictionary
        dem_dataset.SetMetadata(metadata)

        # Close dataset
        dem_dataset = None

def check_gdal_dataset(in_file):
    """
    Checks a dataset can be opened using GDAL.

    Raises IOError if it can't.

    Based on example from Even Rouault

    https://lists.osgeo.org/pipermail/gdal-dev/2013-November/037520.html

    Arguments:

    * in_file - path to existing GDAL dataset.

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    gdal_ds = gdal.Open(in_file, gdal.GA_ReadOnly)
    if gdal.GetLastErrorType() != 0:
        raise IOError(gdal.GetLastErrorMsg())
    gdal_ds = None

def get_nodata_value(in_file):
    """
    Gets nodata value for a GDAL dataset.

    Reverts to default if none is available.

    Arguments:

    * in_file - path to existing GDAL dataset.

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    gdal_ds = gdal.Open(in_file, gdal.GA_ReadOnly)
    nodata = gdal_ds.GetRasterBand(1).GetNoDataValue()
    gdal_ds = None

    return nodata

def set_nodata_value(in_file, nodata_value):
    """
    Sets nodata value for the first band of a GDAL dataset.

    Arguments:

    * in_file - path to existing GDAL dataset.
    * nodata_value - nodata value

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    gdal_ds = gdal.Open(in_file, gdal.GA_Update)
    gdal_ds.GetRasterBand(1).SetNoDataValue(nodata_value)
    gdal_ds = None
