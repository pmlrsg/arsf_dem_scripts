#!/usr/bin/env python
#Description: A script to create a DEM from tiles
"""
Author: Dan Clewley (dac)

Created on: 08 June 2015

"""

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

import sys
import argparse
import glob
from arsf_dem import dem_utilities
from arsf_dem import dem_common
from arsf_dem import dem_common_functions

description_str = """
mosaic_dem_tiles.py

Create a mosaic from DEM tiles (e.g., ASTER / SRTM) and apply offsets
so heights are relative to WGS-84 ellipsoid rather than geoid.

Entire extent of DEM is kept. If subsetting to navigation data is required
use 'create_apl_dem.py' instead. See example 7 in help.

"""
try:
    parser = argparse.ArgumentParser(description=description_str, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("demtiles", nargs='+',type=str, help="Tiles to create DEM from")
    parser.add_argument('-o', '--outdem',
                        metavar ='Out DEM',
                        help ='Output name for mosaiced DEM',
                        required=True,
                        default=None)
    args=parser.parse_args()

    # On Windows don't have shell expansion so fake it using glob
    if args.demtiles[0].find('*') > -1:
        input_tile_list = glob.glob(args.demtiles[0])
    else:
        input_tile_list = args.demtiles

    out_mosaic, grassdb_path = dem_utilities.patch_files(input_tile_list,
                 out_file=None,
                 import_to_grass=True,
                 projection='WGS84LL',
                 nodata=dem_common.NODATA_VALUE,
                 remove_grassdb=False)

    dem_utilities.offset_null_fill_dem(out_mosaic,
                                    out_demfile=args.outdem,
                                    import_to_grass=False,
                                    separation_file=dem_common.WWGSG_FILE,
                                    ascii_separation_file=dem_common.WWGSG_FILE_IS_ASCII,
                                    fill_nulls=True,
                                    projection='WGS84LL',
                                    nodata=dem_common.NODATA_VALUE,
                                    out_raster_format=dem_utilities.get_gdal_type_from_path(args.outdem),
                                    remove_grassdb=True,
                                    grassdb_path=grassdb_path)

except KeyboardInterrupt:
    sys.exit(2)
except Exception as err:
    dem_common_functions.ERROR(err)
    sys.exit(1)
