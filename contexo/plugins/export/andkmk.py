#! /usr/bin/env python
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import contexo.ctx_export as ctx_export
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import os
import re
import contexo.ctx_bc
import contexo.ctx_cmod


msgSender = 'Android MK Export'


def computeLinkOrder(modules, depMgr):
    """Returns a list containing modules sorted by contexo dependencies.
    Note that this is not a very good way to determine link order, and
    it will probably be faulty.
    """
    ctxMod2Lib = {}
    for module in modules:
        for ctxMod in module['MODULELIST']:
            ctxMod2Lib[ctxMod["MODNAME"]] = module['LIBNAME']
    depMap = {}
    for module in modules:
        depMap[module['LIBNAME']] = []
        addedPaths = {} # Not to add the same path several times
        for ctxMod in module['MODULELIST']:
            for path in depMgr.getModuleIncludePaths(ctxMod['MODNAME']):
                if True:#contexo.ctx_cmod.isContexoCodeModule(path):
                    modName = os.path.split(path)[1]
                    if not addedPaths.has_key(modName) and ctxMod2Lib.has_key(modName) and not (ctxMod2Lib[modName] == module['LIBNAME']):
                        addedPaths[modName] = True
                        if not ctxMod2Lib[modName] in depMap[module['LIBNAME']]:
                            depMap[module['LIBNAME']].append(ctxMod2Lib[modName])

    def cmpByDeps(amod1, amod2):
        mod1depsOn2 = amod2['LIBNAME'] in depMap[amod1['LIBNAME']]
        mod2depsOn1 = amod1['LIBNAME'] in depMap[amod2['LIBNAME']]
        if mod1depsOn2 and mod2depsOn1:
            return 0
        elif mod1depsOn2 :
            return 1
        else:
            return -1
    sortedMods = [mod for mod in modules]
    sortedMods.sort(cmp=cmpByDeps)
    sortedMods.reverse()
    return sortedMods

def computeRelPath(fromPath, toPath):
    """Returns a relative path starting from fromPath pointing
    at toPath.
    """
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
    
