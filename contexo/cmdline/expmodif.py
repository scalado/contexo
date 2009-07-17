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
#   expmodif.py --cm code-modules [--o destination] [--optfile filename]      #
#                                                                             #
#   All code modules listed are searched for in the paths given through the   #
#   CONTEXO_CODEMODULE_PATHS system config variable.                          #
#                                                                             #
#   --cm      List of code modules to exporte module interface from.          #
#                                                                             #
#   --o       [optional] Export destination directory. Current working        #
#             directory is used if omitted.                                   #
#                                                                             #
#   --optfile [optional] Option file with commandline options.                #
#                                                                             #
#   Example:                                                                  #
#                                                                             #
#   c:\> expmodif.py --cm scbstr oslmem scbutil --o c:/dev/include            #
#                                                                             #
#   This commandline will result in scbstr.h, oslmem.h and scbutil.h being    #
#   copied to "c:/dev/include"                                                #
#                                                                             #
###############################################################################
"""

import ctx_cmod
from ctx_common import *
import sys

msgSender = 'expmodif.py'

##### ENTRY POINT #############################################################

if len(sys.argv) == 1:
    print info
    ctxExit(0)
    
#
# Process commandline
#

knownOptions = ['--cm', '--o', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )
    
#
# Check mandatory options
#

for opt in ['--cm']:
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

for opt in ['--cm', '--o']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Assemble list of modules, expand list files if present
#

moduleNames = options['--cm']
modules = list()
for moduleName in moduleNames:
    if moduleName[0] == '@':
        nameList = readLstFile( moduleName[1:] )
        for name in nameList:
            modules.append( ctx_cmod.CTXRawCodeModule(name) )
    else:
        modules.append( ctx_cmod.CTXRawCodeModule(moduleName) )
    
#
# Export headers
#

destdir = options['--o'][0]
    
for cm in modules:
    modroot = cm.getRootPath()
    hdrlist = cm.getPubHeaderFilenames()
    if not os.path.exists ( destdir ):
        os.mkdir (destdir)
    for hdr in hdrlist:
        src = os.path.join( modroot, hdr )
        dst = os.path.join( destdir, hdr )
        shutil.copyfile( src, dst )

