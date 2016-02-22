

ARSF DEM Scripts
================

The following command line tools are provided by ARSF DEM.

Note under Windows, there is no need to type the '.py' at the end of the scripts. Batch files have been created to run the Python scripts, which don't need an extension to be provided.

create_apl_dem
-------------------

.. code-block:: bash

   usage: create_apl_dem.py [-h] [-o Out DEM] [-n Nav file]
                            [-p Main project directory] [--aster] [--nextmap]
                            [--srtm] [--demmosaic Input DEM mosaic]
                            [--separation_file Seperation file]
                            [-b BIL Navigation Files] [--keepgrassdb]
   
   A script to create a DEM for use in APL subset to bounds
   of hyperspectral navigation data.
   
   If not running on ARSF systems need to pass in bil format navigation files
   (supplied with delivered hyperspectral data).
   
   Typical usage:
   
   1) Create Next map DEM
   
    create_apl_dem.py --nextmap -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_NEXTMAP.dem
   
   2) Create ASTER DEM
   
    create_apl_dem.py --aster -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_ASTER.dem
   
   3) Create STRM DEM
   
    create_apl_dem.py --srtm -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o GB14_00-2014_216_SRTM.dem
   
   4) Create DEM from custom dataset, where heights are relative to geoid
   
    create_apl_dem.py --demmosaic local_dem_egm96.tif --separation_file /users/rsg/arsf/dems/geoid-spheroid/ww15mgh.grd \
              -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_custom.dem
   
   5) Create DEM from custom dataset, where heights are already relative to WGS-84 ellipsoid
   
    create_apl_dem.py --demmosaic local_dem_utm10n.bil \
              -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_custom.dem
   
   6) Create DEM from ASTER using post-processed bil format navigation data (for delivered data)
   
    create_apl_dem.py --aster --bil_navigation flightlines/navigation -o 2014_216_aster.dem
   
   7) Create a DEM from downloaded SRTM tiles for use in APL using processed navigation files
   
    # Create VRT mosaic of downloaded tiles
   
    gdalbuildvrt srtm_mosaic.vrt *1arc_v3.tif
   
    # Create DEM
   
    create_apl_dem.py --demmosaic strm_mosaic.vrt --separation_file /users/rsg/arsf/dems/geoid-spheroid/ww15mgh.grd \
              --bil_navigation flightlines/navigation -o 2014_216_strm.dem
   
   If calling from within the project directory, there should be no need to specify the
   project path as it will be found from the current location.
   
   Known issues:
   If the correct project path is not found or passed in, or for another reason
   there is a problem finding hyperspectral navigation files the script will
   print a warning but continue and produce a DEM much larger than required.
   
   'create_apl_dem' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
      
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out DEM, --outdem Out DEM
                           Output name for DEM. If not provided will output to
                           standard location for hyperspectral data processing.
     -n Nav file, --nav Nav file
                           Navigation data (.sol / .sbet file)
     -p Main project directory, --project Main project directory
                           Main project directory (default=".")
     --aster               Use ASTER data
                           (/users/rsg/arsf/aster/aster_v2_dem_mosaic.vrt)
     --nextmap             Use Nextmap data (/users/rsg/arsf/nextmap/neodc/nextma
                           p_dsm_mosaic_bng.vrt)
     --srtm                Use SRTM data (/users/rsg/arsf/SRTM/global/srtm_global
                           _mosaic_1arc_v3.vrt)
     --demmosaic Input DEM mosaic
                           Input DEM mosaic. For non-standard DEM. Use "--aster"
                           or "--nextmap" for standard DEMs.
     --separation_file Seperation file
                           File with Height offset to add if "--demmosaic" is
                           used and DEM heights are not relative to WGS-84
                           elepsoid. Not required if using "--aster", "--nextmap"
                           or "--srtm" for standard DEMs.
     -b BIL Navigation Files, --bil_navigation BIL Navigation Files
                           Directory containing post-processed navigation files
                           in BIL format. By default raw navigation data will be
                           used for "--project". If this is not available (e.g.,
                           for ARSF-DAN delivered data) use this option and point
                           to "flightlines/navigation" within delivery directory
     --keepgrassdb         Keep GRASS database (default=False)
   


create_dem_from_lidar
-------------------------

