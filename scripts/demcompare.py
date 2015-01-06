#! /usr/bin/env python

"""
A script to test hyperspectral and LiDAR dems provided in deliveries. It reads in the delivery DEM and the sol file, uses demgen.py to work 
out which tiffs are needed (or accepts a folder full of tiffs if needs be, or reads a dem instead). Then passes the files to grass to patch
tiles together and add spheroid data and finally performs the comparison of the two DEMs.
The total calculation is as follows:

comparison = ((Tile + tile(+tile...)) + spheroid) - input dem)

Averages are acheived by working with the resultant cells in the comparison raster e.g:
total of cell contents / total number of cells

Runs outside of grass.

Author: Stgo
Created on: 4 Nov 2013
Licencing: Used GRASS GIS python scripting library, subject to GNU GPL.

**Warnings**
The DEMS created in this script are NOT smoothed, unlike the other files we produce and deliver. This could be fixed, but will change the data we are comparing.

Available functions
main: Check the files required exist, then read them and run the calculation methods
report: Create a nicely structured report to output.

Updated 10/12/2014 by Dan Clewley (dac) to utilise new arsf_dem library.

"""
# IMPORTS
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys, argparse 
import glob
import shutil
import subprocess

# Import ARSF DEM
try:
   from arsf_dem import common_functions 
   from arsf_dem import grass_library
   from arsf_dem import dem_nav_utilities
   from arsf_dem import dem_lidar
   from arsf_dem import dem_common
except ImportError as err:
   print("Could not import arsf_dem library.\n{}".format(err),file=sys.stderr) 
   sys.exit(1)

# Import GRASS
sys.path.append(dem_common.GRASS_PYTHON_LIB_PATH)
try:
   import grass.script as grass
   import grass.script.setup as gsetup
except ImportError as err:
   print("Could not import grass library from {}".format(dem_common.GRASS_PYTHON_LIB_PATH), file=sys.stderr)
   print(err, file=sys.stderr)
   sys.exit(1)

# Try to import DEM library (only needed to get projection from LAS)
haveDEMLibrary=False
try:
   import dem_library
   haveDEMLibrary = True
except ImportError:
   pass

# GLOBAL VARIABLES

#: DEM to compare with.
COMPARISON_DEM_SOURCE = 'ASTER'

#: LiDAR DEM Type
LIDAR_DEM_TYPE = 'DSM'

def report(dem_dict):
   print("Min:\t\t%s"%dem_dict['min'])
   print("Max:\t\t%s"%dem_dict['max'])
   print("Sum:\t\t%s"%dem_dict['sum'])
   print("Mean:\t\t%s"%dem_dict['mean'])
   try:
      print("Median:\t\t%s"%dem_dict['median'])
   except KeyError:
      common_functions.WARNING("Median not available")
   print("Absolute mean:\t%s"%dem_dict['mean_of_abs'])
   print("Std deviation:\t%s"%dem_dict['stddev'])
   print("Total cells:\t%s"%dem_dict['cells'])
   try:
      print("Non-null cells:\t%s"%dem_dict['n'])
   except KeyError:
      print("Null cells:\t%s"%dem_dict['null_cells'])
      warning = "This report is minimal, which means something went wrong in the comparison process\
            it is worthwile inspecting the dem created for discrepencies. To do this open grass \
            with the tmp folder above. Type g.gui then load 'comparison' into the map display \
            if it is one solid colour then sample it to check what that colour represents and \
            hope it is 0"
      common_functions.WARNING(warning)
   
