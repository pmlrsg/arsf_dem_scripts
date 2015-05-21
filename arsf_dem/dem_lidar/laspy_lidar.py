#! /usr/bin/env python
#
# Author: Dan Clewley (dac)
# Created on: 10 November 2014

# This file has been created by ARSF Data Analysis Node and
# is licensed under the GPL v3 Licence. A copy of this
# licence is available to download with this file.

"""
Functions for working with LiDAR data in LAS format using the laspy
Python library.

http://pythonhosted.org/laspy/

Available Function:

* get_las_bounds - get bounds of LAS file or list of LAS files.
* get_las_bounds_single - used by get_las_bounds, don't call directly.

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)

#: laspy library is available
HAVE_LASPY = True
try:
   import laspy
except ImportError:
   # Don't raise error until a function
   # which requires laspy is called
   HAVE_LASPY = False

def get_las_bounds_single(in_las_file,from_header=True):
   """
   Gets bounds of a single LAS file using
   the laspy library. Used by get_las_bounds, it is reccomended
   to call this function as it can take a list or single file.

   Arguments:

   * in_las_file - input las file
   * from_header - get bounds from header (default)
                   or by reading points (slower)

   Returns:

   * bounding box of las file [[min_x,max_x],
                               [min_y,max_y],
                               [min_z,max_z]]

   """

   if not HAVE_LASPY:
      raise ImportError('Could not import laspy')

   in_las = laspy.file.File(in_las_file, mode='r')

   if from_header:
      min_x = in_las.header.min[0]
      max_x = in_las.header.max[0]
      min_y = in_las.header.min[1]
      max_y = in_las.header.max[1]
      min_z = in_las.header.min[2]
      max_z = in_las.header.max[2]

   else:
      min_x = in_las.x.min()
      max_x = in_las.x.max()
      min_y = in_las.y.min()
      max_y = in_las.y.max()
      min_z = in_las.z.min()
      max_z = in_las.z.max()

   return [[min_x,max_x],
           [min_y,max_y],
           [min_z,max_z]]

def get_las_bounds(in_las, from_header=True):
   """
   Gets bounds of a single LAS file using or outer bounds of a list
   of LAS files using the laspy library.

   Arguments:

   * in_las - input las file / list of files
   * from_header - get bounds from header (default)
                   or by reading points (slower)

   Returns:

   * bounding box of all las files [[min_x,max_x],
                                    [min_y,max_y],
                                    [min_z,max_z]]

   """
   if not HAVE_LASPY:
      raise ImportError('Could not import laspy')

   if isinstance(in_las,str):
      return get_las_bounds_single(in_las, from_header=from_header)
   elif isinstance(in_las, list):
      # Get bounds from LAS files
      min_x = None
      max_x = None
      min_y = None
      max_y = None
      min_z = None
      max_z = None

      for in_las_file in in_las:
         try:
            las_bounds = get_las_bounds_single(in_las_file,
                                    from_header=from_header)

            if min_x is None:
               min_x = las_bounds[0][0]
            elif las_bounds[0][0] < min_x:
               min_x = las_bounds[0][0]

            if max_x is None:
               max_x = las_bounds[0][1]
            elif las_bounds[0][1] > max_x:
               max_x = las_bounds[0][1]

            if min_y is None:
               min_y = las_bounds[1][0]
            elif las_bounds[1][0] < min_y:
               min_y = las_bounds[1][0]

            if max_y is None:
               max_y = las_bounds[1][1]
            elif las_bounds[1][1] > max_y:
               max_y = las_bounds[1][1]

            if min_z is None:
               min_z = las_bounds[2][0]
            elif las_bounds[2][0] < min_z:
               min_z = las_bounds[2][0]

            if max_z is None:
               max_z = las_bounds[2][1]
            elif las_bounds[2][1] > max_z:
               max_z = las_bounds[2][1]

         except Exception as err:
            dem_common_functions.WARNING('Could not get bounds for {}'.format(in_las_file))

      return [[min_x,max_x],
              [min_y,max_y],
              [min_z,max_z]]
   else:
      raise Exception('Did not understand input, expected string or list')