def moduleMk(module, build_params, modules, incPaths, depMgr, lclDstDir, localPath=True, ldlibs=None, staticLibs=None):
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
    outData.append("# Locale module [%s]\n" % (module['LIBNAME']))
    outData.append("include $(CLEAR_VARS)\n\n")
    outData.append("LOCAL_MODULE := %s\n\n" % (module['LIBNAME']))

    #
    # Local flags
    #
    outData.append("LOCAL_CFLAGS := ")
    localFlags = []
    prepDefPrefix = "-D"
    prepDefSuffix = ""
    for ctxMod in module['MODULELIST']:
        localFlags.append(prepDefPrefix + "COMPILING_MOD_" + ctxMod["MODNAME"].upper() + prepDefSuffix)
    for prepDef in build_params.prepDefines:
        localFlags.append(prepDefPrefix + prepDef + prepDefSuffix)
    outData.append((" \\\n" + 17 * " ").join(localFlags))
    outData.append("\n\n")

    #
    # Local include paths
    #
    lclIncPaths = []
    if incPaths <> None:
        for ctxMod in module['MODULELIST']:
            lclIncPaths.append(_incPath(os.path.join(ctxMod['ROOT'], "inc")))
        for incPath in incPaths:
            lclIncPaths.append(_incPath(incPath))
    if depMgr <> None:
        addedPaths = {} # Not to add the same path several times
        for ctxMod in module['MODULELIST']:
            for path in depMgr.getModuleIncludePaths(ctxMod['MODNAME']):
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
    for ctxMod in module['MODULELIST']:
        sources.extend(ctxMod["SOURCES"])
    outData.append("\n\n")
    outData.append("# Note that all sources are relative to LOCAL_PATH.\n")
    outData.append("LOCAL_SRC_FILES := \\\n")
    for source in sources:
        srcPath, srcName = os.path.split(source)
        srcPath = srcPath.replace("\\", "/")
        srcRelPath = computeRelPath(lclDstDir, srcPath)
        outData.append("    %s \\\n" % (srcRelPath + "/" + srcName))
    outData.append("\n")

    if module.has_key('SHAREDOBJECT') and module['SHAREDOBJECT']:
        if staticLibs == None:
            depMods = computeLinkOrder(modules, depMgr)
            depMods = [depMod["LIBNAME"] for depMod in depMods]
        else:
            depMods = staticLibs
        if len(depMods) > 0:
            outData.append("LOCAL_STATIC_LIBRARIES := %s\n\n" % (" ".join(depMods)))
        if ldlibs <> None:
            ldlibs = [("-l" + ldlib) for ldlib in ldlibs]
            if len(ldlibs) > 0:
                outData.append("LOCAL_LDLIBS := %s\n\n" % (" ".join(ldlibs)))

    #
    # Type of library
    #
    if module.has_key('SHAREDOBJECT') and module['SHAREDOBJECT']:
        outData.append("include $(BUILD_SHARED_LIBRARY)\n\n")
    else:
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

    jniLibs = []
    if comp_export:
        for comp in package.export_data['COMPONENTS']:
            for library, modules in comp.libraries.iteritems():
                ctxMods = [ mod for mod in module_map if mod['MODNAME'] in modules  ]
                jniLibs.append( { 'PROJNAME': library, 'LIBNAME': library, 'MODULELIST': ctxMods } )

    if args.ndk == None:
        userErrorExit("--ndk not specified.")
    if not os.path.isdir(args.ndk):
        userErrorExit("'%s' specified by --ndk does not exist or is not a directory." % (args.ndk))
    if args.app == None:
        userErrorExit("--app not specified.")

    # Set up paths.
    dstDir = os.path.join(args.ndk, "apps", args.app)
    if args.output <> None:
        outDir = os.path.join(args.output, args.app)
        if not os.path.isabs(outDir):
            outDir = os.path.join(os.getcwd(), outDir)
    else:
        outDir = dstDir
    projectPath = "project"
    libPath = os.path.join(projectPath, args.mk_path)

    if args.ldlibs <> None and args.shared == None:
        warningMessage("Ignoring option --ldlibs since --shared was not specified.")
    ldlibs = args.ldlibs

    # Determine if anything is to be omitted.
    omits = {"static" : False, "shared" : False, "top" : False, "app" : False}
    if args.no <> None:
        argOmits = [no.lower() for no in args.no]
        for omit in argOmits:
            if not omits.has_key(omit):
                userErrorExit("'%s' is not a valid argument to --no." % (omit))
            else:
                omits[omit] = True

    #
    # Generate the makefile
    #

    if not os.path.exists( outDir ):
        os.makedirs( outDir )

    # There were some problems when one makefile per comp was created, (with the android build).
    # I guess it should be possible to do it that way.
    # However this way has proved to work.
    # So, we set allInOne to True.
    allInOne = True

    sharedInSeparateMk = True
    sharedObjLib = None
    if args.shared <> None:
        for jniMod in jniLibs:
            if jniMod['LIBNAME'] == args.shared:
                # Move it to last in list.
                sharedObjLib = jniMod
                del jniLibs[jniLibs.index(sharedObjLib)]
                if not sharedInSeparateMk:
                    jniLibs.append(sharedObjLib)
                sharedObjLib['SHAREDOBJECT'] = True
                break
        else:
            userErrorExit("Library specifed by --shared ('%s') not found." % (args.shared))

    staticRelPath = "static"
    sharedRelPath = "shared"

    mkFileVerbosity = 1
    if not omits["static"]:
        if not allInOne:
            for jniMod in jniLibs:
                lclDstDir = os.path.join(dstDir, libPath, jniMod['LIBNAME']).replace("\\", "/")
                lclOutDir = os.path.join(outDir, libPath, jniMod['LIBNAME']).replace("\\", "/")
                if not os.path.exists(lclOutDir):
                    os.makedirs(lclOutDir)
                mkFileName = os.path.join(lclOutDir, "Android.mk")
                file = open(mkFileName, "wt")
                file.write(moduleMk(jniMod, build_params, jniLibs, None, depMgr, lclDstDir))
                file.close()
                infoMessage("Created %s" % (mkFileName), mkFileVerbosity)
        else:
            lclDstDir = os.path.join(dstDir, libPath, staticRelPath).replace("\\", "/")
            lclOutDir = os.path.join(outDir, libPath, staticRelPath).replace("\\", "/")
            if not os.path.exists(lclOutDir):
                os.makedirs(lclOutDir)
            mkFileName = os.path.join(lclOutDir, "Android.mk")
            file = open(mkFileName, "wt")
            i = 0
            for jniMod in jniLibs:
                file.write(moduleMk(jniMod, build_params, jniLibs, None, depMgr, lclDstDir, i == 0))
                file.write("#" * 60 + "\n")
                i += 1
            file.close()
            infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if sharedObjLib <> None and not omits["shared"]:
        lclDstDir = os.path.join(dstDir, libPath, sharedRelPath).replace("\\", "/")
        lclOutDir = os.path.join(outDir, libPath, sharedRelPath).replace("\\", "/")
        if not os.path.exists(lclOutDir):
            os.makedirs(lclOutDir)
        mkFileName = os.path.join(lclOutDir, "Android.mk")
        file = open(mkFileName, "wt")
        file.write(moduleMk(sharedObjLib, build_params, jniLibs, None, depMgr, lclDstDir, localPath=True, ldlibs=ldlibs, staticLibs=args.static_libs))
        file.close()
        if args.static_libs == None:
            warningMessage("Computed link order is very likely not accurate.")
            warningMessage("See %s." % (mkFileName))
        infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if not omits["top"]:
        topMkFileName = os.path.join(outDir, libPath, "Android.mk")
        file = open(topMkFileName, "wt")
        file.write("include $(call all-subdir-makefiles)")
        file.close()

    if not omits["app"]:
        appMkFileName = os.path.join(outDir, "Application.mk")
        file = open(appMkFileName, "wt")
        libNames = [jniLib['LIBNAME'] for jniLib in jniLibs]
        if sharedObjLib <> None:
            libNames.append(sharedObjLib['LIBNAME'])
        file.write("APP_PROJECT_PATH := $(call my-dir)/project\n")
        file.write("APP_MODULES      := %s\n" % (" ".join(libNames)))
        if bc_file.dbgmode:
            file.write("APP_OPTIM      := debug\n")
        file.close()
    #
    # The End
    #
    infoMessage("Export done.", 1)


