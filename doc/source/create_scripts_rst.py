#!/usr/bin/env python
"""
Script to generate .rst file for scripts documentation. Runs scripts to get output and
inserts into text.

Inspired by answer suggesting modifying Makefile here:

http://stackoverflow.com/questions/7250659/python-code-to-generate-part-of-sphinx-documentation-is-it-possible

"""

import subprocess
import os

def get_command_out(command):
   """ Get output from command """

   out = subprocess.Popen(command,stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)

   (stdout, stderr) = out.communicate()

   out_tabs = ''

   for line in stdout.decode().split('\n'):
      out_tabs += '   {}\n'.format(line)

   return out_tabs

outfile = os.path.join(os.path.split(__file__)[0],'scripts.rst')

# Run commands and get output
create_apl_dem_out = get_command_out(['create_apl_dem.py','-h'])
create_dem_from_lidar_out = get_command_out(['create_dem_from_lidar.py','-h'])
las_to_dsm_out = get_command_out(['las_to_dsm.py','-h'])
las_to_dtm_out = get_command_out(['las_to_dtm.py','-h'])
las_to_intensity_out = get_command_out(['las_to_intensity.py','-h'])
mosaic_dem_tiles_out = get_command_out(['mosaic_dem_tiles.py','-h'])
load_lidar_to_grass_out = get_command_out(['load_lidar_to_grass.py','-h'])

scripts_text = '''

ARSF DEM Scripts
================

The following command line tools are provided by ARSF DEM.

Note under Windows, there is no need to type the '.py' at the end of the scripts. Batch files have been created to run the Python scripts, which don't need an extension to be provided.

create_apl_dem
-------------------

.. code-block:: bash

{}

create_dem_from_lidar
-------------------------

.. code-block:: bash

{}

las_to_dsm
--------------

.. code-block:: bash

{}

las_to_dtm
--------------

.. code-block:: bash

{}

las_to_intensity
------------------

.. code-block:: bash

{}

mosaic_dem_tiles
------------------

.. code-block:: bash

{}

load_lidar_to_grass
---------------------

.. code-block:: bash

{}

'''.format(create_apl_dem_out,
           create_dem_from_lidar_out,
           las_to_dsm_out,
           las_to_dtm_out,
           las_to_intensity_out,
           mosaic_dem_tiles_out,
           load_lidar_to_grass_out)

f = open(outfile,'w')
f.write(scripts_text)
f.close()
