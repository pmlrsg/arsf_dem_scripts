LiDAR Tutorials
================

Create a DSM using the command line utility
---------------------------------------------

The recomended way to create a Digital Surface Model (DSM), which represents the
top of canopy and buildings is to utilise the `create_dem_from_lidar` script
line tool. This tutorial assumes Windows is being used and GRASS has been installed
through OSGeo4W. Under Linux / OS X the script needs to be called using
`create_dem_from_lidar.py` and is run from a standard terminal.

LiDAR Only
~~~~~~~~~~~

1. Open the OSGeo4W Shell
2. Navigate to the directory the directory containing LiDAR data (in LAS or ASCII format)
e.g.,

.. code-block:: bash

   cd C:\ARSF-LiDAR\

3. Run the following command to create a DSM using only LiDAR data:

.. code-block:: bash

   create_dem_from_lidar --in_projection UKBNG \
                         --outdem lidar_dsm.dem \
                         las1.2

This will create a DSM mosaic, in ENVI format, from all 'LAS' files in the folder 'las1.2'
at the default resolution (2 m). Any points classified as noise within the LAS file
will be dropped. You can create a tiff by changing the extension of the output file to '.tif'

Note, as part of the process a text file is made from each line, dropping points classified as noise.


LiDAR and Additional DEM for APL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a DSM from the LiDAR, suitible for using in the Airborne Processing
Library to geocorrect hyperspectral data, some extra consideration are needed:

   * The DSM needs to use WGS-84 Lat/Long projection and heights need to be relative to the WGS-84 elipsoid.
   * Areas of no-data need to be filled.
   * The format needs to be ENVI Band Interleaved by Line (BIL) or Band Sequential (BSQ).

Similar to creating a DEM using only LiDAR data open the OSGeo4W Shell and navigate
to the directory containing LiDAR data. Then run the following command:

.. code-block:: bash

   create_dem_from_lidar --in_projection UKBNG \
                         --out_projection WGS84LL \
                         --demmosaic RG12_09-2014_088-ASTER.dem \
                         --lidar_bounds \
                         --outdem lidar_aster_dsm.dem \
                         lidar_files_dir

This will create a DSM mosaic from the LAS files in 'lidar_files_dir',
reproject (horizontally and vertically) to WGS84 Lat/Long and patch with
'RG12_09-2014_088-ASTER.dem', cropped to the bounding box of all LiDAR data
plus a buffer of 2 km.

This assumes the vertical datum of the data is the same as that required for the
output projection.

To use downloaded ASTER or SRTM files, which use vertical heights relative to the
geoid you can subset and reproject first.
The first step is to create a virtual raster from all downloaded tiles.

.. code-block:: bash

   gdalbuildvrt srtm_mosaic.vrt *1arc_v3.tif

The second step is to subset and apply a height offset to the DEM

.. code-block:: bash

   create_apl_dem --demmosaic strm_mosaic.vrt \
                     --separation_file geoid-spheroid/ww15mgh.grd \
                     --bil_navigation flightlines/navigation \
                     --outdem 2014_088_strm.dem

Where:

`--separation_file` is a file providing the seperation between the geoid and the spheriod.

`--bil_navigation` is a folder containing the processed BIL format nagivation files
produced by APL and supplied with delivered hyperspectral data.

Note, if running under Linux / OS X `create_apl_dem.py` needs to be used.

Create DSM / DTM using additional programs
--------------------------------------------

In addition to the default of creating a DSM using GRASS, a DSM or Digital Terrain Model (DTM)
can be created using LAStools or SPDLib if they are installed (and a license is available for LAStools).
These packages offer more advanced interpolation and classification of ground returns.

Creation of a DEM can be done in a Python script, using functions from the arsf_dem library, or through
command line tools.

Python Functions
~~~~~~~~~~~~~~~~~

To create a DSM using GRASS the following is used

.. code-block:: python

   from arsf_dem import dem_lidar
   las_to_dsm('in_las.las', 'out_dsm_grass.tif',
              resolution=2, method='GRASS')

The format of the output file is set using the extension, using '.tif' will create a GeoTIFF.
Using '.dem' will create an ENVI file.

If SPDLib is available, and the path has been set in the config file a DSM can be
created using:

.. code-block:: python

   from arsf_dem import dem_lidar
   las_to_dsm('in_las.las', 'out_dsm_spdlib.tif',
               resolution=2, method='SPDLIB')

Similarly, if LAStools are available a DSM can be created using:

.. code-block:: python

   from arsf_dem import dem_lidar
   las_to_dsm('in_las.las', 'out_dsm_lastools.tif',
              resolution=2, method='LASTOOLS')

Note, if you don't have a license for LAStools, this command will still run but will introduce
artefacts, such as diagonal black lines.

You can use these Python functions to iterate through a list of files within a
Python script and create a DSM for each. For example:

.. code-block:: python

   import os
   import glob
   from arsf_dem import dem_lidar

   # Search current directory for all files ending matching '*.LAS'
   in_las_list = glob.glob('*.LAS')

   # Iterate through list of files found
   for in_las in in_las_list:
      # Set name of output DEM as the same as LAS file
      # but with '_dsm.tif' suffix
      out_dsm_basename = os.path.splitext(os.path.split(in_las)[-1])[0]
      out_dsm = os.path.join(out_dir, out_dsm_basename + '_dsm.tif')

      # Run function to create DSM
      dem_lidar.las_to_dsm(in_las,out_dsm)

To create a DTM a similar function las_to_dtm is used. When the method is GRASS this just takes the last
return. When SPDLib or LAStools are used a progressive morphology filter is used to classify ground
returns and a DTM is generated by interpolating these points.

.. code-block:: python

   from arsf_dem import dem_lidar
   # GRASS
   las_to_dtm('in_las.las', 'out_dtm_grass.tif',
              resolution=2, method='GRASS')
   # SPDLib
   las_to_dtm('in_las.las', 'out_dtm_spdlib.tif',
              resolution=2, method='SPDLIB')
   # LAStools
   las_to_dtm('in_las.las', 'out_dtm_lastools.tif',
              resolution=2, method='LASTOOLS')

Command line tools
~~~~~~~~~~~~~~~~~~~

Two utility command line tools are provided to call the Python functions for
producing a DSM / DTM `las_to_dsm` and `las_to_dtm`. Usage is:

.. code-block:: bash

   las_to_dsm -o out_dsm.tif \
              --projection UTM30N \
              in_las.las




