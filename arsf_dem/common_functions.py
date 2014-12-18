#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
Copy of common ARSF Python functions required
by arsf_dem.

Functions have been modified so they should also work under Windows.

License Restrictions: PrintTermWidth uses code from GPLv3 library

"""

from __future__ import print_function # Import print function (so we can use Python 3 syntax with Python 2)
import os
import sys
import select
import inspect
import subprocess

def WARNING(strOutput):
   """Function that emphasises text in the terminal"""
   #Black background + bold white text
   if sys.platform.find('win') < 0:
      print('\033[40;37;1m'+strOutput+'\033[0m')
   # If on windows don't bother trying to change colours, it won't work
   else:
      print(strOutput)
      
def ERROR(strOutput,tostdouttoo=False):
   """Function that emphasises text in the sys.stderr stream"""

   try:
      callerid="%s : %s"%(inspect.stack()[1][1],inspect.stack()[1][3])

   except:
      callerid=""

   if sys.platform.find('win') < 0:
      print('\033[41;33;1m'+"Error in "+callerid+": "+str(strOutput)+'\033[0m', file=sys.stderr)
      if tostdouttoo:
         print('\033[41;33;1m'+"Error in "+callerid+": "+str(strOutput)+'\033[0m', file=sys.stdout)
   else:
      # If on windows don't bother trying to change colours, it won't work
      print("Error in "+callerid+": "+str(strOutput), file=sys.stderr)

def CallSubprocessOn(command=None,redirect=False,quiet=False):
   """
   CallSubprocessOn - run a command via subprocess and output stdout and stderr
   if redirect == True the returns the stdout/stderr rather than printing
   if quiet == True will not print out command it is running
   """
   if command is None:
      raise TypeError("Command to be run must be specified")

   if isinstance(command,str):
      command_to_run=command.split(' ')
   elif isinstance(command,list):
      command_to_run=command
   else:
      raise TypeError("Expected command to be list or space separated string")

   if not quiet:
      print("\nAttempting to run command: "+" ".join(str(x) for x in command_to_run))

   redirecttext=[]
   try:
      process=subprocess.Popen(command_to_run,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
      # If on Windows don't try to run this, as it doesn't work
      if sys.platform.find('win') < 0:
         while process.poll() is None:
            if redirect==False and not quiet:
               lines, _, _ =select.select([process.stdout,process.stderr],[],[],0.1)
               if lines:#if there is data read a line of it
                  someline=lines[0].readline()
                  if someline:
                     print(someline.rstrip())
                  
      #Get anything left over in buffer
      stdout,stderr=process.communicate()
      if redirect==True:
         redirecttext=[stdout,stderr]

      #only output if not redirecting and not quiet
      elif stdout and redirect==False and not quiet:
         print(stdout)

      #still output error if quiet but not if redirecting
      #elif stderr and redirect==False: ERROR(stderr)
      elif stderr and redirect==False: 
         raise StandardError(stderr)
      
   except StandardError as e:
      raise

   if redirecttext:
      return True,redirecttext
   else:
      return True

def PrintTermWidth(text, padding_char=' '):
   """
   Prints a string padding with a character so the string is in the centre of the 
   terminal.

   Function modified from one in https://bitbucket.org/chchrsc/envmaster by 
   Sam Gillingham and make available under GPLv2 License

   """
   # Try to get terminal width, not possible on Windows so will
   # raise exception.
   try:
      import termios
      import fcntl
      import struct

      # Get number of rows and columns in terminal
      data = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ,'1234')
      (textrows,textcols) = struct.unpack('hh', data)

      # put some spaces around it
      if text != '':
         paddedtext = ' {} '.format(text)
      # If an empty string is passed in don't want to print a message
      # just a line of 'padding_chars', in this case don't want a 
      # space (as this will look silly).
      else:
         paddedtext = text
      # how many padding symbols
      nequals = textcols - len(paddedtext)
      # put both sizes of the text
      paddedtext = padding_char * int(nequals / 2) + paddedtext
      paddedtext += padding_char * (textcols - len(paddedtext))
      # write it out
   # Default is to place a single character each side with spaces.
   except Exception:
      paddedtext = ' {0} {1} {0} '.format(padding_char,text)
   
   print(paddedtext)

