#! /usr/bin/env python

info = """
#
#   buildcomp.py
#   Component of Contexo commandline tools - (c) Scalado AB 2006
#
#   Authors: Robert Alm (robert.alm@scalado.com)
#            Manuel Astudillo (manuel.astudillo@scalado.com)
#
#   ------------
#
#   Builds one or more components from COMP files.
#
#   Usage:
#
#   buildcomp.py --comp COMP-files --bc BC-file [--o outputdir] [--sl libraryDir]
#                [--sh headerDir] [--sc] [--env [ENV-files]] [--log [filename]] [--optfile [filename]]
#
#   Options:
#
#   --comp   Components to build.
#
#   --bc     Single build configuration to build with.
#
#   --o      [optional] Output directory. Current working directory is used if omitted.
#
#   --sl     [optional] Subdirectory name for library files.
#
#   --sh     [optional] Subdirectory name for exported headerfiles (PUBLIC_HEADERS). If
#            this option is excluded, all exported headers will be placed with the
#            libraries of the component from which they are exported.
#
#   --sc     [optional] Specifies that a subdirectory for each component should be
#            created beneath the given output directory. The name of the
#            subdirectory will always equal the NAME of the component.
#
#   --env    [optional] One or more ENV files (*.env) which the build system should
#            merge and switch to during build. When the build is concluded the previous
#            environment is restored.
#
#   --log    [optional] Specifies that a build log file should be created. If filename
#            of the log is omitted, 'buildcomp.log' will be used instead.
#
#   --verb   [optional] If specified, the output verbose level is set to 4 during
#            execution of the tool.
#
#   --optfile [optional] Option file with commandline options.
#
#
#   Return:
#
"""


import os
import shutil
import sys
import string
import contexo.config
import time
from contexo import ctx_bc,  ctx_common,  ctx_envswitch,   ctx_log,   ctx_comp
import contexo.ctx_base
#from contexo import ctx_comp
#from ctx_common import *
#from ctx_envswitch import *
#from ctx_log import *
import contexo.ctx_cfg

msgSender = 'buildcomp.py'


CONTEXO_VERSION     = "ctx-0.3.0"
CONTEXO_CFG_FILE    = 'contexo.cfg'
CONTEXO_VIEW_FILE   = 'contexo.vdef'

#
# Get configuration.
#
cfgFile = ctx_cfg.CFGFile (os.path.join ( getUserDir (), CONTEXO_CFG_FILE ))

if len(sys.argv) == 1:
    print info
    ctx_common.ctxExit(0)


#
# Process commandline (the first option is implicit)
#

knownOptions = ['--comp', '--bc', '--o', '--sl', '--sh', '--sc', '--env', '--log', '--verb', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )

#
# Check mandatory options
#

for opt in ['--comp', '--bc']:
    if opt not in options.keys():
        ctx_common.userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )

#
# Assign default values to omitted options
#

if not options.has_key( '--o' ):
    options['--o'] = [os.getcwd(),]

if not options.has_key( '--sl' ):
    options['--sl'] = ["",]

if not options.has_key( '--sh' ):
    options['--sh'] = ["",]

#
# Check for required option arguments
#

for opt in ['--comp','--bc','--sl','--sh','--o', '--env']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        ctx_common.userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

compFiles   = options['--comp']
bcFile      = options['--bc'][0]
outputPath  = options['--o'][0]
libDir      = options['--sl'][0]
hdrDir      = options['--sh'][0]
switchEnv   = bool( options.has_key('--env' ) )
compSubDirs = bool( options.has_key('--sc') )
genLogFile  = bool( options.has_key('--log') )
logFilename = 'ctxbuildlog.xml'

if genLogFile and len(options['--log']) != 0:
    logFilename = options['--log'][0]

verbose     = bool( options.has_key('--verb' ) )
if verbose:
    ctx_common.setInfoMessageVerboseLevel( 4 )


envFiles = list()
if switchEnv:
    envFiles = options['--env']

    # Add our internal environment if not already done by user.
    sysEnv = os.path.join( getUserDir(), 'ctx.env')
    if sysEnv not in envFiles:
        envFiles.append( sysEnv )

#
# Perform environment switch if required
#
global envRestore
global cleanupFuncStack
envLayout                = EnvironmentLayout( envFiles )
oldEnv                   = switchEnvironment( envLayout, envFiles, True )
envRestore               = oldEnv
cleanupFuncStack.append( jitCleanup )
#:::::::::::::::::::::::::::::::::::::::

# Initialize log object
if genLogFile:
    ctx_log.ctxlogStart()

#
# Load build configuration and init build session
#


bc = ctx_bc.BCFile( bcFile, cfgFile )
session = ctx_base.CTXBuildSession( bc )

#LOG
ctx_log.ctxlogSetBuildConfig( bc.getTitle(), \
                      bc.getCompiler().cdefTitle,\
                      bc.getBuildParams().cflags, \
                      bc.getBuildParams().prepDefines,\
                      "N/A" )

#
# Create all component objects and collect all modules names involved.
#

preloadModules = list()
components = list()
for compFile in compFiles:
    comp = ctx_comp.COMPFile( compFile )
    components.append( comp )
    for library, modules in comp.libraries.iteritems():
        preloadModules.extend( assureList(modules) )

#
# preload dependencies for all modules that will be built
#

session.preloadDependencies( preloadModules )

#
# Build components
#

for comp in components:
    comp.build( session, bc, None, outputPath, libDir, hdrDir, compSubDirs )


# Write log file if requested
if genLogFile:
    ctx_log.ctxlogWriteToFile( os.path.join(outputPath, logFilename), False )

#:::::::::::::::::::::::::::::::::::::::
# Restore old environment.
#
ctx_envswitch.switchEnvironment( oldEnv, False )
envRestore = None
cleanupFuncStack.remove( jitCleanup )

ctx_common.infoMessage( "Build duration: %.3f seconds"%(time.clock() - timer), 1, msgSender )
