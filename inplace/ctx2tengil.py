#!/usr/bin/env python
#
# This file is for in-place execution of contexo.
# It adds local module directories to module search path and executes the local ctx.py
# Meaning no need to install efter each modification. Useful for development.
# This file needs to be updated when the structure of Contexo repository changes
#
# The Idle editor is known to run scripts as-is, without treating them as a module, meaning the __file__ attribute will not be created.
# Running it with ordinary pyhon interpreter works well.
#

#This is the structure this file currently assumes:
# * - directories of interest here

#/*
#|-contexo
#|       |-inplace
#|       |    '-ctx.py
#|       |-cmdline*
#|       |      |-ctx.py
#|       |      '-[...]
#|       |-platform
#|       |-plugins
#|       \-ctx_[modulename].py [...]
#|
#|-otherlibs*
#\-setup.py

import sys
import os.path

(contexopath,  filename) = os.path.split( os.path.abspath(__file__))
(rootpath,  contexodir) = os.path.split( contexopath)
contexopath = os.path.join( rootpath, 'contexo')
commandlinedir = os.path.join( contexopath, 'cmdline')
plugindir = contexopath + os.sep + 'plugins' + os.sep + 'export'

# print 'rootpath: ' + rootpath
# print 'contexopath: ' + contexopath
# print 'commandlinedir: ' + commandlinedir
# print 'plugindir: ' + plugindir
# print 'filename: ' + filename
#
sys.path.insert(1,  str(os.path.join(rootpath, 'otherlibs' ) ) ) #'otherlibs'
sys.path.insert(1,  rootpath ) #root
execfile(os.path.join(commandlinedir, filename)) #'/path/to/contexo/cmdline/ctx.py'