.. code-block:: bash

   usage: create_dem_from_lidar.py [-h] -o Out DEM
                                   [-s Out Screenshot File or Directory]
                                   [--shadedrelief] [--las] [--ascii]
                                   [-r Resolution]
                                   [--in_projection In Projection]
                                   [--out_projection Out Projection]
                                   [-n Nav file] [-p Main project directory]
                                   [--demmosaic Input DEM mosaic] [--aster]
                                   [--nextmap] [--srtm] [--hyperspectral_bounds]
                                   [--lidar_bounds] [--fill_lidar_nulls]
                                   [-t Output raster type] [--keepgrassdb]
                                   lidarfiles [lidarfiles ...]
   
   A script to create a DEM from LiDAR data in LAS or ASCII format and optionally patch with a DEM
   
   Typical usage
   
   1) Create DEM from LiDAR files in default projection (UKBNG)
    create_dem_from_lidar.py -o lidar_dsm.dem *LAS
   
   2) Create DEM from LiDAR files in UTM30N projection
    create_dem_from_lidar.py --in_projection UTM30N -o lidar_dsm.dem *LAS
   
   3) Create DEM from LiDAR files and patch with ASTER data
   Output DEM in WGS84LL projection
    create_dem_from_lidar.py --aster --out_projection WGS84LL -o lidar_aster_dsm.dem *LAS
   
   4) Create DEM from LiDAR files and patch with ASTER data, output bounds based on navigation data.
   Output DEM in WGS84LL projection suitible for use in APL. Also export screenshot in JPEG format.
   
    create_dem_from_lidar.py --aster --out_projection WGS84LL \
               -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ \
               -o 2014_216_lidar_aster_dsm.dem \
               --screenshot /screenshots/2014_216_lidar_aster_dsm.jpg \
               ../las1.2
   
   Known issues:
   If you don't pass in the correct project path, or there is a problem
   finding hyperspectral navigation files will print warning but continue and produce
   a DEM much larger than is required. If the DEM is not required for APL you can use
   the flag '--lidar_bounds', which only uses the bounds of the lidar data, not navigation files
   plus a buffer of 2000.0 m.
   
   'create_dem_from_lidar' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
   positional arguments:
     lidarfiles            List or directory containing input LiDAR files
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out DEM, --outdem Out DEM
                           Output name for DEM
     -s Out Screenshot File or Directory, --screenshot Out Screenshot File or Directory
                           Output directory for screenshots or single file for
                           screenshot of mosaic, in JPEG format.
     --shadedrelief        Create shaded relief images for screenshots
     --las                 Input LiDAR data are in LAS format (default=True)
     --ascii               Input LiDAR data are in ASCII format (default=False)
     -r Resolution, --resolution Resolution
                           Resolution for output DEM (default=2)
     --in_projection In Projection
                           Input projection (e.g., UTM30N; default=UKBNG)
     --out_projection Out Projection
                           Out projection. Default is same as input
     -n Nav file, --nav Nav file
                           Navigation data (.sbet / .sol file) used if patching
                           with another DEM
     -p Main project directory, --project Main project directory
                           Main project directory, used if patching with another
                           DEM
     --demmosaic Input DEM mosaic
                           Input DEM mosaic to patch with in GDAL compatible
                           format. Vertical datum needs to be the same as output
                           projection. Only required for non-standard DEM. Use "
                           --aster" or "--nextmap" for standard DEMs.
     --aster               Patch with ASTER data
                           (/users/rsg/arsf/aster/aster_v2_dem_mosaic.vrt)
     --nextmap             Patch with Nextmap data (/users/rsg/arsf/nextmap/neodc
                           /nextmap_dsm_mosaic_bng.vrt)
     --srtm                Use SRTM data (/users/rsg/arsf/SRTM/global/srtm_global
                           _mosaic_1arc_v3.vrt)
     --hyperspectral_bounds
                           If patching with another DEM, get extent from
                           hyperspectral navigation data, recommended if DEM is
                           to be used with APL and navigation data are available.
                           This is the default behaviour
     --lidar_bounds        If patching with another DEM, get extent from lidar
                           data plus default buffer of 2000.0 m. If DEM is not
                           required to be used with APL this option is
                           recommended.
     --fill_lidar_nulls    Fill NULL values in LiDAR data using interpolation.
                           Not available if patching with another DEM
     -t Output raster type, --rastertype Output raster type
                           Output raster type (default DSM)
     --keepgrassdb         Keep GRASS database (default=False)
   


las_to_dsm
--------------

