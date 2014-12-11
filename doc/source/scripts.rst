ARSF DEM Scripts
================

create_apl_dem.py
-------------------

A script to create a DEM for use in APL subset to bounds
of hyperspectral navigation data.

Typical usage

1) Create Next map DEM

 create_apl_dem.py --nextmap -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_nextmap.dem

2) Create ASTER DEM

 create_apl_dem.py --aster -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ -o 2014_216_nextmap.dem

Known issues:
If you don't pass in the correct project path, or there is a problem 
finding hyperspectral navigation files will print warning but continue and produce 
a DEM much larger than is required.

create_dem_from_lidar.py
-------------------------

A script to create a DEM from LiDAR data in LAS or ASCII format and optionally patch with a DEM

Typical usage

1) Create DEM from LiDAR files in default projection (UKBNG)
 create_dem_from_lidar.py -o lidar_dsm.dem \*LAS

2) Create DEM from LiDAR files and patch with ASTER data
Output DEM in WGS84LL projection
 create_dem_from_lidar.py --aster --out_projection WGS84LL -o lidar_aster_dsm.dem \*LAS

3) Create DEM from LiDAR files and patch with ASTER data, output bounds based on navigation data.
Output DEM in WGS84LL projection suitible for use in APL. Also export screenshot in JPEG format.

 create_dem_from_lidar.py --aster --out_projection WGS84LL \
            -p /users/rsg/arsf/arsf_data/2014/flight_data/arsf_internal/GB14_00-2014_216_Little_Riss_Fenix/ \
            -o 2014_216_lidar_aster_dsm.dem \
            --screenshot /screenshots/2014_216_lidar_aster_dsm.jpg \
            ../las1.2

Known issues:
If you don't pass in the correct project path, or there is a problem 
finding hyperspectral navigation files will print warning but continue and produce 
a DEM much larger than is required.

create_intensity_from_lidar.py
--------------------------------

A script to create intensity images from LiDAR data in LAS or ASCII format and optionally patch with a DEM

Typical usage:

 create_intensity_from_lidar.py --screenshot screenshots_dir -o lidar_intensity.tif lidar_dir

