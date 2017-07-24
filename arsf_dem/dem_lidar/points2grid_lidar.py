#Author: Dan Clewley (dac)
#Created on: 02 April 2015
"""
Functions for working with LiDAR data using points2grid:

https://github.com/CRREL/points2grid

Requires the development version of points2grid to be installed which
has filters for LAS points.

Documentation on points2grid is available from:

http://www.opentopography.org/otsoftware/points2grid

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import shutil
import tempfile
# Import common files
from .. import dem_common
from .. import dem_common_functions
from .. import get_gdal_drivers

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
        # Set output options
        out_ext = os.path.splitext(out_raster)[-1]
        out_format = get_gdal_drivers.GDALDrivers().get_driver_from_ext(out_ext)
        out_options = \
        get_gdal_drivers.GDALDrivers().get_creation_options_from_ext(out_ext)

        gdal_translate_cmd = ['gdal_translate',
                              '-of',out_format]
        # If there are creation options add these
        for creation_option in out_options:
            gdal_translate_cmd.extend(['-co', creation_option])

        if projection is not None:
            gdal_translate_cmd.extend(['-a_srs',projection])

        gdal_translate_cmd.extend([in_raster, out_raster])
        dem_common_functions.CallSubprocessOn(gdal_translate_cmd)

def _las_to_dem(in_las, out_dem,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               demtype='DSM',
               grid_method='mean',
               search_radius=None,
               fill_window_size=None,
               exclude_class=[7],
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
    * search_radius - specifies the search radius (default is 2 or resolution, whichever is greater)
    * fill_window_size - window size to use for filling nulls
    * exclude_class - list of classes to exclude (default = class 7)
    * quiet - don't print output from points2grid command

    """
    if not _checkPoints2Grid():
        raise Exception('Could not find points2grid, checked {}'.format(dem_common.POINTS2GRID_BIN_PATH))

    outdem_handler, dem_tmp = tempfile.mkstemp(suffix='', dir=dem_common.TEMP_PATH)

    # Set search raduis. For 'typical' ARSF
    if search_radius is None:
        if resolution < 2:
            search_radius = 2
        else:
            search_radius = resolution

    print('Creating surface')
    surfaceCMD = [os.path.join(dem_common.POINTS2GRID_BIN_PATH,'points2grid'),
                  '--output_file_name',dem_tmp,
                  '--output_format','arc',
                  '--search_radius', str(search_radius),
                  '--resolution',str(resolution)]
    surfaceCMD.extend(['--exclude_class'])
    surfaceCMD.extend([str(c) for c in exclude_class])

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

    if fill_window_size is not None:
        if fill_window_size not in [3, 5, 7]:
            raise ValueError('Size for fill window must be 3, 5 or 7. '
                             '{} was provided'.format(fill_window_size))
        surfaceCMD.extend(['--fill',
                           '--fill_window_size', str(fill_window_size)])

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
               fill_window_size=None,
               quiet=True):
    """
    Create Digital Surface Model (DSM) from a LAS file using points2grid

    Arguments:

    * in_las - Input LAS File
    * out_dsm - Output DTM file
    * resolution - output resolution
    * grid_method - points2grid output type (min, max, mean, idw or std)
    * fill_window_size - window size to use for filling nulls
    * quiet - don't print output from points2grid command

    """
    _las_to_dem(in_las, out_dsm,
                resolution=resolution,
                projection=projection,
                demtype='DSM',
                grid_method=grid_method,
                fill_window_size=fill_window_size,
                quiet=quiet)

    return None

def las_to_dtm(in_las, out_dtm,
               resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
               projection=None,
               grid_method='mean',
               fill_window_size=None,
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
    * fill_window_size - window size to use for filling nulls
    * quiet - don't print output from points2grid command

    """
    _las_to_dem(in_las, out_dtm,
                resolution=resolution,
                projection=projection,
                demtype='DTM',
                grid_method=grid_method,
                fill_window_size=fill_window_size,
                quiet=quiet)

    return None

def classified_las_to_dtm(in_las, out_dtm,
                          resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                          projection=None,
                          grid_method='mean',
                          fill_window_size=7,
                          quiet=True):
    """
    Create Digital Terrain Model (DTM) from a LAS file where the ground
    returns have already been classified (class 2).

    Arguments:

    * in_las - Input classified LAS File
    * out_dtm - Output DTM file
    * resolution - output resolution
    * grid_method - points2grid output type (min, max, mean, idw or std)
    * fill_window_size - window size to use for filling nulls
    * quiet - don't print output from points2grid command

    """
    non_ground_classes = [i for i in range(0,32)]
    non_ground_classes.remove(2)

    _las_to_dem(in_las, out_dtm,
                resolution=resolution,
                projection=projection,
                demtype='DTM',
                grid_method=grid_method,
                fill_window_size=fill_window_size,
                exclude_class=non_ground_classes,
                quiet=quiet)

    return None