##### ENTRY POINT #############################################################

# Create Parser
parser = ArgumentParser( description="""Android NDK MK export - plugin to Contexo Build System (c) 2006-2009 Scalado AB.
 
Note that Contexo has a default bconf which likely is not
compatible with Android. Make sure to specify a bc-file in the
export.

This script can produce the following output:
  <NDK root>/apps/<APP>/Application.mk
  <NDK root>/apps/<APP>/project/<MK path>/Android.mk
  <NDK root>/apps/<APP>/project/<MK path>/static/Android.mk
  <NDK root>/apps/<APP>/project/<MK path>/shared/Android.mk

<NDK root>, <APP> and <MK path> are all specified by command line options.

The @ can be used to put arguments in a file.

Example usage:
ctx export @allcomps.txt --bconf android.bc --env android.env --view . | andkmk.py @args.txt --app-mk --top-mk -o mk
Content of args.txt = [
--ndk C:/dev/android/android-ndk-1.6_r1
--app midemo
--shared albv_android
--ldlibs GLESv1_CM dl log
--static-libs deplib1 deplib2 deplib3 deplib4
]
""",
 version="0.1", formatter_class=RawDescriptionHelpFormatter, fromfile_prefix_chars='@')

parser.set_defaults(func=cmd_parse)

parser.add_argument('-n', '--ndk',
 help="""Specifies the Android NDK root.""")

parser.add_argument('-a', '--app',
 help="""Specifies the name of the application.""")

parser.add_argument('-mp', '--mk-path', default="jni",
 help="""Specifies where the makefiles will be created. This
 is relative to <NDK root>/apps/<APP>/project. All created makefiles
 will be put in this directory or below it, except the
 Application.mk.""")

parser.add_argument('-o', '--output',
 help="""The output directory for the export. Use this option e.g not to
 to overwrite existing makefiles.
 Note that this option does not affect the source and include
 paths in the created makefiles.""")

parser.add_argument('-so', '--shared', default=None,
 help="""Specifies one library that will be built to a shared object,
 depending on all the others. This will be put in a separate makefile.""")

parser.add_argument('--static-libs', default=None, nargs='+',
 help="""Specifies which static libraries the shared object depends on.
 They must be specified in the order that they depend on each other, i.e. the dependant
 comes before dependee.""")

parser.add_argument('--ldlibs', default=None, nargs='+',
 help="""Specifies additional libraries the shared object depends on.
 Par example:
 --ldlibs GLESv1_CM dl log.""")

parser.add_argument('--no', default=None, nargs='+',
 help="""Omits creating the specified makefiles, which must be one or more of
 the following:
 static, shared, top and/or app.
 """)



args = parser.parse_args()
args.func(args)
