#! /usr/bin/env python

info = """
###############################################################################
#                                                                             
#   cleanmod.py
#   Component of Contexo commandline tools - (c) Scalado AB 2006
#                                                                             
#   Author: Robert Alm (robert.alm@scalado.com)
#                                                                             
#   ------------
#                                                                             
#   Cleans intermediates from built code modules.
#                                                                             
#   Usage:
#                                                                             
#   cleanmod.py --cm code modules [--bc BC-files] [--optfile filename]
#
#   Options:
#
#   --cm     One or more code module names to clean intermediates from. The 
#            system config variable CONTEXO_CODEMODULE_PATHS specifies where 
#            to search for the given modules. This parameter can also be a list 
#            file. See examples further down.
#
#   --bc     [optional] One or more specific build configurations to clean. 
#            If omitted, intermediates for all previously built configurations
#            are cleaned.
#
#   --optfile [optional] Option file with commandline options. See Option files 
#             for further information.
#
#
###############################################################################
"""

import os
import shutil
import sys
import string
import ctx_config
import ctx_bc
import ctx_cmod
from ctx_common import *

msgSender = 'cleanmod.py'

##### ENTRY POINT #############################################################


if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)

#
# Process commandline
#

knownOptions = ['--cm', '--bc', '--optfile']
expandOptionFiles = True
options = digestCommandline( sys.argv[1:], expandOptionFiles, knownOptions )

#
# Check mandatory options
#

for opt in ['--cm',]:
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

for opt in ['--cm']:
    if len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

moduleNames = options['--cm']
bcFiles     = options['--bc']

#
# Load build configuration and init build session
#

modules = list()
for moduleName in moduleNames:
    if moduleName[0] == '@':
        nameList = readLstFile( moduleName[1:] )
        for name in nameList:
            modules.append( ctx_cmod.CTXCodeModule(name) )
    else:
        modules.append( ctx_cmod.CTXCodeModule(moduleName) )

infoMessage( "Cleaning intermediates...", 1 )

for module in modules:
    if len(bcFiles) == 0:
        module.clean()
    else:
        for bcFile in bcFiles:
            module.clean( ctx_bc.BCFile(bcFile).getTitle() )

    
