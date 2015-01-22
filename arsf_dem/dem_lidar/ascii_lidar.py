# ascii_lidar
#
# Author: Dan Clewley (dac@pml.ac.uk)
# Created On: 19/11/2014
#
# remove_ascii_class from grass_library by Stephen Gould

"""
Functions for working with lidar data in ASCII format.

Available functions:

* get_ascii_bounds - get bounds from a lidar file.

"""
from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import csv
# Import common files
from .. import dem_common

def get_ascii_bounds(in_ascii):
   """
   Gets bounds of ASCII format LiDAR file.

   Currently pure Python using CSV reader, could be
   made faster.

   Arguments:

   * in_ascii - Input ASCII file

   Returns:

   * bounding box in format: [[min_x,max_x],
                              [min_y,max_y],
                              [min_z,max_z]]
   """

   if not os.path.isfile(in_ascii):
      raise Exception('File "{in_ascii}" does not exist')

   # Set initial min/max bounds to the same as thouse in
   # 'check_ascii_lidar.sh'
   min_x = 10000000
   max_x = -100000000
   min_y = 10000000
   max_y = -100000000
   min_z = 9999999
   max_z = 0
  
   in_ascii_handler = open(in_ascii, 'rU')
   in_ascii_csv = csv.reader(in_ascii_handler, delimiter=' ')

   for line in in_ascii_csv:

      line_x = float(line[dem_common.LIDAR_ASCII_ORDER['x']-1])
      line_y = float(line[dem_common.LIDAR_ASCII_ORDER['y']-1])
      line_z = float(line[dem_common.LIDAR_ASCII_ORDER['z']-1])
   
      if line_x < min_x:
         min_x = line_x
      elif line_x > max_x:
         max_x = line_x
         
      if line_y < min_y:
         min_y = line_y
      elif line_y > max_y:
         max_y = line_y
         
      if line_z < min_z:
         min_z = line_z
      elif line_z > max_z:
         max_z = line_z
  
   # Close file 
   in_ascii_handler.close()

   return [[min_x,max_x],
           [min_y,max_y],
           [min_z,max_z]]

