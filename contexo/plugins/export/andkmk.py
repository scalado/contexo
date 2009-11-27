#! /usr/bin/env python
import sys
from argparse import ArgumentParser
import contexo.ctx_export as ctx_export
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import os
import re
import contexo.ctx_bc
import contexo.ctx_cmod


msgSender = 'Android MK Export'

def computeRelPath(fromPath, toPath):
    fromComps = re.split("[/]", fromPath)
    toComps = re.split("[/]", toPath)
    i = 0
    n = min(len(fromComps), len(toComps))
    while i < n:
        if fromComps[i] != toComps[i]:
            break
        i += 1
    if i == 0:
        return None
    m = len(fromComps) - (i)
    # Step up m tims (with "..") then down into the rest of toComps.
    return "/".join(m * [".."]) + "/" + "/".join(toComps[i:])


    
def moduleMk(module, build_params, modules, incPaths, depMgr, lclDstDir, localPath=True):
    """Returns a string containing Android.mk data for module.
    Several calls to this function can be combined into the same
    makefile.
    """
    
    def _incPath(path):
        return "$(LOCAL_PATH)/" + computeRelPath(lclDstDir, path.replace("\\", "/"))
    
    outData = []
    #
    # The common stuff.
    # Local path.
    # Clear variables.
    # The name of the module.
    #
    if localPath:
        outData.append("LOCAL_PATH := $(call my-dir)\n\n")
    outData.append("# Locale module [%s]\n" % (module['PROJNAME']))
    outData.append("include $(CLEAR_VARS)\n\n")
    outData.append("LOCAL_MODULE := %s\n\n" % (module['PROJNAME']))

    #
    # Local flags
    #
    outData.append("LOCAL_CFLAGS := ")
    localFlags = []
    prepDefPrefix = "-D"
    prepDefSuffix = ""
    for lib_mod in module['MODULELIST']:
        localFlags.append(prepDefPrefix + "COMPILING_MOD_" + lib_mod["MODNAME"].upper() + prepDefSuffix)
    for prepDef in build_params.prepDefines:
        localFlags.append(prepDefPrefix + prepDef + prepDefSuffix)
    outData.append((" \\\n" + 17 * " ").join(localFlags))
    outData.append("\n\n")

    #
    # Local include paths
    #
    lclIncPaths = []
    if incPaths <> None:
        for lib_mod in module['MODULELIST']:
            lclIncPaths.append(_incPath(os.path.join(lib_mod['ROOT'], "inc")))
        for incPath in incPaths:
            lclIncPaths.append(_incPath(incPath))
    if depMgr <> None:
        addedPaths = {} # Not to add the same path several times
        for lib_mod in module['MODULELIST']:
            for path in depMgr.getModuleIncludePaths(lib_mod['MODNAME']):
                lclPath = _incPath(path)
                if not addedPaths.has_key(lclPath):
                    lclIncPaths.append(lclPath)
                    addedPaths[lclPath] = True
    outData.append("LOCAL_C_INCLUDES := ")
    outData.append((" \\\n" + 17 * " ").join(lclIncPaths))
    
    #
    # Sources
    #
    sources = []
    for lib_mod in module['MODULELIST']:
        sources.extend(lib_mod["SOURCES"])
    outData.append("\n\n")
    outData.append("# Note that all sources are relative to LOCAL_PATH.\n")
    outData.append("LOCAL_SRC_FILES := \\\n")
    for source in sources:
        srcPath, srcName = os.path.split(source)
        srcPath = srcPath.replace("\\", "/")
        srcRelPath = computeRelPath(lclDstDir, srcPath)
        outData.append("    %s \\\n" % (srcRelPath + "/" + srcName))
    outData.append("\n")
    
    #
    # Build static library
    #
    outData.append("include $(BUILD_STATIC_LIBRARY)\n\n")
    
    return "".join(outData)

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list ):

    code_module_map = list()

    for mod in ctx_module_list:
        srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()

        rawMod = mod #ctx_cmod.CTXRawCodeModule( mod )

        srcNames = rawMod.getSourceFilenames()
        for srcName in srcNames:
            srcFiles.append( os.path.join( rawMod.getSourceDir(), srcName ) )

        privHdrNames = rawMod.getPrivHeaderFilenames()
        for privHdrName in privHdrNames:
            privHdrs.append( os.path.join( rawMod.getPrivHeaderDir(), privHdrName ) )

        pubHdrNames = rawMod.getPubHeaderFilenames()
        for pubHdrName in pubHdrNames:
            pubHdrs.append( os.path.join( rawMod.getPubHeaderDir(), pubHdrName ) )


        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcFiles, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(), 'ROOT' : rawMod.getRootPath() }
        code_module_map.append( modDict )

    return code_module_map

