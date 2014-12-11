ARSF DEM Scripts
=================

These scripts are currently still in development and are not yet part of the main ARSF operational code. 

As they are designed to replace many existing DEM scripts the plan is to move them to operational following a tidy up of existing DEM scripts (possibly after we move to git).

For testing the scripts can be run from dac's home directory by running:

   source ~dac/dem_scripts_update/load_new_dem_scripts

to add them to your PATH and PYTHONPATH.

Submit any bugs or general feedback to:

https://arsf-dan.nerc.ac.uk/trac/ticket/545

(dac 11/12/14)

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
