ARSF DEM Scripts
=================

About
------

A collection of scripts developed by the [NERC](http://www.nerc.ac.uk/) Airborne Research Facility
Data Analysis Node (NERC-ARF-DAN; https://nerc-arf-dan.pml.ac.uk) for working with DEMs.

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

Contributing                                                                    
---------------                                                                 

### Internal (within PML)                                                  

Internal development takes place using an in-house GitLab instance. Clone from the internal GitLab and create a branch from 'development-branch'. Push this branch to GitLab and submit a merge request (into 'development-branch') once changes are ready to be reviewed. Once changes have been merged into 'development-branch' push them to GitHub. Merge into master branch before tagging a new release.

### External                                                       

External contributions are welcome.                                             

If you have found a bug or would like to suggest new features create an issue providing as much detail as possible.

If you would like to contribute to the code create a fork and make changes into the branch 'development-branch'. Submit a pull request once you are ready for your changes to be merged.
Please note, due to internal PML remote sensing group (RSG) coding guidelines a three space indent is used - any new code must stick to this convention.