def main(commandline):
   unmaskeduniv=None

   #initialise grass and prepares it to take the commands, sets grassrc to our requirements
   tempfolder = grass_library.grassDBsetup()
   tmp_rast=[]
   tiles=[]
   input_dem_location = commandline.dem
   #The base location is kept as WGS84LL if reading aster data, otherwise will be updated to relevant dem type.
   base_location = "WGS84LL"
   
   grass_library.setGrassQuiet(commandline.v)
   
   if commandline.output is not None and os.path.isfile(commandline.output):
      common_functions.ERROR("The output dem you are trying to create (%s) already exists!" % (commandline.output))
      exit(1)

   # Create DEM from another dataset
   if commandline.comparison_dem is None:
      try:
         # Subset source DEM to navigation data and apply offset so heights are relative 
         # to WGS84 datum. The seperation file to be used will be determined based on
         # the DEM source
         common_functions.PrintTermWidth("Creating comparison DEM from %s data"%(COMPARISON_DEM_SOURCE),padding_char='*')
         base_dem, grassdb_path = dem_nav_utilities.create_apl_dem_from_mosaic(None,
                                          dem_source=COMPARISON_DEM_SOURCE,
                                          project=commandline.project,
                                          nav=commandline.nav,
                                          fill_nulls=False,
                                          remove_grassdb=False,
                                          grassdb_path=tempfolder)
      except Exception as err:
         common_functions.ERROR(err)
         exit(1)
   else:
      #attempt import of comparison dem (generally aster dem)
      try:
         base_dem, base_proj, base_location = grass_library.readDem(commandline.comparison_dem)
      except ValueError as v:
         common_functions.ERROR(v)
         exit(1)

   #attempt import of the input dem (generally lidar dem)
   try:
      input_dem, input_proj, input_location = grass_library.readDem(commandline.dem)
   except ValueError as v:
      common_functions.ERROR(v)
      exit(1)
   
   # If lidar directory is supplied, assume a lidar comparison
   # lidar files will be read in rasterised, patched together and
   # used to create a mask
   if commandline.lidar is not None:
      #now that we have the input and comparison dems ready, we create a lidar area mask
      if commandline.lidar_projection is not None:
         if commandline.lidar_projection != input_proj:
            las_loc = grass_library.newLocation(commandline.lidar_projection)
         else:
            las_loc = input_location
      else:
         # If LAS input, use this
         if commandline.las:
            las_lidar_path = commandline.lidar
         else:
            las_lidar_path = commandline.lidar.replace("ascii", "las1.0") 
            if not os.path.isdir(las_lidar_path):
               las_lidar_path = commandline.lidar.replace("ascii", "las1.2") 
            if not os.path.isdir(las_lidar_path):
               common_functions.WARNING("Could not find LAS files based on the ASCII path given")
               common_functions.WARNING("Assuming lidar files use default projection of %s"%(dem_common.DEFAULT_LIDAR_PROJECTION_GRASS))
               lidar_proj_info = dem_common.DEFAULT_LIDAR_PROJECTION_GRASS
            else:
               try: 
                  lidar_proj_info = dem_library.get_project_proj(las_lidar_path)
               except:
                  common_functions.ERROR("There was a problem finding the lidar projection automatically. specify this using -l (UTM##N|S or UKBNG)")
                  exit(1)

         if lidar_proj_info != 'Could not find any projection':
            loc_id = lidar_proj_info[1]
            if loc_id == 'WGS84LL':
               common_functions.WARNING("Lidar projection has returned WGS84LL, this projection is not valid to read Lidar. Will try using input dem projection.")
               loc_id = input_proj
         else:
            if input_proj == 'WGS84LL':
               raise ValueError("Could not find lidar projection automatically and input dem projection is not compatible with lidar. Specify what to use with -l.")
            else:
               common_functions.WARNING("Could not find lidar projection automatically, will try using input dem projection("+input_proj+"). Check this is correct! If not specify with -l")
               loc_id = input_proj
         if input_proj != loc_id:
            las_loc = grass_library.newLocation(loc_id)
         else:
            las_loc = input_location

      if commandline.las:
         lidar_format = 'LAS'
      else:
         lidar_format = 'ASCII'
         
      las_patched, grassdb_path = dem_lidar.lidar_utilities.create_lidar_mosaic(commandline.lidar, out_mosaic=None, 
                     out_screenshot=None,
                     in_projection=commandline.lidar_projection,
                     resolution=dem_common.DEFAULT_LIDAR_RES_METRES,
                     nodata=dem_common.NODATA_VALUE,
                     lidar_format=lidar_format,
                     raster_type=LIDAR_DEM_TYPE,
                     fill_nulls=False,
                     remove_grassdb=False,
                     grassdb_path=tempfolder)

      grass.run_command('g.gisenv', set="LOCATION_NAME=%s" % (base_location))

      if base_location != las_loc:
         grass_library.reproject(las_patched, las_loc, "PERMANENT", las_patched)
      
      ###############
      #Masking
      ###############
      
      #need to convert the mask file to rounded int values, because grass doesn't like floats for masks. 
      #If grass gets updated this can be removed.
      grass.mapcalc("las_mask=int(round(%s))"%las_patched, 
                     overwrite = True)
      
      if input_location != base_location:
         grass.run_command('g.gisenv', set="LOCATION_NAME=%s" % (base_location))
         grass_library.reproject(input_dem, input_location, "PERMANENT", input_dem)
      
      grass_library.createComparisonDem(base_dem, input_dem, "comparison_unmasked")
         
      
      #take statistics before the mask is applied, for completeness.
      unmaskeduniv = grass_library.univariates("comparison_unmasked")
      
      #mask cats '1 thru 6000' avoids 0 asking the entire map, includes the likely heighest points.
      grass.run_command('r.mask', 
                        input='las_mask',
                        maskcats='1 thru 6000')
      
      #create a comparison of the lidar and input
      grass_library.createComparisonDem(base_dem, las_patched, "lidar_comparison")
      lidaruniv = grass_library.univariates("lidar_comparison")

   else:
      if input_location != base_location:
         #otherwise it isn't a lidar and we might need to reproject for comparisons, no mask applied.
         #pretty unlikely that a reprojection would occur though really.
         grass.run_command('g.gisenv', set="LOCATION_NAME=%s" % (base_location))
         grass_library.reproject(input_dem, input_location, "PERMANENT", input_dem)
         unmaskeduniv = None
   
   if commandline.comparison_dem is None:
      common_functions.PrintTermWidth("Comparing supplied DEM (%s) with one created from %s"%(commandline.dem, COMPARISON_DEM_SOURCE))
   else:
      common_functions.PrintTermWidth("Comparing '%s' with '%s'"%(commandline.dem, commandline.comparison_dem))

   grass_library.createComparisonDem(base_dem, input_dem, "comparison")
   
   astersum = grass.read_command("r.sum",
                                 rast=base_dem).replace("SUM = ", "")
   inputsum = grass.read_command("r.sum",
                                 rast=input_dem).replace("SUM = ", "")
   comparisonsum = grass.read_command("r.sum",
                                      rast="comparison").replace("SUM = ", "")
   #set the region to comparison (just in case, otherwise we might get values we don't care about.)
   grass.run_command('g.region',
                     rast="comparison")
   
   #For the output of the created DEM, probably not worth making this into a def of its own right.
   if commandline.output is not None:
      grass.run_command('r.out.gdal', 
                        input="comparison", 
                        output=commandline.output, 
                        format='ENVI', 
                        type='Float64', 
                        flags='c')
   
   statistics = grass_library.univariates("comparison")
   #mode, modevalue = modalavg("comparison")
   
   if commandline.csv:
      try:
         output = [input_dem,
            base_dem,
            base_location,
            input_location,
            astersum.strip(),
            inputsum.strip(),
            comparisonsum.strip(),
            #mode.strip(),
            #modevalue.strip(),
            statistics['min'],
            statistics['max'],
            statistics['sum'],
            statistics['median'],
            statistics['mean'],
            statistics['mean_of_abs'],
            statistics['stddev'],
            statistics['cells'],
            statistics['n'],
            tempfolder]
      except KeyError:
         output = [input_dem,
            base_dem,
            base_location,
            input_location,
            astersum.strip(),
            inputsum.strip(),
            comparisonsum.strip(),
            #mode.strip(),
            #modevalue.strip(),
            statistics['min'],
            statistics['max'],
            statistics['sum'],
            statistics['mean'],
            statistics['mean_of_abs'],
            statistics['stddev'],
            statistics['cells'],
            statistics['null_cells'],
            tempfolder]
      
      if commandline.lidar is not None:
         try:
            output.extend([lidaruniv['min'],
                           lidaruniv['max'],
                           lidaruniv['sum'],
                           lidaruniv['median'],
                           lidaruniv['mean']])
         except KeyError:
            output.extend([lidaruniv['min'],
               lidaruniv['max'],
               lidaruniv['sum'],
               lidaruniv['mean']])
         
      if commandline.script:
         return output
      else:
         print(",".join(output))
   else:
      common_functions.PrintTermWidth("Report",padding_char="*")
      print("Temp folder created at: %s"%tempfolder)
      print("Calculation performed: %s-%s"%(input_dem,base_dem))
      print("The maps were compared in: %s"%base_location)
      print("%s was imported in: %s"%(input_dem, input_location))
      print("%s sum\t: %s"%(base_dem, astersum))
      print("%s sum\t: %s"%(input_dem, inputsum))
      print("Comparison sum\t: %s"%comparisonsum)

      print("Difference statistics:")
      #print "Modal Average:"+mode+" with"+modevalue+"instances"
      if len(statistics) != 0:
         report(statistics)
      else:
         common_functions.ERROR("Something went wrong during comparison, do these dems definitely overlap? Does the mask cover both dems?")

      if unmaskeduniv is not None:
         print("\n\nUnmasked statistics:")
         report(unmaskeduniv)
      common_functions.PrintTermWidth('',padding_char='*')
   
   if commandline.histogram is not None:
      if os.path.exists(commandline.histogram):
         common_functions.WARNING("The file specified with --histogram already exists, adding _1 to the given name")
         grass_library.histogram("comparison_unmasked", commandline.histogram.replace(".","_1."))
      else:
         grass_library.histogram("comparison_unmasked", commandline.histogram)
   
   grass.run_command('r.mask',
                     flags = 'r')
   
   if commandline.png is not None:
      print("Recoloring for clarity, this might take a while")
      grass.run_command('r.colors',
                        flags='e',
                        map=comparison_unmasked,
                        color=grey)
      if os.path.exists(commandline.png):
         common_functions.WARNING("The file specified with --png already exists, adding _1 to the given name")
         grass_library.outputpng("comparison_unmasked", commandline.png.replace(".", "_1."))
      else:
         grass_library.outputpng("comparison_unmasked", commandline.png)

   # If don't explicity state want to keep GRASS DB
   # remove it. Previously was always kept
   if not commandline.keepgrassdb:
      shutil.rmtree(tempfolder)
