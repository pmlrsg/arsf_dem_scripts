ARSF DEM Scripts
=================

About
------

A collection of scripts developed by the Airborne Research and Survey Facility
Data Analysis Node (ARSF-DAN; https://arsf-dan.nerc.ac.uk/trac/) for working with DEMs.

Licensing
----------

This software is available under the General Public License (GPL) Version 3.
See the file 'LICENSE' for more details.

Installation
-------------

For the scripts to work a number of other software packages, coordinate transform and offset files are also required.

Required Software:

* GRASS
* Python (Needs to be the same version used by GRASS, currently 2.7)
* LAStools (free/paid) - Free tools required for importing LAS files, paid tools can be used to create DTMs/DSMs.

Following installation of these packages, install ARSF DEM scripts using:

   python setup.py install --prefix=~/install/path

More advanced functionality (e.g., coordinate transforms) requires additional files and packages.

For more details on installation see [installation](doc/source/installation.rst).

Usage
------

See the [tutorial](doc/source/tutorial_lidar.rst) for more details on creating DEMs from LiDAR data and
the [scripts](doc/source/scripts.rst) page for details on available scripts.
