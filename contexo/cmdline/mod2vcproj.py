#! /usr/bin/env python

info = """
###############################################################################
#                                                                             
#   mod2vcproj.py                                                             
#   Accessory of Contexo - (c) Scalado AB 2007                                
#                                                                             
#   Author: Robert Alm (robert.alm@scalado.com)                               
#                                                                             
#   ------------                                                              
#                                                                             
#   Translates a range of code modules + build configuration into a           
#   Visual Studio project.                                                    
#                                                                             
#   Usage:                                                                    
#
#   --cm       Code modules to translate.
#                                                                              
#   --bc       Single build configuration to include. Include paths, 
#              preprocessor symbols and compiler flags are extracted from this
#              file.          
#
#   --name     The name of the VS project file and output library. 
#
#   --release  [optional] If specified, the resulting VS projects will be set
#              to debug mode. Otherwise debug mode is used. Note that this 
#              option does not affect any potential debugging parameters 
#              introduced by the build configuration specified with the --bc 
#              option.
#
#   --o        [optional] The output directory where resulting files are 
#              created. Will be created if not already present. Current working 
#              directory is used if omitted.
#
#   --optfile  [optional] Option file with commandline options. 
#
#
#   Random notes:
#
#   All code module paths found in the locations specified by the system 
#   configuration variable CONTEXO_DEPEND_PATHS are appended as include paths 
#   to the VS projects created. Also, the 'inc' folder of all code modules are 
#   appended.
#                                                                             
###############################################################################
"""

import ctx_cmod
import sys
from ctx_common import *
from ctx_bc import *
from ctx_cmod import *
import ctx_msvc

msgSender = 'mod2vcproj.py'

##### ENTRY POINT #############################################################


if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)


#
# Process commandline (the first option is implicit)
#

knownOptions = ['--cm', '--bc', '--name', '--release', '--o', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )

#
# Check mandatory options
#

for opt in ['--cm', '--bc', '--name']:
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

for opt in ['--cm','--bc', '--o', '--name']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

modules     = options['--cm']
name        = options['--name'][0]
bcFile      = options['--bc'][0]
outputPath  = options['--o'][0]
debugmode   = bool( not options.has_key('--release') )


projName = name


# strip vcproj extension if the user included it.
if projName[ -7: ].lower() == '.vcproj':
    projName = projName[0:-7]

#
# Load build configuration.
#

bc = BCFile( bcFile )

buildParams = bc.getBuildParams()



#
# We append all codemodule paths available in system config CONTEXO_DEPEND_PATHS
# as include paths, rather than trying to figure out exactly which ones we actually need.
# Build time may increase, but we avoid complex logic extracting dependencies from
# dependency manager.
#

modTags = list()
incPaths    = list()
syscfg      = getSystemConfig()
depRoots    = syscfg['CONTEXO_DEPEND_PATHS']
for depRoot in depRoots:
    incPathCandidates = os.listdir( depRoot )
    for cand in incPathCandidates:
        path = os.path.join(depRoot, cand)
        if ctx_cmod.isContexoCodeModule( path ):
            rawMod = CTXRawCodeModule(path)
            incPaths.append( path )
            incPaths.append( os.path.join(rawMod.getRootPath(), rawMod.getPrivHeaderDir()) )
            modTags.append( 'COMPILING_MOD_' + string.upper( rawMod.getName() ) )


# If the user requested an exact replication of the components we create one vcproj
# per component library, otherwise we create one large library of all code modules
# specified in all components.


vcprojList = list() # list of dict['PROJNAME':string, 'LIBNAME':string, 'MODULELIST':listof( see doc of make_libvcproj7 ) ]


    
#codeModules = listof dictionaries: { MODNAME: string, SOURCES: list(paths), PRIVHDRS: list(paths), PUBHDRS: list(paths) } 
codeModules = list()

expMods = list() # all mods with potential *.lst files expanded.

for mod in modules:

    if mod[0] == '@':
        nameList = readLstFile( mod[1:] )
        for name in nameList:
            expMods.append( name )
    else:
        expMods.append( mod )

    
for mod in expMods:

    if mod[0] == '@':
        nameList = readLstFile( mod[1:] )
        for name in nameList:
            modules.append( ctx_cmod.CTXCodeModule(name) )
    
    srcFiles = list()
    privHdrs = list()
    pubHdrs  = list()
    
    rawMod = CTXCodeModule( mod )
    
    srcNames = rawMod.getSourceFilenames()
    for srcName in srcNames:
        srcFiles.append( os.path.join( rawMod.getSourceDir(), srcName ) )
    
    privHdrNames = rawMod.getPrivHeaderFilenames()
    for privHdrName in privHdrNames:
        privHdrs.append( os.path.join( rawMod.getPrivHeaderDir(), privHdrName ) )

    pubHdrNames = rawMod.getPubHeaderFilenames()
    for pubHdrName in pubHdrNames:
        pubHdrs.append( os.path.join( rawMod.getPubHeaderDir(), pubHdrName ) )
    
    if rawMod.hasExternalDependencies():
        extIncPaths = assureList(rawMod.resolveExternalDeps())
        incPaths.extend( extIncPaths )
    
        
    modDict = { 'MODNAME': mod, 'SOURCES': srcFiles, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs }
    codeModules.append( modDict )
    

# Assemble list of sourcepaths for the modules' sourcefiles.
srcFiles = list()
for mod in modules:
    rawMod = CTXRawCodeModule( mod )
    srcNames = rawMod.getSourceFilenames()
    for srcName in srcNames:
        srcFiles.append( os.path.join( rawMod.getSourceDir(), srcName ) )
        


vcprojList.append( { 'PROJNAME': projName, 'LIBNAME': name, 'MODULELIST': codeModules } )


if not os.path.exists( outputPath ):
    os.makedirs( outputPath ) 


guidDict = dict()    
for proj in vcprojList:
    ctx_msvc.make_libvcproj7( proj['PROJNAME'], buildParams.cflags, buildParams.prepDefines + modTags, proj['MODULELIST'], proj['LIBNAME'] + '.lib', debugmode, incPaths, outputPath, proj['PROJNAME'] )
    
