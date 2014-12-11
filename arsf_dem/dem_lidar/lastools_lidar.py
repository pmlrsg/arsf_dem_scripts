#! /usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created on: 05 November 2014
# Licensing restrictions: Uses a mixture of GPL and commercial LAStools

"""
Functions for working with LiDAR data using LAStools:

http://rapidlasso.com/lastools/

Note, some functions require a valid LAStools license.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os, sys
import tempfile
# Import common files
from .. import dem_common
from .. import common_functions

def checkFreeLAStools():
   """Check if LAStools are installed."""
   
   try:
      common_functions.CallSubprocessOn([os.path.join(dem_common.LASTOOLS_FREE_BIN_PATH,'las2txt'),'-h'],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False 

def checkPaidLAStools():
   """Check if paid LAStools are installed."""
   
   try:
      common_functions.CallSubprocessOn([os.path.join(dem_common.LASTOOLS_PAID_BIN_PATH,'las2dem.exe'),'-h'],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False 

def check_flag(in_flag):
   """Check if flags have been
   passed in in format '-flag'.
   If not add dash.
   """

   if in_flag[0] == '-':
      return in_flag
   else:
      return '-' + in_flag

def convert_las_to_ascii(in_las, out_ascii, drop_class=None, keep_class=None,flags=None):
   """
   Convert LAS files to ASCII using las2txt
   tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2txt_README.txt
   
   Calls with the following options:
   
   las2txt -parse txyzicrna -sep space 
            -i in_las -o out_ascii

   If a list of classes to drop is supplied will drop using the following
   command:

   las2txt -parse txyzicrna -sep space 
            -drop_class 7
            -i in_las -o out_ascii

   If a list of classes to keep is supplied will drop using the following
   command:

   las2txt -parse txyzicrna -sep space 
            -keep_class 7
            -i in_las -o out_ascii   

   Can use flags to only keep first (-first_only) or last returns (-last_only)
            
            
   Arguments:

   * in_las - Input LAS file
   * out_ascii - Output ASCII file
   * drop_class - Integer or list of integer class codes to drop
   * keep_class - Integer or list of integer class codes to keep
   * flags - List of additional flags for las2txt

   Returns:
   
   * None

   """
   if not checkFreeLAStools():
      raise Exception('Could not find LAStools')

   las2txt_cmd = [os.path.join(dem_common.LASTOOLS_FREE_BIN_PATH,'las2txt'),
                  '-parse',
                  'txyzicrna',
                  '-sep',
                  'space']

   if drop_class is not None:
      if isinstance(drop_class,list):
         drop_class_str = []
         for item in drop_class:
            drop_class_str.append(str(item))
         las2txt_cmd = las2txt_cmd + ['-drop_class'] + drop_class_str

      elif isinstance(drop_class,int):
         las2txt_cmd = las2txt_cmd + ['-drop_class',str(drop_class)]

   if keep_class is not None:
      if isinstance(keep_class,list):
         keep_class_str = []
         for item in keep_class:
            drop_class_str.append(str(item))
         las2txt_cmd = las2txt_cmd + ['-drop_class'] + drop_class_str

      elif isinstance(drop_class,int):
         las2txt_cmd = las2txt_cmd + ['-drop_class',str(drop_class)]

   # Check for flags
   if flags is not None:
      if isinstance(flags,list):
         for item in flags:
            las2txt_cmd = las2txt_cmd + [check_flag(item)]

      elif isinstance(flags,str):
         las2txt_cmd = las2txt_cmd + [check_flag(flags)]

   las2txt_cmd = las2txt_cmd + ['-i',in_las,
                                '-o',out_ascii]
   
   common_functions.CallSubprocessOn(las2txt_cmd)

def classify_ground_las(in_las,out_las):
   """
   Classify ground returns in a LAS file.

   Calls the lasground tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/lasground_README.txt

   Note: this tool requires a license.
   
   Arguments:

   * in_las - Input LAS file
   * out_las - Output LAS file

   Returns:
   
   * None
 
    """
   if not checkPaidLAStools():
      raise Exception('Could not find LAStools')

   lasground_cmd = [os.path.join(dem_common.LASTOOLS_PAID_BIN_PATH,'lasground.exe'),
                  '-i',in_las,
                  '-o',out_las]
   
   common_functions.CallSubprocessOn(lasground_cmd)


def las_to_dsm(in_las, out_dsm):
   """
   Create Digital Surface Model (DSM) 
   from LAS file using the las2dem tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2dem_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_dsm - Output DSM, format depends on extension. 

   Returns:
   
   * None

   """

   if not checkPaidLAStools():
      raise Exception('Could not find LAStools')

   las2dem_cmd = [os.path.join(dem_common.LASTOOLS_PAID_BIN_PATH,'las2dem.exe'),
                  '-i',in_las,
                  '-o',out_dsm]
   
   common_functions.CallSubprocessOn(las2dem_cmd)

def las_to_dtm(in_las, out_dtm, keep_las=False):
   """
   Create Digital Terrain Model (DTM) from LAS file 
   using the las2dem tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2dem_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_dtm - Output DTM, format depends on extension. 
   * keep_las - Keep ground classified LAS file

   Returns:
   
   * Ground classified LAS file / None

   """

   if not checkPaidLAStools():
      raise Exception('Could not find LAStools')

   lasfile_grd_tmp = tempfile.mkstemp(suffix='.LAS', dir=dem_common.TEMP_PATH)[1]
   
   print('Classifying ground returns')
   classify_ground_las(in_las, lasfile_grd_tmp)

   las2dem_cmd = [os.path.join(dem_common.LASTOOLS_PAID_BIN_PATH,'las2dem.exe'),
                  '-keep_class', '2',
                  '-i',lasfile_grd_tmp,
                  '-o',out_dtm]
   
   common_functions.CallSubprocessOn(las2dem_cmd)

   if keep_las:
      return lasfile_grd_tmp
   else:
      os.remove(lasfile_grd_tmp)
      return None

