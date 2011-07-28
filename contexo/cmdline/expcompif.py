#! /usr/bin/env python

info = """
###############################################################################
#                                                                             #
#   expmodif.py                                                               #
#   Accessory of Contexo - (c) Scalado AB 2007                                #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Exports all public interface headers from given code modules to a         #
#   destination directory.                                                    #
#                                                                             #
#   Usage:                                                                    #
#                                                                             #
#   expcompif.py --comp code-modules [--o destination] [--optfile filename]      #
#                                                                             #
#   All code modules listed are searched for in the paths given through the   #
#   CONTEXO_CODEMODULE_PATHS system config variable.                          #
#                                                                             #
#   --comp      List of code modules to exporte module interface from.          #
#                                                                             #
#   --o       [optional] Export destination directory. Current working        #
#             directory is used if omitted.                                   #
#   --sc     [optional] Specifies that a subdirectory for each component should be 
#            created beneath the given output directory. The name of the 
#            subdirectory will always equal the NAME of the component.
#                                                                             #
#   --optfile [optional] Option file with commandline options.                #
#                                                                             #
#                                                                             #
###############################################################################
"""

import ctx_cmod
from ctx_common import *
from ctx_comp import *
import sys

msgSender = 'expcompif.py'

##### ENTRY POINT #############################################################

if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)
    
#
# Process commandline
#

knownOptions = ['--comp', '--o', '--sc', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )
    
#
# Check mandatory options
#

for opt in ['--comp']:
    if opt not in options.keys():
        userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )


#
# Assign default values to omitted options
#

if not options.has_key( '--o' ):
    options['--o'] = [os.getcwd(),]
    
#
# Check for required option arguments
#

for opt in ['--comp', '--o']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )
        
compSubDirs = bool( options.has_key('--sc') )

#
# Assemble list of modules, expand list files if present
#

compFiles   = options['--comp']
preloadModules = list()
components = list()
for compFile in compFiles:
    comp = COMPFile( compFile )
    components.append( comp )
    for library, modules in comp.libraries.iteritems():
        preloadModules.extend( assureList(modules) )
    
#
# Export headers
#

outputPath = options['--o'][0]

#
# Build components
#

for comp in components:
    comp.copyPublicHeaderFiles( None, outputPath, None, compSubDirs )