#end function
   
if __name__ == "__main__":
   description_str = '''A script to compare DEMs

For documentation and details on usage see:

https://arsf-dan.nerc.ac.uk/trac/wiki/Processing/demcompare

Report bugs to:

https://arsf-dan.nerc.ac.uk/trac/ticket/545

'''

   try:
      parser = argparse.ArgumentParser(description=description_str,formatter_class=argparse.RawDescriptionHelpFormatter)
      parser.add_argument('-d','--dem',
                          metavar ='DEM to be tested',help ='The DEM file that will be tested.', 
                          required = True)
      parser.add_argument('-p','--project', 
                          metavar ='Main project directory',
                          help ='Main project directory, assumed as . if not given',
                          default='.')
      parser.add_argument('-n', '--nav',metavar ='Nav file',
                          help ='.sol file used to produce the original DEM, a different sol file may give a different result.',
                          default=None)
      parser.add_argument('-c','--comparison_dem', 
                          metavar ='Comparison DEM',
                          help ='Compare to a prepared DEM rather than creating a new DEM from %s data. Make sure you input these the right way around.'%COMPARISON_DEM_SOURCE,
                          default=None)
      parser.add_argument('-l','--lidar_projection', 
                          metavar ='Lidar projection',
                          help ='UTM zone or UKBNG, must either be formatted UTM##N|S or as UKBNG.',
                          default=None)
      parser.add_argument('-v', 
                          metavar ='Verbosity',
                          help ='0 - 3, 0 being only errors/staging, 3 maximum detail. Default is 0.',
                          default=0)
      parser.add_argument('--output',
                          help ='output the resultant comparison DEM for inspection in another program.',
                          default=None)
      parser.add_argument('--lidar',
                          help ='Input directory of lidar data in LAS or ASCII format.',
                          default=None)
      parser.add_argument('--las',
                          action='store_true',
                          help='Input LiDAR data are in LAS format (default=False)',
                          default=False,
                          required=False)
      parser.add_argument('--ascii',
                          action='store_true',
                          help='Input LiDAR data are in ASCII format (default=True)',
                          default=True,
                          required=False) 
      parser.add_argument('--csv', 
                          action='store_true', 
                          help ='Output as csv format for batch processing.',
                          default=False)
      parser.add_argument('--script', 
                          action='store_true', 
                          help ='Use with csv to indicate return rather than print',
                          default=False)
      parser.add_argument('--histogram', 
                          help ='Create a histogram and output it as a png at specified location. Include file extension.',
                          default=None)
      parser.add_argument('--png', 
                          help ='Create a PNG of the difference dem at the specified location. Include file extension.',
                          default=None)
      parser.add_argument('--keepgrassdb',
                          action='store_true',
                          help='Keep GRASS database (default=False)',
                          default=False,
                          required=False)
      args=parser.parse_args()
      main(args)
   except KeyboardInterrupt:
      exit(1)
   #end try
#end if
