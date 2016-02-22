#! /usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created on: 05 November 2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
Functions for working with LiDAR data using LAStools:

http://rapidlasso.com/lastools/

Note, some functions require a valid LAStools license.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import tempfile
import glob
import subprocess
# Import common files
from .. import dem_common
from .. import dem_common_functions

def _checkFreeLAStools():
   """Check if LAStools are installed."""

   try:
      dem_common_functions.CallSubprocessOn([os.path.join(dem_common.LASTOOLS_FREE_BIN_PATH,'las2txt'),'-h'],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False

def _checkPaidLAStools():
   """Check if paid LAStools are installed."""

   try:
      dem_common_functions.CallSubprocessOn([os.path.join(dem_common.LASTOOLS_NONFREE_BIN_PATH,'las2dem.exe'),'-h'],
                        redirect=True, quiet=True)
      return True
   except OSError:
      return False

def _check_flags(in_flags):
   """
   Check if flags have been passed in in format '-flag'.
   If not add dash. If flag contains spaces splits and returns as list

   Arguments:

   * in_flag / list of input flags

   Returns:

   * list containing flag to pass to subprocess
   """
   outflags_list = []

   if isinstance(in_flags,list):
      for flag in in_flags:
         if flag[0] != '-':
            flag = '-' + flag
         # Split strings into separate list components for
         # subprocess.
         outflags_list.extend(flag.split())

   elif isinstance(in_flags,str):
      if in_flags[0] != '-':
         in_flags = '-' + in_flags
      # Split strings into separate list components for
      # subprocess.
      outflags_list.extend(in_flags.split())

   return outflags_list

def convert_las_to_ascii(in_las, out_ascii, drop_class=None, keep_class=None,flags=None,print_only=False):
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

   If a list

   Arguments:

   * in_las - Input LAS file / directory containing LAS files
   * out_ascii - Output ASCII file / directory containing LAS files
   * drop_class - Integer or list of integer class codes to drop
   * keep_class - Integer or list of integer class codes to keep
   * flags - List of additional flags for las2txt
   * print_only - Don't run commands, only print

   Returns:

   * None

   """
   if not _checkFreeLAStools():
      raise Exception('Could not find LAStools, checked {}'.format(dem_common.LASTOOLS_FREE_BIN_PATH))

   las2txt_cmd_base = [os.path.join(dem_common.LASTOOLS_FREE_BIN_PATH,'las2txt'),
                  '-parse',
                  'txyzicrna',
                  '-sep',
                  'space']

   if drop_class is not None:
      if isinstance(drop_class,list):
         drop_class_str = []
         for item in drop_class:
            drop_class_str.append(str(item))
         las2txt_cmd_base = las2txt_cmd_base + ['-drop_class'] + drop_class_str

      elif isinstance(drop_class,int):
         las2txt_cmd_base = las2txt_cmd_base + ['-drop_class',str(drop_class)]

   if keep_class is not None:
      if isinstance(keep_class,list):
         keep_class_str = []
         for item in keep_class:
            keep_class_str.append(str(item))
         las2txt_cmd_base = las2txt_cmd_base + ['-keep_class'] + keep_class_str

      elif isinstance(keep_class,int):
         las2txt_cmd_base = las2txt_cmd_base + ['-keep_class',str(keep_class)]

   # Check for flags
   if flags is not None:
      las2txt_cmd_base += _check_flags(flags)

   if isinstance(in_las,list):
      # If a list is passed in, run for each file
      for in_las_file in in_las:
         out_ascii_base = os.path.splitext(os.path.basename(in_las_file))[0]
         out_ascii_file = os.path.join(out_ascii, out_ascii_base + '.txt')
         las2txt_cmd = las2txt_cmd_base + ['-i',in_las_file,
                                '-o',out_ascii_file]
         if print_only:
            print(" ", " ".join(las2txt_cmd))
         else:
            dem_common_functions.CallSubprocessOn(las2txt_cmd)

   elif os.path.isdir(in_las):
      # If a directoy is passed in
      # Look for LAS or LAZ files
      in_las_list = glob.glob(
                           os.path.join(in_las,'*LAS'))
      in_las_list.extend(glob.glob(
                           os.path.join(in_las,'*LAZ')))
      in_las_list.extend(glob.glob(
                           os.path.join(in_las,'*las')))
      in_las_list.extend(glob.glob(
                           os.path.join(in_las,'*laz')))
      if len(in_las_list) == 0:
         raise IOError('Could not find any LAS files in directory:\n {}'.format(in_las))

      # Check a directory has been provided for output
      if not os.path.isdir(out_ascii):
         raise Exception('Must provide path to existing directory if an input directory is provided')

      for in_las_file in in_las_list:
         out_ascii_base = os.path.splitext(os.path.basename(in_las_file))[0]
         out_ascii_file = os.path.join(out_ascii, out_ascii_base + '.txt')
         las2txt_cmd = las2txt_cmd_base + ['-i',in_las_file,
                                '-o',out_ascii_file]

         if print_only:
            print(" ", " ".join(las2txt_cmd))
         else:
            dem_common_functions.CallSubprocessOn(las2txt_cmd)

   else:
      las2txt_cmd = las2txt_cmd_base + ['-i',in_las,
                                '-o',out_ascii]

      if print_only:
         print(" ", " ".join(las2txt_cmd))
      else:
         dem_common_functions.CallSubprocessOn(las2txt_cmd)

def classify_ground_las(in_las,out_las, flags=None):
   """
   Classify ground returns in a LAS file.

   Calls the lasground tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/lasground_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_las - Output LAS file
   * flags - List of additional flags for lasground

   Returns:

   * None

    """
   if not _checkPaidLAStools():
      raise Exception('Could not find LAStools, checked {}'.format(dem_common.LASTOOLS_NONFREE_BIN_PATH))

   lasground_cmd = [os.path.join(dem_common.LASTOOLS_NONFREE_BIN_PATH,'lasground.exe')]
   # Check for flags
   if flags is not None:
      lasground_cmd += _check_flags(flags)

   lasground_cmd.extend(['-i',in_las, '-o',out_las])

   # Run directly through subprocess, as CallSubprocessOn
   # raises exception under windows for unlicensed LAStools
   print('Attempting to run command: ' + ' '.join(lasground_cmd))
   subprocess.check_output(lasground_cmd)

def las_to_dsm(in_las, out_dsm, flags=None):
   """
   Create Digital Surface Model (DSM)
   from LAS file using the las2dem tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2dem_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_dsm - Output DSM, format depends on extension.
   * flags - List of additional flags for las2dem

   Returns:

   * None

   """

   if not _checkPaidLAStools():
      raise Exception('Could not find LAStools, checked {}'.format(dem_common.LASTOOLS_NONFREE_BIN_PATH))

   print('Creating DSM')
   las2dem_cmd = [os.path.join(dem_common.LASTOOLS_NONFREE_BIN_PATH,'las2dem.exe')]
   # Check for flags
   if flags is not None:
      las2dem_cmd += _check_flags(flags)

   las2dem_cmd.extend(['-i',in_las, '-o',out_dsm])

   # Run directly through subprocess, as CallSubprocessOn
   # raises exception under windows for unlicensed LAStools
   print('Attempting to run command: ' + ' '.join(las2dem_cmd))
   subprocess.check_output(las2dem_cmd)

def las_to_dtm(in_las, out_dtm, keep_las=False, flags=None):
   """
   Create Digital Terrain Model (DTM) from LAS file
   using the las2dem tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2dem_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_dtm - Output DTM, format depends on extension.
   * keep_las - Keep ground classified LAS file
   * flags - List of additional flags for las2dem

   Returns:

   * Ground classified LAS file / None

   """

   if not _checkPaidLAStools():
      raise Exception('Could not find LAStools, checked {}'.format(dem_common.LASTOOLS_NONFREE_BIN_PATH))

   lasfile_grd_tmp = tempfile.mkstemp(suffix='.LAS', dir=dem_common.TEMP_PATH)[1]

   print('Classifying ground returns')
   classify_ground_las(in_las, lasfile_grd_tmp, flags=['-ignore_class 7'])

   print('Creating DTM')
   las2dem_cmd = [os.path.join(dem_common.LASTOOLS_NONFREE_BIN_PATH,'las2dem.exe')]
   # Check for flags
   if flags is not None:
      las2dem_cmd += _check_flags(flags)

   las2dem_cmd.extend(['-keep_class', '2'])
   las2dem_cmd.extend(['-i',lasfile_grd_tmp, '-o',out_dtm])

   # Run directly through subprocess, as CallSubprocessOn
   # raises exception under windows for unlicensed LAStools
   print('Attempting to run command: ' + ' '.join(las2dem_cmd))
   subprocess.check_output(las2dem_cmd)

   if keep_las:
      return lasfile_grd_tmp
   else:
      os.remove(lasfile_grd_tmp)
      return None

def las_to_intensity(in_las, out_intensity, flags=None):
   """
   Create an Intensity image from a
   from LAS file using the las2dem tool.

   http://www.cs.unc.edu/~isenburg/lastools/download/las2dem_README.txt

   Note: this tool requires a license.

   Arguments:

   * in_las - Input LAS file
   * out_intensity - Output intensity image, format depends on extension.
   * flags - List of additional flags for las2dem

   Returns:

   * None

   """

   if not _checkPaidLAStools():
      raise Exception('Could not find LAStools, checked {}'.format(dem_common.LASTOOLS_NONFREE_BIN_PATH))

   print('Creating Intensity image')
   las2dem_cmd = [os.path.join(dem_common.LASTOOLS_NONFREE_BIN_PATH,
                               'las2dem.exe')]
   # Check for flags
   if flags is not None:
      las2dem_cmd += _check_flags(flags)

   las2dem_cmd.extend(['-i',in_las, '-o',out_intensity, '-intensity'])

   # Run directly through subprocess, as CallSubprocessOn
   # raises exception under windows for unlicensed LAStools
   print('Attempting to run command: ' + ' '.join(las2dem_cmd))
   subprocess.check_output(las2dem_cmd)


def grass_proj_to_lastools_flag(in_grass_proj):
   """
   Converts GRASS projection (e.g., UTM30N)
   into projection flags for LAStools

   Currently only works with UTM

   Arguments:

   * in_grass_proj - Input GRASS projection.

   Returns:

   * flags for LAStools (e.g., -utm 30N)

   """

   if in_grass_proj[:3].upper() != 'UTM':
      raise Exception('Currently only UTM projections are supported')
   else:
      return '-utm {}'.format(in_grass_proj[3:])