.. code-block:: bash

   usage: las_to_dsm.py [-h] -o Out DEM [--hillshade Out Hillshade]
                        [-r Resolution] [--projection In Projection]
                        [--method Method]
                        lasfile
   
   Create a Digital Surface Model (DSM) from a LAS file.
   
   'las_to_dsm' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
   The programs used by las_to_dsm are available under a range of licenses, please
   consult their respective documentation for more details.
   
   positional arguments:
     lasfile               Input LAS file
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out DEM, --outdem Out DEM
                           Output name for DTM
     --hillshade Out Hillshade
                           Output name for hillshade image (optional)
     -r Resolution, --resolution Resolution
                           Resolution for output DEM (default=2)
     --projection In Projection
                           Input projection (e.g., UTM30N)
     --method Method       Software package to use. Options are:
                           GRASS,SPDLib,LAStools,FUSION,points2grid
   


las_to_dtm
--------------

.. code-block:: bash

   usage: las_to_dtm.py [-h] -o Out DEM [--hillshade Out Hillshade]
                        [-r Resolution] [--projection In Projection]
                        [--method Method]
                        lasfile
   
   Create a Digital Terrain Model (DTM) from a LAS file.
   
   'las_to_dtm' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
   The programs used by las_to_dtm are available under a range of licenses, please
   consult their respective documentation for more details.
   
   positional arguments:
     lasfile               Input LAS file
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out DEM, --outdem Out DEM
                           Output name for DTM
     --hillshade Out Hillshade
                           Output name for hillshade image (optional)
     -r Resolution, --resolution Resolution
                           Resolution for output DEM (default=2)
     --projection In Projection
                           Input projection (e.g., UTM30N)
     --method Method       Software package to use. Options are:
                           GRASS,SPDLib,LAStools,FUSION,points2grid
   


las_to_intensity
------------------

.. code-block:: bash

   usage: las_to_intensity.py [-h] -o Out Intensity [-r Resolution]
                              [--projection In Projection] [--method Method]
                              lasfile
   
   Create an Intensity Raster from a LAS file.
   
   'las_to_intensity' was created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
   The programs used by las_to_intensity are available under a range of licenses, please
   consult their respective documentation for more details.
   
   positional arguments:
     lasfile               Input LAS file
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out Intensity, --outintensity Out Intensity
                           Output name for Intensity image
     -r Resolution, --resolution Resolution
                           Resolution for output image (default=2)
     --projection In Projection
                           Input projection (e.g., UTM30N)
     --method Method       Software package to use. Options are: GRASS,LAStools
   


mosaic_dem_tiles
------------------

.. code-block:: bash

   usage: mosaic_dem_tiles.py [-h] -o Out DEM demtiles [demtiles ...]
   
   mosaic_dem_tiles.py
   
   Create a mosaic from DEM tiles (e.g., ASTER / SRTM) and apply offsets
   so heights are relative to WGS-84 ellipsoid rather than geoid.
   
   Entire extent of DEM is kept. If subsetting to navigation data is required
   use 'create_apl_dem.py' instead. See example 7 in help.
   
   positional arguments:
     demtiles              Tiles to create DEM from
   
   optional arguments:
     -h, --help            show this help message and exit
     -o Out DEM, --outdem Out DEM
                           Output name for mosaiced DEM
   


load_lidar_to_grass
---------------------

.. code-block:: bash

   usage: load_lidar_to_grass.py [-h] [-r Resolution]
                                 [--projection In Projection]
                                 [-t Output raster type]
                                 lidarfiles [lidarfiles ...]
   
   Load LiDAR files into GRASS for further processing.
   
   For LAS files converts to ASCII first using las2txt.
   
   Points flagged as noise (class 7) are dropped before being added.
   
   Performs the following steps:
   
   1. Sets up GRASS database in the required projection
   2. Loads converted files using r.in.xyz
   
   Then returns the path of the database which can be opened using:
   
      grass PATH_TO_DATABASE
   
   For examples of futher processing see:
   
   https://grasswiki.osgeo.org/wiki/LIDAR
   
   Created by ARSF-DAN at Plymouth Marine Laboratory (PML)
   and is made available under the terms of the GPLv3 license.
   
   positional arguments:
     lidarfiles            List or directory containing input LiDAR files
   
   optional arguments:
     -h, --help            show this help message and exit
     -r Resolution, --resolution Resolution
                           Resolution for output DEM (default=2)
     --projection In Projection
                           Input projection (e.g., UTM30N)
     -t Output raster type, --rastertype Output raster type
                           Raster type - determines the lidar returns to load
                           into GRASS. For all select DEM (default), for first
                           only select DSM, for last only select DTM.
   


