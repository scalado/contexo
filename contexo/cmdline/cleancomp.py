#! /usr/bin/env python

info = """
###############################################################################
#                                                                             
#   cleancomp.py
#   Component of Contexo commandline tools - (c) Scalado AB 2006
#                                                                             
#   Author: Robert Alm (robert.alm@scalado.com)
#                                                                             
#   ------------
#                                                                             
#   Cleans intermediates from built components.
#                                                                             
#   Usage:
#                                                                             
#   cleancomp.py --comp COMP-files [--bc BC-files]
#
#   Options:
#
#   --comp   Components to clean intermediates from.
#
#   --bc     [optional] One or more specific build configurations to clean. 
#            If omitted, intermediates for all previously built configurations
#            are cleaned.
#
#   --optfile [optional] Option file with commandline options. See Option files
#            for further information.
#
#   Return:
#
###############################################################################
"""

import os
import shutil
import sys
import string
import config
import ctx_bc
import ctx_comp
from ctx_common import *

msgSender = 'cleancomp.py'

##### ENTRY POINT #############################################################


if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)

#
# Process commandline
#

knownOptions = ['--comp', '--bc', '--optfile']
expandOptionFiles = True
options = digestCommandline( sys.argv[1:], expandOptionFiles, knownOptions )

#
# Check mandatory options
#

for opt in ['--comp',]:
    if opt not in options.keys():
        userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )

#
# Assign default values to omitted options
#

if not options.has_key( '--bc' ):
    options['--bc'] = list()
    
#
# Check for required option arguments
#

for opt in ['--comp']:
    if len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

compFiles   = options['--comp']
bcFiles     = options['--bc']

#
# Load build configuration and init build session
#

infoMessage( "Cleaning intermediates...", 1 )
 
for compFile in compFiles:
    bcList = list()
    for bcFile in bcFiles:
        bcList.append( ctx_bc.BCFile( bcFile ) )

    comp = ctx_comp.COMPFile( compFile )
    comp.clean( bcList )
    
