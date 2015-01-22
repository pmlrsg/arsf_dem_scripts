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

   return stdout

outfile = os.path.join(os.path.split(__file__)[0],'scripts.rst')

create_apl_dem_out = get_command_out(['create_apl_dem.py','-h'])
create_apl_dem_out = create_apl_dem_out.replace('create_apl_dem.py','.. code-block:: bash\n\n   create_apl_dem.py')
create_apl_dem_out = create_apl_dem_out.replace('gdalbuildvrt','.. code-block:: bash\n\n   gdalbuildvrt')

create_dem_from_lidar_out = get_command_out(['create_dem_from_lidar.py','-h'])
create_dem_from_lidar_out = create_dem_from_lidar_out.replace('create_dem_from_lidar.py','.. code-block:: bash\n\n   create_dem_from_lidar.py')

scripts_text = '''

ARSF DEM Scripts
================

Note under Windows, there is no need to type the '.py' at the end of the scripts. Batch files have been created to run the Python scripts, which don't need an extension to be provided.

create_apl_dem.py
-------------------

.. code-block:: bash

   {}

create_dem_from_lidar.py
-------------------------

.. code-block:: bash

   {}

'''.format(create_apl_dem_out, create_dem_from_lidar_out)

f = open(outfile,'w')
f.write(scripts_text)
f.close()