#------------------------------------------------------------------------------
def allComponentModules( component_list ):

    modules = list()
    for comp in component_list:
        for lib, libmods in comp.libraries.iteritems():
            modules.extend( libmods )

    return modules

#------------------------------------------------------------------------------
def cmd_parse( args ):
    import string
    infoMessage("Receiving export data from Contexo...", 1)
    package = ctx_export.CTXExportData()
    package.receive() # Reads pickled export data from stdin

    infoMessage("Received export data:", 4)
    for item in package.export_data.keys():
        infoMessage("%s: %s"%(item, str(package.export_data[item])), 4)

    # Retrieve build config from session
    bc_file =  package.export_data['SESSION'].getBCFile()
    build_params = bc_file.getBuildParams()

    #TODO? debugmode = bool( not args.release )

    #
    # Add module paths/repositories as include directories
    #

    modTags     = list()
    incPaths    = list()
    depRoots    = package.export_data['PATHS']['MODULES']
    depMgr      = package.export_data['DEPMGR']
    for depRoot in depRoots:
        incPathCandidates = os.listdir( depRoot )
        for cand in incPathCandidates:
            path = os.path.join(depRoot, cand)
            if contexo.ctx_cmod.isContexoCodeModule( path ):
                rawMod = contexo.ctx_cmod.CTXRawCodeModule(path)
                incPaths.append( path )

                # Only include private headers for projects containing the specified module
                #incPaths.append( os.path.join(rawMod.getRootPath(), rawMod.getPrivHeaderDir()) )

                modTags.append( 'COMPILING_MOD_' + string.upper( rawMod.getName() ) )

    #
    # Collect additional include paths
    #
    # user_includepaths = list()
    # if args.additional_includes != None:
        # filename = args.additional_includes
        # if os.path.isdir( filename ):
            # userErrorExit("The 'additional includes' option should be used with a file that lists the additional include paths. %s is a directory"%filename)
        # elif not os.path.isfile( filename ):
            # userErrorExit("Cannot find option file '%s'"%filename)
        # file = open( filename, "r" )
        # for line in file.readlines():
            # line = line.strip()
            # user_includepaths += line.split(";")
        # file.close()
        # user_includepaths = filter(lambda x: x.strip(" ") != '',user_includepaths)
        # incPaths += user_includepaths

    #
    # Determine if we're exporting components or modules, and do some related
    # sanity checks
    #

    comp_export = bool( package.export_data['COMPONENTS'] != None )

    if comp_export:
    #Exporting components
        pass
    else:
    # Exporting modules
        userErrorExit( "No components specified. Currently no support for module-export.")

    # Regardless if we export components or modules, all modules are located in export_data['MODULES']
    module_map = create_module_mapping_from_module_list( package.export_data['MODULES'].values() )

    androidJniModList = []
    if comp_export:
        for comp in package.export_data['COMPONENTS']:
            for library, modules in comp.libraries.iteritems():
                lib_modules = [ mod for mod in module_map if mod['MODNAME'] in modules  ]
                androidJniModList.append( { 'PROJNAME': library, 'LIBNAME': library, 'MODULELIST': lib_modules } )

    #
    # Generate the makefile
    #

    if args.dest == None:
        userErrorExit("--dest not specified.")
    # if args.dest == None and args.output == None):
        # userErrorExit("Must specify either --output, --dest or both.")

    if args.dest <> None:
        dstDir = args.dest
    else:
        dstDir = args.output

    if args.output <> None:
        outDir = args.output
    else:
        outDir = args.dest

    if not os.path.isabs(dstDir):
        dstDir = os.path.join(os.getcwd(), dstDir)
    if not os.path.isabs(outDir):
        outDir = os.path.join(os.getcwd(), outDir)

    infoMessage("Output: %s" % (outDir), 2)
    infoMessage("Dest: %s" % (dstDir), 2)

    if not os.path.exists( outDir ):
        os.makedirs( outDir )

    # There were some problems when one makefile per comp was created, (with the android build).
    # I guess it should be possible to do it that way.
    # However this way has proved to work.
    # So, we set allInOne to True.
    allInOne = True
    mkFileVerbosity = 1
    if not allInOne:
        for jniMod in androidJniModList:
            lclDstDir = os.path.join(dstDir, jniMod['PROJNAME']).replace("\\", "/")
            lclOutDir = os.path.join(outDir, jniMod['PROJNAME']).replace("\\", "/")
            if not os.path.exists(lclOutDir):
                os.makedirs(lclOutDir)
            mkFileName = os.path.join(lclOutDir, "Android.mk")
            file = open(mkFileName, "wt")
            file.write(moduleMk(jniMod, build_params, androidJniModList, None, depMgr, lclDstDir))
            file.close()
            infoMessage("Created %s" % (mkFileName), mkFileVerbosity)
    else:
        lclDstDir = dstDir.replace("\\", "/")
        lclOutDir = outDir.replace("\\", "/")
        if not os.path.exists(lclOutDir):
            os.makedirs(lclOutDir)
        mkFileName = os.path.join(lclOutDir, "Android.mk")
        file = open(mkFileName, "wt")
        i = 0
        for jniMod in androidJniModList:
            file.write(moduleMk(jniMod, build_params, androidJniModList, None, depMgr, lclDstDir, i == 0))
            file.write("#" * 60 + "\n")
            i += 1
        file.close()
        infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if args.app_mk:
        appMkFileName = os.path.join(outDir, "Application.mk")
        file = open(appMkFileName, "wt")
        modNames = [lib_mod['PROJNAME'] for lib_mod in androidJniModList]
        file.write("APP_PROJECT_PATH := $(call my-dir)/project\n")
        file.write("APP_MODULES      := %s\n" % (" ".join(modNames)))
        file.close()
    #
    # The End
    #
    infoMessage("Export done.", 1)


