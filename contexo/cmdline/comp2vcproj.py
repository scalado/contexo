#! /usr/bin/env python

info = """
###############################################################################
#
#   comp2vcproj.py
#   Accessory of Contexo - (c) Scalado AB 2007
#
#   Author: Robert Alm (robert.alm@scalado.com)
#           Johannes Stromberg (johannes.stromberg@scalado.com)
#
#   ------------
#
#   Translates a range of components + build configuration into a
#   corresponding Visual Studio project.
#
#   Usage:
#
#   --comp     Components to translate.
#
#   --bc       Single build configuration to include. Include paths,
#              preprocessor symbols and compiler flags are extracted from this
#              file.
#
#   --exact    [optional] If specified, the translation will mirror the exact
#              distribution of libraries from each component, resulting in one
#              VS project for each library where the name of the project will
#              be used as name for both the library ad the project. If this
#              option is omitted, all sourcefiles from the given components
#              will be fitted into one single VS project. In this case the
#              --name option sets the name for the project and library,
#              otherwise the --name option is ignored (warning will be
#              displayed).
#
#   --name     [conditional] The name of the VS project file and output
#              library. If the --exact option is omitted, this option is
#              mandatory, otherwise it is ignored (warning will be displayed).
#
#   --sln      [optional] Specifies a VS solution filetitle. If this option is
#              used, a *.sln file is created (overwriting any existing) and all
#              VS projects produced are added to it. The solution will be
#              created at the location specified by the --o option.
#
#   --release  [optional] If specified, the resulting VS projects will be set
#              to debug mode. Otherwise debug mode is used. Note that this
#              option does not affect any potential debugging parameters
#              introduced by the build configuration specified with the --bc
#              option.
#
#   --platform [optional] If specified, the resulting VS projects will use
#              the specified platform. Otherwise "Win32" mode is used.
#              Note that this option does not affect any potential debugging
#              parameters introduced by the build configuration specified with
#              the --bc option.
#
#   --incpathsfile [optional] File with include paths to append to the include
#              directories of all VS projects generated. The paths in the file
#              can be separated by line or by semicolon.
#
#   --exevcproj [optional] Specifies a VS project filetitle. If this option is
#              used, the AdditionalIncludeDirectories for the compiler will be
#              the same as the for the generated vcproj files.
#              if the --sln option is specified it will be appended to the
#              *.sln file with dependencies on all other projects.
#
#   --o        [optional] The output directory where resulting files are created.
#              Will be created if not already present. Current working directory is
#              used if omitted.
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
#
###############################################################################
"""

import ctx_cmod
import sys
from ctx_common import *
from ctx_bc import *
from ctx_comp import *
from ctx_cmod import *
import ctx_msvc

msgSender = 'comp2vcproj.py'

##### ENTRY POINT #############################################################


if len(sys.argv) == 1:
    print info
    ctxExit(0)


#
# Process commandline (the first option is implicit)
#

knownOptions = ['--comp', '--bc', '--exact', '--name', '--sln', '--release', \
                '--o', '--optfile','--platform','--incpathsfile','--exevcproj']
options = digestCommandline( sys.argv[1:], True, knownOptions )

#
# Check mandatory options
#

for opt in ['--comp', '--bc']:
    if opt not in options.keys():
        userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )

#
# Assign default values to omitted options
#

if not options.has_key( '--o' ):
    options['--o'] = [os.getcwd(),]

if not options.has_key( '--platform' ):
    options['--platform'] = ['Win32',]

#
# Check for required option arguments
#

for opt in ['--comp','--bc', '--o', '--name', '--platform', '--incpathsfile', \
            '--exevcproj']:
    if options.has_key( opt ) and len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

#
# Prepare all build parameters from the digested commandline
#

compFiles   = options['--comp']
bcFile      = options['--bc'][0]
outputPath  = options['--o'][0]
exact       = bool( options.has_key('--exact') )
debugmode   = bool( not options.has_key('--release') )
platform = options['--platform'][0]

exevcproj = None
if options.has_key('--exevcproj'):
    exevcproj = ctx_msvc.get_info_vcproj8(os.path.abspath(options['--exevcproj'][0]))
    exevcproj['DEBUG'] = debugmode


slnName = None
if options.has_key( '--sln' ):
    slnName = options['--sln'][0]

#
# Parse additional include paths
#

additionalIncPaths = []
if options.has_key('--incpathsfile'):
    incpathsfile = options['--incpathsfile'][0]
    if not os.path.exists( incpathsfile ):
        userErrorExit( "Cannot find option file '%s'"%incpathsfile )

    file = open( incpathsfile, "r" )
    for line in file.readlines():
        line = line.strip( " \n\r" )
        additionalIncPaths += line.split(";")

    file.close()

    additionalIncPaths = filter(lambda x: x.strip(" ") != '',additionalIncPaths)


