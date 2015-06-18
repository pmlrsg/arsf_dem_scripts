Installation
============

For the scripts to work a number of other software packages, coordinate transform and offset files are also required.

Required Software:

* Python (Needs to be the same version used by GRASS, currently 2.7)
* GRASS
* LAStools (free/paid) - Free tools required for importing LAS files, paid tools can be used to create DTMs/DSMs.

Optional Software:

* SPDLib - Can be used to create DTMs/DSMs.
* laspy - Used to get bounds of LAS file (if not available will use ASCII).

Windows
~~~~~~~~

The recommended way to install GRASS is using the OSGeo4W installer:

1. Download the OSGeo4W installer from: http://trac.osgeo.org/osgeo4w/
2. Select Advanced install and select 'QGIS Full' and 'GRASS' from Desktop applications, choose the standard install location of C:\\OSGeo4W
3. Download the arsf_dem library, open a command prompt and navigate to the directory the code was downloaded to. Then run:

.. code-block:: bash

   python setup.py
   sudo python setup.py install

For more information on installing Python modules see https://docs.python.org/2/install/.

4. Download LAStools from http://lastools.org, unzip the folder and copy the folder 'LAStools' to the C drive.
5. (Optional) Download Windows binaries of SPDLib from https://bitbucket.org/petebunting/spdlib/downloads and copy the folder 'spdlib' to the C drive.

Linux
~~~~~~

1. Install GRASS from the package manager using:

.. code-block:: bash

   sudo yum install  grass

if you are using a Red Hat derivative e.g., Fedora or CentOS.
For a Debian derivative (e.g., Ubuntu) use:

.. code-block:: bash

   sudo apt-get install grass

2. Install the arsf_dem library using:

.. code-block:: bash

   python setup.py
   sudo python setup.py install

This will install the scripts to /usr/local/bin, so they will be available on the
main path.

3. Download the ARSF fork of LAStools from from https://github.com/arsf/LAStools and install using:

.. code-block:: bash

   make
   sudo make install


OS X
~~~~~

1. Follow the instructions to install GRASS from http://www.kyngchaos.com/software/grass

2. Install the arsf_dem library using:

.. code-block:: bash

   python setup.py
   sudo python setup.py install

3. Download the ARSF fork of LAStools from from https://github.com/arsf/LAStools and install using:

.. code-block:: bash

   make
   sudo make install

Configuration
---------------

There are a number of variables used by the DEM scripts to set default parameters,
locations of files (e.g., DEMs, separation files). These can be overridden by setting
them in 'arsf_dem.cfg', by default this file is installed to the same location as the
Python library. By placing a copy in the home directory (`~\.arsf_dem.cfg`) the settings
can be changed for a particular user. They can also be changed by placing a copy
of arsf_dem.cfg in the working directory.


