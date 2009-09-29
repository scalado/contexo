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
#|       |
#|       |-cmdline*
#|       |      |-ctx.py
#|       |      |-ctx-devel.py
#|       |      \ [...]
#|       |
#|       |-platform
#|       |-plugins
#|       \-ctx_[modulename].py [...]
#|
#|-otherlibs*
#\-setup.py

import sys
import os.path

(contexopath,  commandlinedir) = os.path.split( os.path.dirname(__file__) )
(rootpath,  contexodir) = os.path.split( contexopath)

sys.path.insert(1,  str(os.path.join(rootpath, 'otherlibs' ) ) ) #'otherlibs'
sys.path.insert(1,  rootpath ) #root
execfile(os.path.join(contexopath,  commandlinedir,  'ctx.py')) #'/path/to/contexo/cmdline/ctx.py'