projName = ""
if exact:
    if options.has_key('--name'):
        infoMessage( "WARNING: Option '--name' is ignored when '--exact' is used", 0, msgSender )
else:
    if not options.has_key('--name'):
        userErrorExit( "'--name' option is mandatory when '--exact' is omitted.", msgSender )
    projName = options['--name'][0]





# strip vcproj extension if the user included it.
if projName[ -7: ].lower() == '.vcproj':
    projName = projName[0:-7]

#
# Load build configuration.
#

bc = BCFile( bcFile )

buildParams = bc.getBuildParams()



#
# preload dependencies for all modules that will be built
#
#session.preloadDependencies( preloadModules )

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
            # Only include private headers for projects containing the specified module
            #incPaths.append( os.path.join(rawMod.getRootPath(), rawMod.getPrivHeaderDir()) )
            modTags.append( 'COMPILING_MOD_' + string.upper( rawMod.getName() ) )

incPaths += additionalIncPaths


#
# Create all component objects and collect all modules names involved.
#

preloadModules = list()
components = list()
for compFile in compFiles:
    comp = COMPFile( compFile )
    components.append( comp )


#    for library, modules in comp.libraries.iteritems():
#
#        preloadModules.extend( assureList(modules) )


# If the user requested an exact replication of the components we create one vcproj
# per component library, otherwise we create one large library of all code modules
# specified in all components.


vcprojList = list() # list of dict['PROJNAME':string, 'LIBNAME':string, 'MODULELIST':listof( see doc of make_libvcproj7 ) ]


for comp in components:
    for library, modules in comp.libraries.iteritems():

        #codeModules = listof dictionaries: { MODNAME: string, SOURCES: list(paths), PRIVHDRS: list(paths), PUBHDRS: list(paths) }
        codeModules = list()

        for mod in modules:

            srcFiles = list()
            privHdrs = list()
            pubHdrs  = list()

            rawMod = CTXRawCodeModule( mod )

            srcNames = rawMod.getSourceFilenames()
            for srcName in srcNames:
                srcFiles.append( os.path.join( rawMod.getSourceDir(), srcName ) )

            privHdrNames = rawMod.getPrivHeaderFilenames()
            for privHdrName in privHdrNames:
                privHdrs.append( os.path.join( rawMod.getPrivHeaderDir(), privHdrName ) )

            pubHdrNames = rawMod.getPubHeaderFilenames()
            for pubHdrName in pubHdrNames:
                pubHdrs.append( os.path.join( rawMod.getPubHeaderDir(), pubHdrName ) )


            modDict = { 'MODNAME': mod, 'SOURCES': srcFiles, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir() }
            codeModules.append( modDict )


        # Assemble list of sourcepaths for the modules' sourcefiles.
        srcFiles = list()
        for mod in modules:
            rawMod = CTXRawCodeModule( mod )
            srcNames = rawMod.getSourceFilenames()
            for srcName in srcNames:
                srcFiles.append( os.path.join( rawMod.getSourceDir(), srcName ) )


        if exact:
            vcprojList.append( { 'PROJNAME': library, 'LIBNAME': library, 'MODULELIST': codeModules } )
        else:
            if len(vcprojList) == 0:
                vcprojList.append( {'PROJNAME': projName, 'LIBNAME': projName, 'MODULELIST': list() } )

            vcprojList[0]['MODULELIST'].extend( codeModules )

if not os.path.exists( outputPath ):
    os.makedirs( outputPath )

guidDict = dict()
for proj in vcprojList:
    guidDict[proj['PROJNAME']] = ctx_msvc.make_libvcproj8( proj['PROJNAME'],
                                                                                  buildParams.cflags,
                                                                                  buildParams.prepDefines + modTags,
                                                                                  proj['MODULELIST'],
                                                                                  proj['LIBNAME'] + '.lib',
                                                                                  debugmode, incPaths, outputPath,
                                                                                  platform,
                                                                                  proj['PROJNAME'])

if exevcproj:
    attrs = list()
    attrs.append(dict({"DEBUG":debugmode, "TOOL":"VCCLCompilerTool","KEY":"AdditionalIncludeDirectories","VALUE":";".join(incPaths)}))
    ctx_msvc.update_vcproj8(exevcproj['FILENAME'],attrs)

if slnName != None:

    slnProjects = list()
    for proj in vcprojList:
        slnProjects.append( { 'PROJNAME': proj['PROJNAME'], 'PROJGUID': guidDict[proj['PROJNAME']], 'DEBUG': debugmode } )

    ctx_msvc.make_solution8( slnName, outputPath, slnProjects, exevcproj, platform )
