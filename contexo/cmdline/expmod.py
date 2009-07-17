#! /usr/bin/env python

info = """
###############################################################################
#                                                                             #
#   expmod.py                                                                 #
#   Accessory of Contexo - (c) Scalado AB 2007                                #
#                                                                             #
#   Author: Johannes Stromberg (johannes.stromberg@scalado.com)               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Exports all public interface headers from given code modules to a         #
#   destination directory.                                                    #
#                                                                             #
#   Usage:                                                                    #
#                                                                             #
#   expmod.py --cm code-modules [--osrc destination] [--oinc destination]     #
                    [--optfile filename]                                      #
#                                                                             #
#   All code modules listed are searched for in the paths given through the   #
#   CONTEXO_CODEMODULE_PATHS system config variable.                          #
#                                                                             #
#   --cm      List of code modules to exporte module interface from.          #
#                                                                             #
#   --oinc    [optional] Export destination directory for module include      #
#             files (public and private). Current directory is used if        #
              omitted.                                                        #
#                                                                             #
#   --osrc    [optional] Export destination directory for module source       #
              files. --oinc dir is used if omitted.                           #
#                                                                             #
#   --optfile [optional] Option file with commandline options.                #
#                                                                             #
#   Example:                                                                  #
#                                                                             #
#   c:\> expmod.py --cm scbstr oslmem scbutil --oinc c:/dev/include           #
#                           --osrc c:/dev/src                                 #
#                                                                             #
#                                                                             #
###############################################################################
"""

import ctx_cmod
from ctx_common import *
import sys

msgSender = 'expmod.py'

##### ENTRY POINT #############################################################

if len(sys.argv) == 1:
    print info
    ctxExit(0)
    
#
# Process commandline
#

knownOptions = ['--cm', '--osrc', '--oinc', '--optfile']
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

if not options.has_key( '--oinc' ):
    options['--oinc'] = [os.getcwd(),]
    
if not options.has_key( '--osrc' ):
    options['--osrc'] = [options['--oinc'][0],]
    
    
#
# Check for required option arguments
#

for opt in ['--cm', '--osrc', '--oinc']:
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

srcdir = options['--osrc'][0]
incdir = options['--oinc'][0]
    
for cm in modules:
    modroot = cm.getPubHeaderDir()
    privateroot = cm.getPrivHeaderDir()
    srcroot = cm.getSourceDir()
    hdrlist = map(lambda x: (os.path.join(modroot,x),os.path.join(incdir,x)),cm.getPubHeaderFilenames())
    hdrlist.extend(map(lambda x: (os.path.join(privateroot,x),os.path.join(incdir,x)),cm.getPrivHeaderFilenames()))
    hdrlist.extend(map(lambda x: (os.path.join(srcroot,x),os.path.join(srcdir,x)),cm.getSourceFilenames()))
    if not os.path.exists ( srcdir ):
        os.makedirs(srcdir)
    if not os.path.exists ( incdir ):
        os.makedirs(incdir)
    for hdr in hdrlist:
        src = hdr[0]
        dst = hdr[1]
        shutil.copyfile( src, dst )