##### ENTRY POINT #############################################################

# Create Parser
parser = ArgumentParser( description="""Android NDK MK export -
 plugin to Contexo Build System (c) 2006-2009 Scalado AB
 Note that Contexo has a default bconf which likely is not
 compatible with Android. Make sure to specify a bc-file in the
 export.
 """,
 version="0.1")

parser.set_defaults(func=cmd_parse)

# Will we want this feature?
# parser.add_argument('-mc', '--mirror-components', action='store_true',
 # help="""If specified, the export will mirror the exact distribution of
 # libraries from any included components, resulting in one VS project for each
 # library within the components. The name of each library will be used as both
 # project name and output library name. If this option is omitted, one VS project
 # will be created including all sourcefiles from all components. In this case the
 # --project-name option sets the name of the project.""")

# Do we need this?
# parser.add_argument('-r', '--release', action='store_true',
 # help="""If specified, the resulting VS projects will be set to release mode.
 # Otherwise debug mode is used. Note that this option does not affect any
 # potential debugging parameters introduced by the build configuration specified
 # with the -b or --bconf option""")

# Do we need this?
# parser.add_argument('-ai', '--additional-includes', default=None,
 # help="""Path to a file with include paths to append to the include directories
 # of all makefiles generated. The paths in the file can be separated by line
 # or by semicolon.""")

# parser.add_argument('-pl', '--platform', default='Win32',
 # help="""If specified, the resulting VS projects will use
 # the specified platform. Default is "Win32". Note that this option does not affect
 # any settings introduced by the build configuration specified with the -b or
 # --bconf option.""")

parser.add_argument('-o', '--output', #default=os.getcwd(),
 help="""The output directory for the export. Use this option e.g not to
 to overwrite an existing makefile.""")

parser.add_argument('-d', '--dest', default=None,
 help="""Location of makefile(s) to create. This should be a sub directory of <android ndk>/apps/<app name>.
 The sources and includes pointed out by the makefile will be relative to this location.
 If both this option and --output are specified the makefile will be created as specified by the
 output option, but it's paths will still be relative to the destination.""")

parser.add_argument('--app-mk', action='store_true',
 help="""If specified, a basic Application.mk will be created.
 Note that this makefile most likely will differ from the desired
 Application.mk, since this must contain more modules than the
 static library modules created by this script.""")
args = parser.parse_args()
args.func(args)
