ARSF DEM Scripts
=================

Installation
-------------

Install using:

   python setup.py install --prefix=~/install/path

Config file
------------

The parameters for configuration are stored in `arsf_dem/arsf_dem.cfg`
by changing these values you can adjust system level default values.

It is also possible to copy the config folder to `~/.arsf_dem` to 
overwrite the settings for a user or to `arsf_dem.cfg` within the current
working directory to overwite the settings for a project.

Documentation
--------------

Documentation for each function is stored as standard Python docstrings. You can generate Sphinx documentation by running:

   make html

from within 'doc'
