#! /usr/bin/env python

info = """
#
#   buildmod.py
#   Component of Contexo commandline tools - (c) Scalado AB 2006
#
#   Author: Robert Alm (robert.alm@scalado.com)
#           Manuel Astudillo (manuel.astudillo@scalado.com)
#
#   ------------
#
#   Builds one or more code modules.
#
#   Usage:
#
#   buildmod.py --cm code modules --bc BC-file [--lib library title]
#               [--o outputdir] [--h] [--sh headerDir] [--sl libraryDir]
#               [--env [ENV-files]] [--optfile [filename]]
#
#   Options:
#
#   --cm     One or more code module names to build. The system config variable
#            CONTEXO_CODEMODULE_PATHS specifies where to search for the given
#            modules. This parameter can also be a list file. See examples
#            further down.
#
#   --bc     Single build configuration to build with.
#
#   --lib    [optional] Title of the output library (excluding extension) to
#            produce from all built code modules. If this paramter is omitted,
#            each code module is built into a library with the same name as the
#            code module.
#
#   --o      [optional] Output directory. Current working directory is used if
#            omitted.
#
#   --sh     [optional] Subdirectory name for exported headerfiles (relative to
#            output directory). If this parameter is used, all public headers
#            of all built code modules are exported to the given folder. If not
#            used, no headers are exported.
#
#   --sl     [optional] Subdirectory name for library files.
#
#   --env    [optional] One or more ENV files (*.env) which the build system
#            should merge and switch to during build. When the build is
#            concluded the previous environment is restored.
#
#   --verb   [optional] If specified, the output verbose level is set to 4
#            during execution of the tool.
#
#   --optfile [optional] Option file with commandline options. See Option files
#             for further information.
#
"""

import os
import shutil
import sys
import string
import time
import config
import ctx_bc
import ctx_envswitch
import ctx_cmod
import ctx_base
from ctx_common import *


msgSender = 'buildmod.py'

##### ENTRY POINT #############################################################

#
# Check for contexo updates ( once a day )
#
if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)

timer = time.clock()

#
# Process commandline
#

knownOptions = ['--cm', '--bc', '--lib', '--o', '--sh', '--sl', '--env', '--verb', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )

#
# Check mandatory options
#

for opt in ['--cm', '--bc']:
    if opt not in options.keys():
        userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )

#
# Assign default values to omitted options
#

if not options.has_key( '--o' ):
    options['--o'] = [os.getcwd(),]

if not options.has_key( '--sl' ):
    options['--sl'] = ["",]

#
# Check for required option arguments
#

for opt in ['--cm','--bc','--o', '--env']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

moduleNames    = options['--cm']
bcFile         = options['--bc'][0]
outputPath     = options['--o'][0]

singleLib      = bool( options.has_key( '--lib' ) )
singleLibTitle = str()
if singleLib:
    singleLibTitle = options['--lib'][0]

libDir       = options['--sl'][0]

hdrExport    = bool( options.has_key('--sh') )
hdrExportDir = str()
if hdrExport:
    hdrExportDir = options['--sh'][0]

switchEnv   = bool( options.has_key('--env' ) )
envFiles = list()
if switchEnv:
    envFiles = options['--env']

    # Add our internal environment if not already done by user.
    sysEnv = os.path.join( getUserDir(), 'ctx.env')
    if sysEnv not in envFiles:
        envFiles.append( sysEnv )


verbose     = bool( options.has_key('--verb' ) )
if verbose:
    setInfoMessageVerboseLevel( 4 )


#
# Perform environment switch if required
#
global envRestore
global cleanupFuncStack
envLayout                = ctx_envswitch.EnvironmentLayout( envFiles )
oldEnv                   = ctx_envswitch.switchEnvironment( envLayout, envFiles, True )
envRestore               = oldEnv
cleanupFuncStack.append( ctx_envswitch.jitCleanup )
#:::::::::::::::::::::::::::::::::::::::




#
# Load build configuration and init build session
#

modules = list()
preloadModules = list()
for moduleName in moduleNames:
    if moduleName[0] == '@':
        nameList = readLstFile( moduleName[1:] )
        preloadModules.extend( assureList(nameList) )
        for name in nameList:
            modules.append( ctx_cmod.CTXCodeModule(name) )
    else:
        preloadModules.append(moduleName)
        modules.append( ctx_cmod.CTXCodeModule(moduleName) )

bc = ctx_bc.BCFile( bcFile )
session = ctx_base.CTXBuildSession( bc.getCompiler() )
session.setBuildParams( bc.getBuildParams() )

#
# Preload module dependencies
#

session.preloadDependencies( preloadModules )

#
# Determine and assure presence of directories for output.
#

libPath   = os.path.join( outputPath, libDir )

#
# Build either one library of all modules, or one library for each module.
#

if not os.path.exists( libPath ):
    os.makedirs( libPath )

if singleLib:
    obj = list()
    for module in modules:
        obj += module.buildStaticObjects( session, None, bc.getTitle() )

    session.buildStaticLibrary( obj, singleLibTitle, libPath )
else:
    for module in modules:
        obj = module.buildStaticObjects( session, None, bc.getTitle() )
        session.buildStaticLibrary( obj, module.getName(), libPath )

#
# Export headers if required.
#

if hdrExport:

    hdrExportPath = os.path.join( outputPath, hdrExportDir )
    if not os.path.exists( hdrExportPath ):
        os.makedirs( hdrExportPath )

    for module in modules:
        hdrList = module.getPubHeaderFilenames()
        for hdr in hdrList:
            src = os.path.join( module.getRootPath(), hdr )
            dst = os.path.join( hdrExportPath, hdr )
            shutil.copyfile( src, dst )



#:::::::::::::::::::::::::::::::::::::::
# Restore old environment.
#
ctx_envswitch.switchEnvironment( oldEnv, False )
envRestore = None
cleanupFuncStack.remove( ctx_envswitch.jitCleanup )

infoMessage( "Build duration: %.3f seconds"%(time.clock() - timer), 1, msgSender )
