#! /usr/bin/env python
# grass_library
#
# Created by Stephen Goult 2014
#
# Modified by Dan Clewley (dac) to
# become part of arsf_dem library
#
# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
A Python library of useful grass functions, these are built from the grass python scripting library. (advanced sysopen calls mostly)
Nothing needs to be done to use these inside of grass, they will work as default. To have the script work externally you MUST run grass db setup. Your imports will also need to include the following::

   import os, sys, argparse
   sys.path.append('/usr/lib64/grass/etc/python/')
   import grass.script as grass
   import grass.script.setup as gsetup

or use setGrassPythonLoc after import sys.

Most of these functions should work in grass 7 if we update to that.

Available functions:

* grassDBsetup: Open and create an instance of grass for scripting. Must be run before anything else or grass will have a fit.
* setGrassQuiet: Set grass verbosity level.
* setGrassPythonLoc: place in imports to make grass.script work.
* createTiffDem: Create a dem from a list of tiles and a spheroid file.
* readAsciiLidar: Read and patch together a series of ascii lidar files.
* readDem: Read a dem file, works with all gdal types.
* checkDemProj: Check the projection of a dem file.
* setLocation: Uses the dem location to create a location in grassDB
* newLocation: Creates location in grassDB from given projection.
* reproject: Projects between locations and projection types.
* mapCalculate: Calculates 2 maps according to formula.
* modalavg: Finds mode of a map file.
* createComparisonDem: Takes one dem from another.
* univariates: Finds univariate stats (min max mean, median std dev etc).
* openPngMonitor: Opens a png writing monitor for outputing images.
* outputpng: Outputs png of dem using pngmonitor.
* histogram: Outputs png of histogram using pngmonitor.
* closePngMonitor: Closes png monitor and writes commands.
* cleanup: Cleans out map files used in program.
* grass_location_to_proj4: Convert GRASS style projection to Proj4 format
* proj4_to_grass_location: Convert Proj4 projection to GRASS style
* grass_location_to_wkt: Convert GRASS style projection to WKT
* checkFileExists: Check a file exists within GRASS
* convertVectorXYZtoSHP: Convert csv file of points to shapefile
* importVectors: Import OGR supported vectors into GRASS database
* overlayVectorsOnRaster: Function to patch rasters
* createMosaicFromRastersAndVectors: Create mosaic from all rasters & vectors in mapset
* setNull: Set the null value for a raster
* locationFromFile: Create a GRASS location from a file
* rescale: Rescale a raster (or group)
* rescaleRGB: Rescale 3 bands and return as an RGB group
* rasterWithMapsetName: Append the mapset name to a raster
* SetRegion: Set the region based on given bounds or a raster
* importGdal: Import a GDAL supported raster
* splitGroupIntoRasters: Split the given group into individual rasters
"""

################################################################################
###################################Imports######################################
################################################################################
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys, re
import subprocess
# Import from arsf_dem
from . import dem_common_functions
from . import dem_common

# Check DEM library is available
# this is only used on ARSF systems
HAVE_DEM_LIBRARY = True
try:
    import dem_library
except ImportError as err:
    HAVE_DEM_LIBRARY = False

try:
    import hdr_files
except Exception as err:
    pass

#gives us access to grass and its pythony bits
sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)
try:
    import grass.script as grass
    import grass.script.setup as gsetup
except ImportError as err:
    print("Could not import grass library. Try setting 'GRASS_PYTHON_LIB_PATH' environmental variable.", file=sys.stderr)
    print(err, file=sys.stderr)
    sys.exit(1)
import shutil
import time
import numpy
import tempfile
# Try to import GDAL
HAVE_GDAL=True
try:
    from osgeo import gdal
    from osgeo import osr
except ImportError:
    # If can't import don't complain until GDAL is actually needed
    HAVE_GDAL=False

################################################################################
###############################Global Variables#################################
################################################################################
#You'll be told repeatedly the script needs to be run inside of grass if this is wrong.
GISBASE = os.environ['GISBASE'] = dem_common.GRASS_LIB_PATH

################################################################################
###############################Grass Setup Functions############################
################################################################################

def _remove_leading_trailing_quotes(in_string):
    """
    Check if string contains leading or trailing quotes
    and remove them
    """
    # Leading quotes
    if in_string[0] == '"' or in_string[0] == '\'':
        in_string = in_string[1:]
    # Trailing quotes
    if in_string[-1] == '"' or in_string[-1] == '\'':
        in_string = in_string[:-1]

    return in_string

def grassDBsetup():
    """Function grassDBsetup

       Sets up a temporary folder by copying the template database for grass.
       Gsetup is a grass function, which creates a temporary grassrc for this session
       and initialises grass for interaction.

       Arguments:

       Returns: The created grass database location
    """
    pid = os.getpid()
    t = time.strftime("%H%M%S")
    tempfolder = "grassdb-%s-%s" % (pid,t)
    tempfolder = os.path.join(dem_common.TEMP_PATH,tempfolder)
    print("Grass database created at: {}".format(tempfolder))
    shutil.copytree(dem_common.GRASS_DATABASE_TEMPLATE,
                    tempfolder)
    gisdbase = os.path.join(tempfolder)
    location = "WGS84LL"
    mapset   = "PERMANENT"
    gsetup.init(GISBASE,
                gisdbase,
                location,
                mapset)
    return tempfolder

def setGrassQuiet(verbosity=0):
    """Function grassDBsetup

       sets grass verbosity. 0 minimum (errors only), 3 maximum (completion,
       commands etc)

       Arguments:
                v: verbosity, set between 0 and 3 (0 being silent, 3 being noisy)

       Returns:
    """
    os.environ['GRASS_VERBOSE']=str(verbosity)

def setGrassPythonLoc():
    """Function setGrassPythonLoc
    gives us access to grass and its python bits, run in imports after sys
    """
    sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)


################################################################################
###############################Import Functions#################################
################################################################################

def createTiffDem(tilelist, outname, spheroidfile):
    """Function createTiffDem

       Takes a list of geotiff tile locations then patches them together and adds a
       spheroid file on top. This can be used repeatedly and should clean up after
       itself.

       Arguments:
                tilelist:list of tiles to import, usually generated by demgen.py
                outname:output dem name
                spheroidfile: spheroid geoid file, for heights

       Returns:
    """
    #since it's the first run for this tile list
    tiles = []
    print("Creating patched version of tiles")
    if len(tilelist) != 1:
        for tile in tilelist:
            tilename=os.path.basename(tile)
            print(tilename)
            #import the tile
            try:
                grass.run_command("r.in.gdal",
                                     input=tile,
                                     output=tilename,
                                     overwrite=True,
                                     flags='e',
                                     quiet=False)

            except:
                dem_common_functions.WARNING("This tile %s was not imported, might not exist?" % tile)
                continue
            tiles.append(tilename)
        #if tiles is empty no tiles were imported :(
        if tiles == 0:
            raise Exception

        grass.run_command("g.region",
                          rast=tiles,
                          quiet=True)
        #has to be run after g.region else results in nulls.
        grass.run_command("r.patch",
                          input=tiles,
                          output="patched_tiles",
                          overwrite=True,
                          flags="z")
    else:
        grass.run_command("r.in.gdal",
                          input=tilelist[0],
                          output="patched_tiles",
                          overwrite=True,
                          flags='e')

    #attach spheroid so that heights will be correct.
    grass.run_command('r.in.ascii',
                      input=spheroidfile,
                      output=os.path.basename(spheroidfile),
                      overwrite=True)
    grass.run_command('r.mapcalculator',
                      formula="A+B",
                      amap="patched_tiles",
                      bmap=os.path.basename(spheroidfile),
                      outfile=outname,
                      overwrite=True)
    print("tile dem created, proceeding")
#end function

def readLidar(lasfolder,location=None,patch=True,datacolumn=dem_common.LIDAR_ASCII_ORDER['z'],resolution=2):
    """Function readLidar

       Can be used to read in a directory of LiDAR files whether LAS or ASCII or mixed.
    """
    lasfiles=[]
    asciifiles=[]
    if type(lasfolder) is str and os.path.isdir(lasfolder):
        filelist=dem_common_functions.FileListInDirectory(lasfolder)
    elif type(lasfolder) is str and os.path.isfile(lasfolder):
        filelist=[lasfolder]
    elif type(lasfolder) is list:
        filelist=lasfolder
    else:
        dem_common_functions.ERROR("lasfolder should be a file or directory path, or a list of files. I got %s"%lasfolder)
        return None

    for item in filelist:
        if item.endswith('.TXT') or item.endswith('.txt'):
            asciifiles.append(item)
        elif item.endswith('.LAS') or item.endswith('.las'):
            lasfiles.append(item)
        else:
            dem_common_functions.WARNING("Unrecognised file in lidar directory: %s"%item)

    #to store the returned varaibles from the readasciilidar + readlaslidar
    lasreturns=[]
    asciireturns=[]
    return_lasfiles=[]
    return_patched_las=[]

    if len(lasfiles)!=0:
        lasreturns=readLasLidar(lasfiles,location=location,patch=patch,datacolumn=datacolumn,resolution=resolution)

    if len(asciifiles)!=0:
        asciireturns=readAsciiLidar(asciifiles,location=location,patch=patch,datacolumn=datacolumn,resolution=resolution)

    #Is there a better way to do this. Need to combine returns from both calls into one list for each item returned
    if len(lasreturns) > 0:
        return_lasfiles=lasreturns[0]
        return_patched_las=[lasreturns[1]]

    if len(asciireturns) > 0:
        return_lasfiles.extend(asciireturns[0])
        return_patched_las.append(asciireturns[1])

    return return_lasfiles,return_patched_las


#Note this is just a wrapper that converts the las to ascii and calls readAsciiLidar
def readLasLidar(lasfolder,location=None,patch=True,datacolumn=dem_common.LIDAR_ASCII_ORDER['z'],resolution=dem_common.DEFAULT_LIDAR_RES_METRES):
    """Function readLasLidar

       Wrapper to convert LAS files into ASCII LiDAR files and then call readAsciiLidar

       Arguments:
                lasfolder: folder (or single file) of LAS files
                location: location (projection) to import to (if not the current one)
                patch: whether to mosaic the images (patch the rasters) or not
                datacolumn: which column from ascii csv to import (default is 'z')

       Returns: list of grass internal raster names
    """
    #Create a tmp folder for storing the ascii files
    tempdir=tempfile.mkdtemp(dir=dem_common.TEMP_PATH)

    from .dem_lidar import lastools_lidar
    lastools_lidar.convert_las_to_ascii(lasfolder, tempdir)

    #Call readAsciiLidar on the files
    out_grass_names = readAsciiLidar(tempdir,location=location,patch=patch,datacolumn=datacolumn,resolution=resolution)

    # Remove temp file with ASCII files (now all imported to GRASS)
    shutil.rmtree(tempdir)

    return out_grass_names


def readAsciiLidar(lasfolder, location=None,patch=True,datacolumn=dem_common.LIDAR_ASCII_ORDER['z'],resolution=2,ignoreclassification=True):
    """Function readAsciiLidar

       Read Ascii lidar files, must have a UTM location or OSGB location to import
       to and grass must be primed using g.gisenv (use newlocation() to create one).
       WGS84LL will not work. Don't try.

       Arguments:
                lasfolder: folder (or single file) of ASCII lidar files
                location: location (projection) to import to (if not the current one)
                patch: whether to mosaic the images (patch the rasters) or not
                datacolumn: which column from ascii csv to import (default is 'z')

       Returns: list of grass internal raster names
    """

    if not HAVE_DEM_LIBRARY:
        raise ImportError('Could not import "dem_library", check "PYTHONPATH"')

    #get las bounds (from lasinfo?) subprocess.Popen(etc...
    lasfiles = []
    if location is not None:
        # take the origin location to reset at the end
        orig_loc = grass.read_command('g.gisenv', get="LOCATION_NAME").replace('\n','')
        setLocation(location)

    print("Importing Ascii lidar")
    #if lasfolder is a folder get the file list - else create a list with just the lasfolder FILE
    if type(lasfolder) is list:
        #is a list of files
        filelist=lasfolder
    elif os.path.isdir(lasfolder):
        #is a directory name
        filelist=os.listdir(lasfolder)
        filelist=[os.path.join(lasfolder,x) for x in filelist]
    else:
        #is a single file
        filelist=[lasfolder]

    for lasfile in filelist:
        bounds = dem_library.getASCIIBounds(lasfile)
        print(bounds)
        grass.run_command('g.region',
                          res=resolution,
                          n=bounds[3],
                          s=bounds[2],
                          e=bounds[1],
                          w=bounds[0],)

        if ignoreclassification:
            updatedfilename=tempfile.mkstemp()[1]
            removeASCIIClass(lasfile, updatedfilename)
        else:
            updatedfilename=lasfile

        #currently our ascii LAS files use xyz columns of 2 3 and 4 (referenced to 1) respectively.
        grass.run_command('r.in.xyz',
                          input=updatedfilename,
                          output=os.path.basename(lasfile),
                          fs=' ',
                          x=dem_common.LIDAR_ASCII_ORDER['x'],
                          y=dem_common.LIDAR_ASCII_ORDER['y'],
                          z=datacolumn,
                          overwrite = True)
        lasfiles.append(os.path.basename(lasfile))

        # Remove temp file created
        if ignoreclassification:
            os.remove(updatedfilename)

    if patch is True:
        print("Patching lidar together...")
        patched_las='las_patched'
        grass.run_command('g.region', rast=lasfiles)
        grass.run_command('r.patch', input=lasfiles, output=patched_las, overwrite = True)
    else:
        patched_las=None

    if location is not None:
        #resets to original location
        grass.run_command('g.gisenv', set="LOCATION_NAME=%s" % (orig_loc))

    #return the list of grass internal raster names
    return lasfiles,patched_las

#end function

def removeASCIIClass(filename, newfilename, drop_class=7, keep_class=None, first_only=False, last_only=False):
    """
    Function to copy points from one ascii file to another, dropping
    points with a given classification.

    Under Linux/OS X uses awk to remove class which takes about half the time.

    Arguments:

    * filename - Input file.
    * newfilename - Output file.
    * drop_class - Classification to drop (default = 7)

    Returns:

    * None

    """
    if (drop_class is not None) and (keep_class is not None):
        raise Exception('Setting both a class to drop and keep makes no sense!')
    if first_only and last_only:
        raise Exception('Setting "first_only" and "last_only" makes no sense!')

    if not os.path.isfile(filename):
        raise Exception('Could not find input file "{}"'.format(filename))

    if not os.path.isdir(os.path.split(newfilename)[0]):
        raise Exception('Output directory "{}" does not exist'.format(os.path.split(newfilename)[0]))

    print('Updating "{}" to file "{}". '.format(filename, newfilename),end='')

    awk_select = '1'

    if drop_class is not None:
        print('Removing classification {}. '.format(drop_class),end='')
        # Convert drop_class to int as will raise exception if it can't be converted
        awk_select += ' && ${} != {}'.format(dem_common.LIDAR_ASCII_ORDER['classification'],int(drop_class))
    elif keep_class is not None:
        print('Keeping classification {}. '.format(keep_class),end='')
        # Convert keep_class to int as will raise exception if it can't be converted
        awk_select += ' && ${} == {}'.format(dem_common.LIDAR_ASCII_ORDER['classification'],int(keep_class))
    if first_only:
        print('Keeping only first returns.')
        awk_select += ' && ${} == 1'.format(dem_common.LIDAR_ASCII_ORDER['returnnumber'])
    elif last_only:
        print('Keeping only last returns.')
        awk_select += ' && ${} == ${}'.format(dem_common.LIDAR_ASCII_ORDER['returnnumber'],
                                              dem_common.LIDAR_ASCII_ORDER['numberofreturns'])
    else:
        print('')

    # Convert to string of not None.
    if drop_class is not None:
        drop_class = str(drop_class)
    if keep_class is not None:
        keep_class = str(keep_class)

    # If not on windows use awk, which looks messy but is about twice the speed
    if sys.platform != 'win32':
        awk_command = "cat {0} | awk '{{ if({1}) print $0 }}' > {2}".format(filename,
                                                                     awk_select,
                                                                     newfilename)
        # Need shell=True for this to work, all inputs are checked first
        try:
            subprocess.check_call(awk_command, shell=True)
        except subprocess.CalledProcessError:
            dem_common_functions.ERROR('Error running command: {}'.format(awk_command))
            raise
    else:
        fin=open(filename)
        fout=open(newfilename,'w')

        for line in fin.readlines():
            writeLine = False
            classCheck = False
            elements = line.split()
            # Check class
            if (drop_class is not None) and (elements[dem_common.LIDAR_ASCII_ORDER['classification']-1] != drop_class):
                classCheck = True
            elif (keep_class is not None) and (elements[dem_common.LIDAR_ASCII_ORDER['classification']-1] == keep_class):
                classCheck = True

            # Check return
            if classCheck:
                if first_only:
                    if elements[dem_common.LIDAR_ASCII_ORDER['returnnumber']-1] == '1':
                        writeLine = True
                elif last_only:
                    if elements[dem_common.LIDAR_ASCII_ORDER['returnnumber']-1] == elements[dem_common.LIDAR_ASCII_ORDER['numberofreturns']-1]:
                        writeLine = True
                else:
                    writeLine = True

            if writeLine:
                fout.write(line)

        fin.close()
        fout.close()

    return newfilename


def readDem(demfile):
    """Function readDem

       Read a dem file and return useful information about it

       Arguments:
                demfile: a valid path to a demfile

       Returns:
             demname: the basename used in grass to represent this file
             dem_proj: the projection of the dem (w
             dem_location
    """
    if os.path.isfile(demfile):
        #test what kind of dem it is, then create a new location if needed
        #replace - with _ for safety with mapcalc
        demname = os.path.basename(demfile).replace("-","_")
        dem_proj = getGRASSProjFromGDAL(demfile)
        dem_location = setLocation(dem_proj)
        grass.run_command('r.in.gdal',
                    input = demfile,
                    output=demname,
                    overwrite=True)

        return demname, dem_proj, dem_location
    else:
        raise ValueError("There was a problem reading the DEM! Please check it exists and that it has a hdr file connected to it.")
#end function


################################################################################
###############################Projection Functions#############################
################################################################################

def checkDemProj(dem):
    """Function checkDemProj

       Checks the projection of an ENVI dem file and its header.

       DEPRECATED: Use getGRASSProjFromGDAL instead

       Arguments:
                dem: dem file to check

       Returns: Dem projection
    """
    header_file = os.path.splitext(dem)[0] + ".hdr"
    header = hdr_files.DemHdr(header_file)
    if header.projection == "Geographic Lat/Lon":
        proj = "WGS84LL"
    elif header.projection == "Transverse Mercator":
        proj = "UKBNG"
    elif header.projection == "UTM":
        proj = "UTM%s%s" % (header.utmGrid, header.utmNS[:1])
    else:
        print("I can't identify the projection from the .hdr file")
        proj = None
    return proj
#end function

def getGRASSProjFromGDAL(in_file):
    """
    Gets GRASS location name from image
    using GDAL (if GDAL Python bindings are available).

    Similar to 'checkDemProj but tries to be more general
    by using GDAL to read projection information and osr to
    pull out relevant attributes.

    Arguments:

    * in_file - input GDAL dataset

    Returns:

    * grass style projection (e.g., UKBNG)

    """
    # Check if GDAL was imported
    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL Python bindings')

    gdaldataset = gdal.Open(in_file,gdal.GA_ReadOnly)

    proj_wkt = gdaldataset.GetProjectionRef()
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromWkt(proj_wkt)

    utmZone = spatial_ref.GetUTMZone()
    projection = spatial_ref.GetAttrValue('PROJECTION')
    spheroid = spatial_ref.GetAttrValue('SPHEROID')
    grass_proj = None
    if utmZone != 0:
        # If positive North
        if utmZone > 0:
            utmZone_str = str(utmZone).zfill(2)
            grass_proj = "UTM%sN" % (utmZone_str)
        # If negative South
        else:
            utmZone = utmZone * -1
            utmZone_str = str(utmZone).zfill(2)
            grass_proj = "UTM%sS" % (utmZone_str)
    elif projection is None:
        grass_proj = "WGS84LL"
    # Check for BNG
    elif ((projection.lower() == "transverse_mercator") or \
             (projection.lower() == "transverse mercator")) and \
             (spheroid.lower().find("airy") > -1):
        grass_proj = "UKBNG"
    else:
        gdaldataset = None
        raise Exception('Could not identify projection from file.\n' +
                       'WKT string is: {}'.format(spatial_ref.ExportToPrettyWkt()))

    gdaldataset = None
    return grass_proj


def setLocation(projection):
    """Function setLocation

       Takes a projection from and either sets or creates a new location
       in the grass DB

       Arguments:
                projection: projection to switch to or create location for

       Returns: The location switched to, or created
    """
    if projection == "WGS84LL":
        location = projection
    elif projection == "UKBNG":
        location = projection
    elif 'UTM' in projection:
        location = newLocation(projection)
    else:
        # If the projection is not the expected GRASS location format
        # try as a proj4 string.
        try:
            location = newLocation(projection)
        except Exception:
            dem_common_functions.ERROR("No recognisable projection given")
            location = None
    if location is not None:
        grass.run_command('g.gisenv',
                    set="LOCATION_NAME=%s" % (location))
    return location
#end function

def newLocation(projection):
    """
    Function newLocation

    Creates a new location from a GRASS type projection or
    Proj4 string. Checks for a valid proj4 string using
    'proj4_to_grass_location'.

    Currently only works with UKBNG, WGS84LL and UTM

    Arguments:

    * projection: projection to create new location can be
                         proj4 string or GRASS style projection name
                         (e.g., UKBNG)

    Returns:

    * GRASS style projection name for use with g.gisenv

    """
    try:
        grass_loc = proj4_to_grass_location(projection)
        proj4_str = projection
    except Exception:
        grass_loc = projection
        proj4_str = grass_location_to_proj4(grass_loc)

    grass.run_command('g.proj',
                         flags='c',
                         proj4=proj4_str,
                         location=grass_loc)
    return grass_loc
#end function

def reproject(project_map, project_from, mapset, output_map, vertical_reproject=True):
    """
    Function reproject

    Take a map and the location FROM which to project it, the mapset it is
    held in and a name to project it to. Output in current location.

    Arguments:

    * project_map - map name to reproject
    * project_from - location to reproject from
    * mapset - mapset in location, usually PERMANENT
    * output_map-  output name in current location

    Returns:

    * None

    """
    print("Reprojecting")
    seperation="seperation"
    #switch to the location to project from
    output_loc = grass.read_command('g.gisenv',
                                     get="LOCATION_NAME").replace('\n','')
    grass.run_command('g.gisenv',
                      set="LOCATION_NAME=%s" % (project_from))
    grass.run_command('g.region',
                      rast=project_map)

    #create a map of the current region, to set in the destination mapset.
    grass.run_command('v.in.region',
                      output='vector_box',
                      type='area',
                      overwrite = True)

    #switch to the output location
    grass.run_command('g.gisenv', set="LOCATION_NAME=%s" % (output_loc))

    #project the vector to set the region
    grass.run_command('v.proj',
                      input='vector_box',
                      location=project_from,
                      mapset=mapset,
                      output='vector_box_1',
                      overwrite = True)

    # -a sets the region resolution based on the size of the vector.
    grass.run_command('g.region',
                      vect='vector_box_1',
                      flags='a')

    # reproject the map then output it as whatever.
    grass.run_command('r.proj',
                      input=project_map,
                      location=project_from,
                      mapset=mapset,
                      output=output_map,
                      overwrite = True)
    if project_from == 'UKBNG' and output_loc == 'WGS84LL' and vertical_reproject:
        grass.run_command("r.external",
                       input=dem_common.UKBNG_SEP_FILE_WGS84,
                       output=seperation,
                       overwrite=True,
                       flags='e')
        mapCalculate(output_map, seperation, "A+B", output_map)

    elif project_from == 'WGS84LL' and output_loc == 'UKBNG' and vertical_reproject:
        grass.run_command("r.external",
              input=dem_common.UKBNG_SEP_FILE_UKBNG,
              output=seperation,
              overwrite=True,
              flags='e')
        mapCalculate(output_map, seperation, "A-B", output_map)
#end function

def grass_location_to_proj4(in_grass_proj):
    """
    Converts GRASS location name (e.g., UKBNG)
    to a Proj4 string.

    If Proj4 string is passed in, will just return it.

    Arguments:

    * in_grass_proj - Input GRASS location name

    Returns:

    * Proj4 string

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    spatial_ref = osr.SpatialReference()

    # Check if Proj4 string was passed in - if so just return it
    if spatial_ref.ImportFromProj4(_remove_leading_trailing_quotes(in_grass_proj)) == 0:
        return _remove_leading_trailing_quotes(in_grass_proj)
    elif in_grass_proj == 'UKBNG':
        return dem_common.OSTN02_PROJ4_STRING
    elif in_grass_proj == 'WGS84LL':
        return dem_common.WGS84_PROJ4_STRING
    elif in_grass_proj[0:3] == 'UTM':
        if in_grass_proj[-1] == 'N':
            epsg_code = 32600 + int(in_grass_proj[3:5])
        elif in_grass_proj[-1] == 'S':
            epsg_code = 32700 + int(in_grass_proj[3:5])
        else:
            raise Exception('UTM projection must end in "N" or "S"')
        spatial_ref.ImportFromEPSG(epsg_code)
        return spatial_ref.ExportToProj4()
    else:
        raise Exception('Could not determine projection for {}'.format(in_grass_proj))

def grass_location_to_wkt(in_grass_proj, outfile=None):
    """
    Converts GRASS location name (e.g., UKBNG)
    to a WKT string / File.

    If Proj4 string is passed in will create WKT file from this.

    Arguments:

    * in_grass_proj - Input GRASS location name.
    * outfile (optional) - File to save wkt string to.

    Returns:

    * wkt string

    """

    if in_grass_proj is not None:
        in_grass_proj = str(in_grass_proj)

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    spatial_ref = osr.SpatialReference()
    # Check if Proj4 string was passed in
    if spatial_ref.ImportFromProj4(_remove_leading_trailing_quotes(in_grass_proj)) == 0:
        spatial_ref.ImportFromProj4(_remove_leading_trailing_quotes(in_grass_proj))
    elif in_grass_proj == 'UKBNG':
        spatial_ref.ImportFromProj4(dem_common.OSTN02_PROJ4_STRING)
    elif in_grass_proj == 'WGS84LL':
        spatial_ref.ImportFromProj4(dem_common.WGS84_PROJ4_STRING)
    elif in_grass_proj[0:3] == 'UTM':
        if in_grass_proj[-1] == 'N':
            epsg_code = 32600 + int(in_grass_proj[3:5])
        elif in_grass_proj[-1] == 'S':
            epsg_code = 32700 + int(in_grass_proj[3:5])
        else:
            raise Exception('UTM projection must end in "N" or "S"')
        spatial_ref.ImportFromEPSG(epsg_code)
    else:
        raise Exception('Could not determine projection for {}'.format(in_grass_proj))

    wkt_str = spatial_ref.ExportToWkt()

    # If output file is provided write WKT string to it
    if outfile is not None:
        out_wkt = open(outfile,'w')
        out_wkt.write(wkt_str)
        out_wkt.close()

    return wkt_str

def proj4_to_grass_location(in_proj4):
    """
    Converts Proj4 string to GRASS location name
    (e.g., UKBNG)

    Arguments:

    * in_proj4 - Input GRASS location name

    Returns:

    * GRASS location name string

    """

    if not HAVE_GDAL:
        raise ImportError('Could not import GDAL')

    # Check if Proj4 string is within quotes
    # remove if so.
    in_proj4 = _remove_leading_trailing_quotes(in_proj4)

    spatial_ref = osr.SpatialReference()
    osr_out = spatial_ref.ImportFromProj4(in_proj4)

    if osr_out != 0:
        raise Exception('Could not create projection. '\
                       'Is "{}" a valid proj4 string'.format(in_proj4))

    utmZone = spatial_ref.GetUTMZone()
    projection = spatial_ref.GetAttrValue('PROJECTION')
    spheroid = spatial_ref.GetAttrValue('SPHEROID')
    grass_proj = None

    if utmZone != 0:
        # If positive North
        if utmZone > 0:
            utmZone_str = str(utmZone).zfill(2)
            grass_proj = "UTM%sN" % (utmZone_str)
        # If negative South
        else:
            utmZone = utmZone * -1
            utmZone_str = str(utmZone).zfill(2)
            proj = "UTM%sS" % (utmZone_str)
    elif projection is None:
        grass_proj = "WGS84LL"
    # Check for BNG
    elif ((projection.lower() == "transverse_mercator") or \
             (projection.lower() == "transverse mercator")) and \
             (spheroid.lower().find("airy") > -1):
        grass_proj = "UKBNG"
    else:
        dem_common_functions.WARNING('''Could not determine GRASS location name from:

  {}

  Setting to 'UNKNOWN'
  '''.format(in_proj4))
        grass_proj = "UNKNOWN"

    return grass_proj


################################################################################
###############################Calculation Functions############################
################################################################################

def modalavg(raster):
    """Function modalavg

       Finds the modal average using r.stats to find most commonly occuring value.
       This could be done with numpy to read the entire dem, but risks massive use
       of memory. (read: makes this function really really slow)

       Arguments:
                raster: input raster to average.

       Returns:
             mode: modal average
             modevalue: number of cells this value is found in
    """
    parseout = grass.parse_command('r.stats',
                                   input=raster,
                                   flags='Acn',
                                   #increase nsteps for greater accuracy
                                   nsteps='100',
                                   fs=',')
    cellcounts = numpy.genfromtxt(parseout,
                                  delimiter=',')
    #split the array vertically
    cellsplit = numpy.split(cellcounts,
                            2,
                            axis=1)
    #find the highest number in the arrays
    cellmax = numpy.amax(cellsplit,
                         axis = 1)
    #check the second array (the cell counts) against the array itself for the cell index
    countindex = numpy.where(cellmax[1]==cellcounts)
    cell=countindex[0]
    mode = str(cellcounts[cell, 0])
    modevalue = str(cellmax[1])
    return mode.strip("[]"), modevalue.strip("[]")
#end function

def mapCalculate(A, B, formula, output):
    """Function mapCalculate

       Calculates 2 input maps according to the formula given, outputs to selected name

       Arguments:
                A:Map A
                B:Map B
                formula: Formula to calculate, e.g. A - B, B -A, A + B etc
                output: Name of the raster name to output

       Returns:
    """
    grass.run_command('g.region',
                      rast=A)
    grass.run_command('r.mapcalculator',
                      formula=formula,
                      amap=A,
                      bmap=B,
                      outfile=output,
                      overwrite = True)

def createComparisonDem(base, inputdem, output):
    """Function createComparisonDem

       Subtracts one dem from another then cleans a nameholder.
       Make sure the dems are the right way round, inputdem will set the region size so
       anything outside of this is likely to be ignored by mapcalc.

       Arguments:
                base: reference dem
                inputdem: dem to be subtracted from
                output: output name

       Returns:
    """
    #spheroid first since it's the original
    grass.run_command('g.region',
                      rast=inputdem)
    grass.run_command('r.mapcalculator',
                      formula="A-B",
                      amap=base,
                      bmap=inputdem,
                      outfile=output,
                      overwrite = True)
#end function

################################################################################
###############################Analysis Functions###############################
################################################################################

def univariates(raster):
    """Function univariates

       Hands a name to r.univar and tries to recieve statistics. If extended stats
       fails will try with standard univar, if that fails then there is something
       very wrong with the map being used.

       Arguments:
                raster: raster map to use from grass.

       Returns:
             Stats: dictionary type of the returned statistics
    """
    stats = grass.parse_command('r.univar',
                                  map=raster,
                                  flags='ge',
                                  quiet=True)
    try:
        minimum = stats['min']
    except KeyError:
        stats = grass.parse_command('r.univar', map=raster, flags='g', quiet=True)
    return stats
#end function

################################################################################
###############################Output Functions#################################
################################################################################

def outputpng(dem, output):
    """Function outputpng

       Creates a png of the dem given at a specified location. Uses grass display
       monitors to save memory

       Arguments:
                dem: the dem being pngified
                output: the location and name of the output. Include file
                        extension

       Returns:
    """
    openPngMonitor('1280', '960', output)
    grass.run_command('d.rast',
                      map=dem)
    closePngMonitor()
#end function

def histogram(dem, output):
    """Function histogram

       Creates a histogram of the selected dem, runs openmonitor first. Check that
       you don't have a monitor already open or this will lock up.

       Arguments:
                dem: the dem being histogrammed
                output: the location and name of the output. Include file extension.

       Returns:
    """
    openPngMonitor('640', '480', output)
    grass.run_command('d.histogram',
                      map=dem)
    closePngMonitor()
#end function

def openPngMonitor(width, height, output):
    """Function openPngMonitor

       opens a png monitor to be written to, this will accept as many commands as it is
       given.

       Arguments:
                width: width in pixels, default is 640
                height: height in pixels, default is 480
                output: the location and name of the output. Include file extension.

       Returns:
    """
    os.environ['GRASS_HEIGHT'] = height
    os.environ['GRASS_WIDTH'] = width
    os.environ['GRASS_PNGFILE'] = output
    grass.run_command('d.mon',
                      start='PNG')
#end function

def closePngMonitor():
    """Function closePngMonitor

       Closes the png monitor, all actions performed since png monitor was opened are written
       to the file specified in openPngMonitor.

       Arguments:

       Returns:
    """
    grass.run_command('d.mon',
                      stop='PNG')
#end function

def outputToGDAL(inputname,outputname,imtype='JPEG',nodata=0,datatype='Byte',setregiontoimage=False,resolution=None,tidyup=True):
    """Function outputToGDAL

       Write out a raster data set to a GDAL supported file type
       If output type is JPEG checks number of cells is less than allowed limit.
       Decreases resolution until it is.
    """
    #Set the output region to the raster if requested
    if setregiontoimage:
        SetRegion(rast=inputname)

    #update the resolution if requested
    if resolution:
        SetRegion(res=resolution)

    #For jpeg output sometimes large images cause a problem to view them - so decrease resolution until size is < a value
    JPGOUTPUTCELLSIZELIMIT=104857600 # this value was taken from an old script - don't know where it came from
    if imtype=='JPEG':
        while grass.region()['cells'] > JPGOUTPUTCELLSIZELIMIT:
            dem_common_functions.WARNING("Decreasing Resolution slightly so that output number of cells is less than %d"%JPGOUTPUTCELLSIZELIMIT)
            grass.run_command('g.region',nsres=grass.region()['nsres']*1.01,ewres=grass.region()['ewres']*1.01)

    grass.run_command('r.out.gdal',format=imtype,input=inputname,output=outputname,nodata=nodata,type=datatype,flags='f')

    #Remove the XML file that gets output as most of the time we don't care about this
    if tidyup:
        outputname=outputname+'.aux.xml'
        if os.path.exists(outputname) and os.path.isfile(outputname):
            os.remove(outputname)

################################################################################
###############################Cleanup Functions################################
################################################################################

def cleanup(tmp_rast):
    """
    function cleanup
    Tmp_rast being made up of all the rast names, assuming this has been made,
    cleans all names stored in list. This cleans out the grass database which may
    be a little counterintuitive if we need to see results.

    Only cleans out current location folder, should be advanced to work with all in DB
    """
    for rast in tmp_rast:
        grass.run_command("g.remove",
                          rast = rast,
                          quiet = True)
#end function


################################################################################
###############################Imaging Functions################################
################################################################################

def importGdal(inputname,outputname=None,band=None,flags='ok',setnull=True,null=0):
    """
    Import a GDAL supported file optionally setting the null value,
    all bands or a single band, default is to override the projection
    """
    #if not output name given use the input name
    if outputname==None:
        outputname=os.path.basename(inputname)

    if band==None:
        grass.run_command('r.in.gdal',flags=flags,input=inputname,output=outputname)
    else:
        try:
            int(band)
        except:
            raise Exception("Band must be integer value in importGdal function")
        grass.run_command('r.in.gdal',flags=flags,input=inputname,output=outputname,band=band)

    if setnull:
        setNull(outputname,null)

def splitGroupIntoRasters(group):
    """
    Split the passed group up into a list of rasters and return the list
    If the group is actually a raster already, will just return this raster name
    """

    #print "GROUP: ",group
    #print "TYPE: ",type(group)

    return_list=[]
    #if only one group passed - set it as a list
    if type(group) is str:
        group=[group]

    #is group a list
    if type(group) is list:
        for item in group:
            #test if we've been given a group
            if rasterWithMapsetName(item) in grass.list_strings(type = 'group'):
                #It's a group
                #Create a list of rasters from the group, removing the @MAPSET from each raster name
                namestr=grass.read_command('i.group',flags='g',group=item)
                namelist=[re.sub('\@%s$'%grass.gisenv()['MAPSET'],'',x) for x in namestr.split('\n') if len(x) > 1]
            elif rasterWithMapsetName(item) in grass.list_strings(type = 'rast'):
                #group is actually not a group - is it a raster already? Yes - just remove the mapset name
                namelist=[re.sub('\@%s$'%grass.gisenv()['MAPSET'],'',item)]
            else:
                dem_common_functions.ERROR("splitGroupIntoRasters expected a group to be passed to it - this was neither a group or a raster: %s"%item)
                namelist=[]

            return_list.extend(namelist)
    else:
        dem_common_functions.ERROR("splitGroupIntoRasters expected a string or list of strings to be passed to it - this was a: %s"%type(group))
        return_list=[]

    if len(return_list) == 0:
        return_list=None

    return return_list

def SetRegion(rast=None,bounds=None,res=None):
    """
    Set the region based on either a raster or bounds (dict containing n,s,e,w)
    resolution can be set using the res parameter

    Arguments:

    * rast - raster or list of rasters
    * bounds - dictionary condaining n,s,e,w
    * res - resolution

    """
    if rast is None and bounds is None and res is not None:
        #Only update the resolution
        grass.run_command('g.region',res=res)
    elif rast is not None:
        #in case rast is a group - split it into rasters (has no effect if already a raster)
        rast=splitGroupIntoRasters(rast)
        if res is None:
            grass.run_command('g.region',rast=rast)
        else:
            grass.run_command('g.region',rast=rast,res=res)
    elif bounds is not None:
        if res is None:
            grass.run_command('g.region',n=bounds['n'],s=bounds['s'],e=bounds['e'],w=bounds['w'])
        else:
            grass.run_command('g.region',n=bounds['n'],s=bounds['s'],e=bounds['e'],w=bounds['w'],res=res)
    else:
        dem_common_functions.WARNING("Set region being called to do nothing!")


def rescale(raster,bounds):
    """
    Rescale a raster (or a group of rasters) to the given bounds
    """
    rasterout="%s.rescaled"%str(raster)
    #check if raster or group
    if rasterWithMapsetName(raster) in grass.list_strings(type = 'rast'):
        #It's a raster
        #we need to make sure the region is set to this raster prior to rescaling
        SetRegion(rast=raster)
        grass.run_command('r.rescale.eq',input=raster,output=rasterout,to=bounds)
    elif rasterWithMapsetName(raster) in grass.list_strings(type = 'group'):
        #It's a group
        #Create a list of rasters from the group, removing the @MAPSET from each raster name
        namelist=splitGroupIntoRasters(raster)
        namesout=[]

        #rescale each raster in the list
        for name in namelist:
            print("Name:",name)
            nameout="%s.rescaled"%str(name)
            namesout.append(nameout)
            SetRegion(rast=name)
            grass.run_command('r.rescale.eq',input=name,output=nameout,to=bounds)

        #Now re-group and return the group name
        if grass.run_command('i.group',group=rasterout,input=namesout) != 0:
            #An error occurred
            rasterout=None
    else:
        #What is it?
        dem_common_functions.ERROR("rescale function can currently only work with a raster or group within the current mapset.")
        return None

    return rasterout

def rasterWithMapsetName(raster):
    """
    Return a string of the given raster with the @MAPSET appended to it (if not already in the name)
    """
    if raster.find("@%s"%grass.gisenv()['MAPSET']) != -1:
        #already contains the mapset in name - will not append
        dem_common_functions.WARNING("rasterWithMapsetName received raster string with mapset name already included - will not append again.")
        return raster
    else:
        return "%s@%s"%(raster,grass.gisenv()['MAPSET'])

def rescaleRGB(r,g,b,bounds='0,255'):
    """
    Rescale 3 bands and return as a group
    """
    #set the region
    #SetRegion(rast='%s,%s,%s'%(r,g,b))
    SetRegion(rast=[r,g,b])
    #for each raster - rescale to bounds
    rescale_list=[]
    for raster in [r,g,b]:
        rasterout=rescale(raster,bounds)
        rescale_list.append(rasterout)

        #Test rescaled bands exist as can't figure out how to test for failure in above
        rasterlist=grass.list_strings(type = 'rast')
        if rasterWithMapsetName(rasterout) not in rasterlist:
            dem_common_functions.WARNING("Scaling doesn't seem to have worked - trying to use unscaled file (but renamed as though rescaled)")
            grass.run_command('g.copy',rast=(raster,rasterout))

    groupname= '%s%s%srescaled.group'%(r,g,b)
    #create an igroup for RGB image
    if grass.run_command('i.group',group=groupname,input="%s,%s,%s"%(rescale_list[0],rescale_list[1],rescale_list[2])) != 0:
        #An error occurred
        groupname=None
    return groupname


def locationFromFile(filename, locationname=None):
    """
    Create a new location that matches the given file. Can specify the new location name.
    """
    if locationname is None:
        try:
            locationname = getGRASSProjFromGDAL(filename)
        except Exception:
            pid = os.getpid()
            t = time.strftime("%H%M%S")
            locationname="custom-%s-%s" % (pid,t)

    if grass.run_command('g.proj',georef=filename,flags='c',location=locationname) != 0:
        #An error occurred
        locationname=None

    return locationname


def setNull(raster,value=0):
    """
    Set the null value for the given raster
    """
    return grass.run_command('r.null',setnull=value,map=raster)


def createMosaicFromRastersAndVectors(groupnames=None,vectorraster=None,vectorcolour='yellow'):
    """
    Generate a mosaic from all the rasters and vectors within the mapset
    unless groupnames is given: a list of groups to use as rasters to mosaic.
    vectorraster is a raster created from vectors (by importVector)
    """
    rasterlist=[]
    Rrasterlist=[]
    Grasterlist=[]
    Brasterlist=[]
    if groupnames==None:
        #list of rasters in mapset
        rasterlist=grass.list_strings(type = 'rast')
    else:
        #use list of rasters from list of groupnames
        for groupname in groupnames:
            namelist=splitGroupIntoRasters(groupname)
            if len(namelist)==3:
                Rrasterlist.append(namelist[0])
                Grasterlist.append(namelist[1])
                Brasterlist.append(namelist[2])
            elif len(namelist)==1:
                #Create copies and treat as a 3 band image
                Rrasterlist.append(namelist[0])
                grass.run_command('g.copy',rast=[namelist[0],namelist[0]+'_1'])
                Grasterlist.append(namelist[0]+'_1')
                grass.run_command('g.copy',rast=[namelist[0],namelist[0]+'_2'])
                Brasterlist.append(namelist[0]+'_2')
            else:
                dem_common_functions.ERROR("Can only create mosaics from groups with 3 bands in or single rasters, got length: %d"%len(namelist))
                return None

        #rasterlist is used for region setting so update it here
        rasterlist=Rrasterlist

    #list of vectors within mapset
    if vectorraster == None:
        vectordata=vectorraster
    else:
        vectordata=vectorraster

    #make the mosaic from the rasters
    SetRegion(rast=rasterlist)
    pid = os.getpid()
    t = time.strftime("%H%M%S")
    outputname="patched-%s-%s" % (pid,t)

    if groupnames==None:
        #if only one file - shouldn't really have called this function should you!!
        if len(rasterlist)==1:
            #rename the raster to be the expected patched name
            grass.run_command('g.rename',rast=[rasterlist[0],outputname])
        else:
            #Patch all rasters together
            grass.run_command('r.patch',input=rasterlist,output=outputname)
    else:
        #if only one file - shouldn't really have called this function should you!!
        if len(Rrasterlist)==1:
            #rename the raster to be the expected patched name
            grass.run_command('g.rename',rast=[Rrasterlist[0],outputname+'R'])
            grass.run_command('g.rename',rast=[Grasterlist[0],outputname+'G'])
            grass.run_command('g.rename',rast=[Brasterlist[0],outputname+'B'])
        else:
            #Need to patch all the R bands, G bands, B bands - and then igroup them
            grass.run_command('r.patch',input=Rrasterlist,output=outputname+'R')
            grass.run_command('r.patch',input=Grasterlist,output=outputname+'G')
            grass.run_command('r.patch',input=Brasterlist,output=outputname+'B')

        #If there are vectors then add them
        if vectordata != None:
            #Overlay the vector raster map onto another raster map
            if vectorcolour in ['red','yellow']:
                overlayVectorsOnRaster(vectordata,outputname+'R')
            if vectorcolour in ['green','yellow']:
                overlayVectorsOnRaster(vectordata,outputname+'G')
            if vectorcolour in ['blue']:
                overlayVectorsOnRaster(vectordata,outputname+'B')

        if grass.run_command('i.group',group=outputname+'RGB',input="%s,%s,%s"%(outputname+'R',outputname+'G',outputname+'B')) != 0:
            #An error occurred
            return None
        outputname=outputname+'RGB'

    return outputname


def overlayVectorsOnRaster(vectormap,rastermap):
    """
    Function to 'overlay' the vector (which is actually a raster) map onto a raster map
    Deleting the original raster map and replacing with new one
    """
    overlaidmap='%s_%s'%(vectormap,rastermap)
    #overlay (patch) the two rasters
    grass.run_command('r.patch',input=[vectormap,rastermap],output=overlaidmap)
    #delete the original rastermap
    cleanup([rastermap])
    #rename the overlaid vector map to the raster map name just deleted
    grass.run_command('g.rename',rast=[overlaidmap,rastermap])

    return

def convertVectorXYZtoSHP(vectorfile,outputshape=None,delim='\t',skiplines=0,x=1,y=2,z=0,format='point'):
    """
    Import XYZ csv vector and output as shapefile vector. Can specify input + output filenames, delimiter,
    how many lines to skip at start and which columns are associated with x,y,z. Can change format although
    this would usually be point.
    """
    #output name in grass database - replace the main forbidden chars that may be in a filename
    output=os.path.basename(vectorfile).replace('.','_').replace('-','_').replace('+','_')
    #if no output shapefile name given then output into tmp dir
    if outputshape is None:
        shapeoutputdir=tempfile.mkdtemp(suffix="vector")
        outputshape=os.path.join(shapeoutputdir,output+".shp")
    #import the csv into grass
    grass.run_command('v.in.ascii',input=vectorfile,output=output,format=format,fs=delim,skip=skiplines,x=x,y=y,z=z,cat=0,overwrite=True)
    #output as a shape file
    grass.run_command('v.out.ogr',flags='s',input=output, type="point,line", dsn=outputshape,layer=1,format="ESRI_Shapefile")
    #return the the output filename
    return outputshape

def importVectors(directory,region=None,tables=None):
    """
    Import SHP vector files from the given directory. Can specify
    a region and list of tables else imports everything
    """
    #Make an array of random column names
    columnnames=['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','x','y','z']
    flags=''
    #Is the directory a directory
    if not os.path.isdir(directory):
        dem_common_functions.ERROR("importVectors expects a directory containing Shapefiles. Received %s"%directory)
        return None
    #if we have no tables given use all available ones
    if tables == None:
        tablestr=grass.read_command('v.in.ogr',flags='l',dsn=directory)
        tables=[x.replace(' ','') for x in tablestr.split(',') if len(x) > 1]
    #if we have a region then change the current region to this and import only within this region
    if region != None:
        if type(region) is dict:
            SetRegion(bounds=region)
        elif type(region) is list:
            SetRegion(rast=region)
        else:
            dem_common_functions.ERROR("region passed to importVectors should either be list or dict, I got %s"%type(region))
            return None
        flags='r'

    rasterlist=[]
    for table in tables:
        #read in the vectors
        grass.run_command('v.in.ogr',dsn=directory,layer=table,output=table,cnames=columnnames,flags=flags+'to')
        #convert them to a raster
        output_thin=table+'_rast_tmp'
        grass.run_command('v.to.rast',input=table,output=output_thin,use='val',value=255)
        #Make the lines thicker
        output_thick=table+'_rast'
        grass.run_command('r.neighbors',input=output_thin,output=output_thick,method='maximum',size=1)
        rasterlist.append(output_thick)

    #patch the vector rasters together
    pid = os.getpid()
    t = time.strftime("%H%M%S")
    output_name='vector_map%s%s'%(pid,t)
    if len(rasterlist) > 1:
        grass.run_command('r.patch',input=rasterlist,output=output_name)
    else:
        grass.run_command('g.rename',rast=[rasterlist[0],output_name])
    return output_name

def checkFileExists(file_name):
    """
    Check file exists within GRASS database by
    running 'g.findfile' and checking for 'file_name'
    in output.

    http://grass.osgeo.org/grass65/manuals/g.findfile.html

    """

    p = grass.core.pipe_command('g.findfile',
                                 file=file_name,
                                 element='cell')

    find_out = p.communicate()[0]

    if find_out.find(file_name) > 0:
        return True
    else:
        return False
