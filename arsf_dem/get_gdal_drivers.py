"""
get_gdal_drivers.py

General library to get driver names and extensions for all supported
GDAL drivers.

Author: Dan Clewley (dac)
Date: 07/05/2015

License restrictions: None known. Uses GDAL (MIT/X license)

Known issues: Some drivers must be used with creation options to get the desired
output. For example .bil and .bsq both use the ENVI driver but must use creation
options to specify the interleave.

Available functions:

* GDALDrivers().get_driver_from_ext - Get GDAL driver from extension
* GDALDrivers().get_ext_from_driver - Get extension from GDAL driver name
* GDALDrivers().get_creation_options_from_ext - Get GDAL creation options from extension
* GDALDrivers().get_creation_options_from_driver - Get GDAL creation options driver name

"""

from osgeo import gdal

#: List of Non-GDAL extensions (mostly for ENVI)
NON_GDAL_DRIVER_FROM_EXT = {'bil' : 'ENVI',
                            'bsq' : 'ENVI',
                            'bip' : 'ENVI',
                            'dem' : 'ENVI',
                            'raw' : 'ENVI',
                            'h5'  : 'HDF5',
                            'tiff': 'GTiff'}

#: Preferred creation options for GDAL
GDAL_CREATION_OPTIONS = {'bil' : ['INTERLEAVE=BIL'],
                         'bsq' : ['INTERLEAVE=BSQ'],
                         'tif' : ['COMPRESS=LZW'],
                         'nc'  : ['FORMAT=NC4C', 'COMPRESS=DEFLATE']}

class GDALDrivers(object):
   """
   Class to get GDAL drivers or
   extensions.

   Gets list of all available GDAL drivers and adds some
   additional extensions for existing drives (e.g., for ENVI)

   Example usage::

      import get_gdal_drivers
      get_gdal_drivers.GDALDrivers().get_driver_from_ext('.tif')
      get_gdal_drivers.GDALDrivers().get_ext_from_driver('GTiff')

   """

   def __init__(self):
      # Set up two empty dictionaries
      # One uses the extension as the key and one the driver
      self.gdal_ext_from_driver = {}
      self.gdal_driver_from_ext = {}

      # Go through all drivers registered to GDAL
      for driver_num in range(gdal.GetDriverCount()):
         try:
            driver = gdal.GetDriver(driver_num)
            driver_ext = driver.GetMetadata()['DMD_EXTENSION']

            # For ENVI use BSQ (will get this if we don't pass in creation options)
            if driver.ShortName == 'ENVI':
               driver_ext = 'bsq'

            # If there is no extension, use the driver name in lower case
            if driver_ext == '':
               driver_ext = driver.ShortName.lower()

            # Add to dictionaries
            self.gdal_ext_from_driver[driver.ShortName] = driver_ext
            self.gdal_driver_from_ext[driver_ext] = driver.ShortName

         # If they don't have an extension specified - skip
         except KeyError:
            pass
      # Add non-GDAL drivers
      self.gdal_driver_from_ext.update(NON_GDAL_DRIVER_FROM_EXT)

   def get_driver_from_ext(self, file_ext):
      """
      Get GDAL driver short name from file
      extension.

      :param file_ext: File extension (e.g., .bil)
      :type file_ext: str

      """
      # Remove '.' if there is one before the extension.
      file_ext = file_ext.lstrip('.')
      try:
         return self.gdal_driver_from_ext[file_ext]
      except KeyError:
         raise KeyError('The driver for file extension {} could not be found'.format(file_ext))

   def get_ext_from_driver(self, driver_name):
      """
      Get file extension from GDAL short
      driver name.

      :param driver_name: Driver Name (e.g., GTiff)
      :type driver_name: str

      """
      try:
         return '.' + self.gdal_ext_from_driver[driver_name]
      except KeyError:
         raise KeyError('The extension for driver {} could not be found'.format(driver_name))

   def get_creation_options_from_ext(self, file_ext):
      """
      Get preferred GDAL creation options from file
      extension.

      :param file_ext: File extension (e.g., .bil)
      :type file_ext: str

      """
      # Remove '.' if there is one before the extension.
      file_ext = file_ext.lstrip('.')
      try:
         return GDAL_CREATION_OPTIONS[file_ext]
      except KeyError:
         # If there are no creation options defined return an empty list
         return []

   def get_creation_options_from_driver(self, driver_name):
      """
      Get preferred GDAL creation options from file
      extension.

      :param driver_name: Driver Name (e.g., GTiff)
      :type driver_name: str

      """
      file_ext = self.get_ext_from_driver(driver_name)
      file_ext = file_ext.lstrip('.')
      try:
         return GDAL_CREATION_OPTIONS[file_ext]
      except KeyError:
         # If there are no creation options defined return an empty list
         return []

   def get_all_gdal_extensions(self):
      """
      Get all available GDAL extensions
      """
      return self.gdal_driver_from_ext.keys()

   def get_all_gdal_drivers(self):
      """
      Get all available GDAL drivers
      """
      return self.gdal_ext_from_driver.keys()

