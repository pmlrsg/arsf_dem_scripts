Installation
============

For the scripts to work a number of other software packages, coordinate transform and offset files are also required.

Required Software:

* Python (Needs to be the same version used by GRASS, currently 2.7)
* GRASS

Optional Software:

* LAStools (free/paid) - Free tools required for importing LAS files, paid tools can be used to create DTMs/DSMs.
* SPDLib - Can be used to create DTMs/DSMs.
* laspy - Used to get bounds of LAS file (if not available will use ASCII).

Windows
--------

The recommended way to install is using the OSGeo4W installer:

1. Download the OSGeo4W installer from: http://trac.osgeo.org/osgeo4w/
2. Select Advanced install and select 'QGIS Full' and 'GRASS' from Desktop applications, choose the standard install location of C:\OSGeo4W
3. (Optional, required for LAS files) Download LAStools from http://lastools.org, unzip the folder and copy LAStools to the C drive. 
4. Download the arsf_dem library, open a command prompt and navigate to the directory the code was downloaded to. Then run:

.. code-block:: bash

   python setup.py
   sudo python setup.py install

For more information on installing Python modules see https://docs.python.org/2/install/.

Linux
------

1. Install GRASS from the package manager using::

.. code-block:: bash

   sudo yum install grass

If you are using a Red Hat derivative e.g., Fedora or CentOS.
For a Debian derivative (e.g., Ubuntu) use:
      
.. code-block:: bash

   sudo apt-get install grass

2. Install the arsf_dem library using::
   
.. code-block:: bash

   python setup.py
   sudo python setup.py install

OS X
-----

1. Follow the instructions to install GRASS from http://www.kyngchaos.com/software/grass
2. Install the arsf_dem library using::
   
.. code-block:: bash

   python setup.py
   sudo python setup.py install
   





