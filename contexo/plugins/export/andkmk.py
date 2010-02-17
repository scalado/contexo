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

absPathSub = ["", ""]
relPathSub = ["", ""]

def absPath(path):
    newPath = path
    for i in range(len(absPathSub) / 2):
        newPath = newPath.replace(absPathSub[2 * i], absPathSub[2 * i + 1])
    return newPath
def relPath(path):
    newPath = path
    for i in range(len(relPathSub) / 2):
        newPath = newPath.replace(relPathSub[2 * i], relPathSub[2 * i + 1])
    return newPath
def prepPath(path):
    if os.path.isabs(path):
        return absPath(path)
    else:
        return relPath(path)

def lowestCommonPath(paths):
    """Returns the shortest absolute path common to all the paths in a list.
    """
    pos = 0
    reg = re.compile("[/\\\\]")
    paths = [reg.split(absPath(path)) for path in paths]
    newPathComps = []
    size = len(paths[0])
    for path in paths:
		size = min(size, len(path))
    while pos < size:
        cmp = paths[0][pos]
        doBreak = False
        for path in paths:
            if pos >= len(path) or path[pos] != cmp:
                doBreak = True
                break
        if doBreak:
            break
        newPathComps.append(cmp)
        pos += 1
    if len(newPathComps) > 0:
        return "/".join(newPathComps)
    else:
        return "/"

def computeRelPath(fromPath, toPath):
    """Returns a relative path starting from fromPath pointing
    at toPath.
    """
    fromComps = re.split("[/\\\\]", fromPath)
    toComps = re.split("[/\\\\]", toPath)
    i = 0
    n = min(len(fromComps), len(toComps))
    while i < n:
        if fromComps[i] != toComps[i]:
            break
        i += 1
    m = len(fromComps) - (i)
    newComps = m * [".."]
    newComps.extend(toComps[i:])
    return "/".join(newComps)

def moduleMk(module, build_params, modules, incPaths, depMgr, lclDstDir, args, useMkDir=True, localPath=None, useObjOutPath=False):
    """Returns a string containing Android.mk data for module.
    Several calls to this function can be combined into the same
    makefile.
    """
    ldlibs = args.ldlibs
    staticLibs = args.static_libs
    
    outData = []
    #
    # The common stuff.
    # Local path.
    # Clear variables.
    # The name of the module.
    #
    lclPath = lclDstDir
    if useObjOutPath:
        lclPath = absPath(os.path.join(args.ndk, "out", "apps", args.app, "objs", module['LIBNAME']).replace("\\", "/"))
        outData.append("# Note that this is the location where the build system wants to place objects.\n")
        outData.append("# By being relative to this we ensure objects are put next to sources (which seems to be as good as it gets).\n")
        outData.append("LOCAL_PATH := %s\n\n" % (lclPath))
    elif localPath <> None:
        lclPath = localPath
        outData.append("LOCAL_PATH := %s\n\n" % (lclPath))
    elif useMkDir:
        outData.append("LOCAL_PATH := $(call my-dir)\n\n")
    outData.append("# Locale module [%s]\n" % (module['LIBNAME']))
    outData.append("include $(CLEAR_VARS)\n\n")
    outData.append("LOCAL_MODULE := %s\n\n" % (module['LIBNAME']))

    def _incPath(path):
        #return "$(LOCAL_PATH)/" + relPath(computeRelPath(lclDstDir, path.replace("\\", "/")))
        return "$(LOCAL_PATH)/" + relPath(computeRelPath(lclPath, absPath(path.replace("\\", "/"))))
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
    outData.append((" \\\n" + 16 * " ").join(localFlags))
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
                _lclPath = _incPath(path)
                if not addedPaths.has_key(_lclPath):
                    lclIncPaths.append(_lclPath)
                    addedPaths[_lclPath] = True
    outData.append("LOCAL_C_INCLUDES := ")
    lclIncPaths.sort()
    outData.append((" \\\n" + 20 * " ").join(lclIncPaths))
    
    #
    # Sources
    #
    sources = []
    for ctxMod in module['MODULELIST']:
        sources.extend(ctxMod["SOURCES"])
    sources = set(sources)
    _sources = []
    for source in sources:
        srcPath, srcName = os.path.split(source)
        srcPath = absPath(srcPath)#relPath(srcPath)
        srcRelPath = computeRelPath(lclPath, srcPath)
        _sources.append(srcRelPath + "/" + srcName)
    _sources.sort()
    outData.append("\n\n")
    outData.append("# Note that all sources are relative to LOCAL_PATH.\n")
    outData.append("LOCAL_SRC_FILES := ")
    outData.append((" \\\n" + 19 * " ").join(_sources))
    outData.append("\n\n")

    if module.has_key('SHAREDOBJECT') and module['SHAREDOBJECT']:
        if staticLibs == None:
            depMods = computeLinkOrder(modules, depMgr)
            depMods = [depMod["LIBNAME"] for depMod in depMods]
        else:
            depMods = staticLibs
        if len(depMods) > 0:
            outData.append("LOCAL_STATIC_LIBRARIES := %s\n\n" % (" ".join(depMods)))
        if ldlibs <> None and len(ldlibs) > 0:
            ldlibs = [("-l" + ldlib) for ldlib in ldlibs]
            if len(ldlibs) > 0:
                outData.append("LOCAL_LDLIBS := %s\n\n" % (" ".join(ldlibs)))

    if args.arm_mode <> None:
        outData.append("LOCAL_ARM_MODE := %s\n\n" % (args.arm_mode))
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

    allSources = [] # Used to find a common path.
    allCtxMods = {}
    staticLibs = []
    if comp_export:
        for comp in package.export_data['COMPONENTS']:
            for library, modules in comp.libraries.iteritems():
                ctxMods = [ mod for mod in module_map if mod['MODNAME'] in modules  ]
                staticLibs.append( { 'PROJNAME': library, 'LIBNAME': library, 'MODULELIST': ctxMods } )
                for ctxMod in ctxMods:
                    allSources.extend(ctxMod["SOURCES"])
                    if not allCtxMods.has_key(ctxMod['MODNAME']):
                        allCtxMods[ctxMod['MODNAME']] = []
                    allCtxMods[ctxMod['MODNAME']].append(comp)
        for ctxModName, comps in allCtxMods.iteritems():
            if len(comps) > 1:
                warningMessage("Contexo module, '%s' specified in multiple .comp-files:" % (ctxModName))
                for comp in comps:
                    warningMessage("      %s." % (comp.path))

    if args.ndk == None:
        userErrorExit("--ndk not specified.")
    if not os.path.isdir(args.ndk):
        userErrorExit("'%s' specified by --ndk does not exist or is not a directory." % (args.ndk))
    if args.app == None:
        userErrorExit("--app not specified.")
    if args.arm_mode <> None and not args.arm_mode in ["arm", "thumb"]:
        userErrorExit("Illegal arm mode '%s', specified with --arm-mode." % (args.arm_mode))

    if args.abs_sub <> None:
        if (len(args.abs_sub) % 2 != 0): userErrorExit("--abs-sub: number of arguments must be a 2-multiple.")
        global absPathSub
        absPathSub = args.abs_sub
    if args.rel_sub <> None:
        if (len(args.rel_sub) % 2 != 0): userErrorExit("--rel-sub: number of arguments must be a 2-multiple.")
        global relPathSub
        relPathSub = args.rel_sub

    # This will be used as LOCAL_PATH for all (android) modules.
    # By using this path we ensure that no paths contain any "..".
    # (They would mess up the android build system.)
    localPath = lowestCommonPath(allSources)

    # Returns a path to be used in a makefile.
    def getDstPath(*pathComps):
        if args.project <> None:
            if not os.path.isabs(args.project):
                return os.path.join(os.getcwd(), args.project, *pathComps).replace("\\", "/")
            else:
                return os.path.join(args.project, *pathComps).replace("\\", "/")
        else:
            return os.path.join(args.ndk, "apps", args.app, "project", *pathComps).replace("\\", "/")
			
    # Returns a path that locates where to actually put a file.
    def getOutPath(*pathComps):
        if args.output <> None:
            if not os.path.isabs(args.output):
                return os.path.join(os.getcwd(), args.output, "apps", args.app, "project", *pathComps).replace("\\", "/")
            else:
                return os.path.join(args.output, "apps", args.app, "project", *pathComps).replace("\\", "/")
        else:
            return getDstPath(*pathComps)

    # Determine location of the Application.mk.
    if args.output == None:
        applicationDir = os.path.join(args.ndk, "apps", args.app)
    else:
        if not os.path.isabs(args.output):
            applicationDir = os.path.join(os.getcwd(), args.output, "apps", args.app).replace("\\", "/")
        else:
            applicationDir = os.path.join(args.output, "apps", args.app).replace("\\", "/")
    
    libPath = args.mk_path

    # Determine if anything is to be omitted.
    omits = {"static" : False, "shared" : False, "top" : False, "app" : False}
    if args.no <> None:
        argOmits = [no.lower() for no in args.no]
        for omit in argOmits:
            if not omits.has_key(omit):
                userErrorExit("'%s' is not a valid argument to --no." % (omit))
            else:
                omits[omit] = True

    # We generate one makefile per library.
    # This variable could be possible to change via commandline.
    # However, it's more practical to subdivide into several
    # makefiles. If one of them is changed all others needn't be rebuilt.
    allInOne = False

    sharedObjLib = None
    if args.shared <> None:
        if len(args.shared) == 0:
            userErrorExit("No libraries specifed by --shared.")
        partsOfShared = []
        for name in args.shared:
            for libMod in staticLibs:
                if libMod["LIBNAME"] == name:
                    break
            else:
                userErrorExit("Contexo library '%s', specified by --shared not found in export." % (name))
            del staticLibs[staticLibs.index(libMod)]
            partsOfShared.append(libMod)
        name = args.shared[0] if args.shared_name == None else args.shared_name
        sharedObjLib = { 'PROJNAME': name, 'LIBNAME': name, 'MODULELIST': [], 'SHAREDOBJECT' : True }
        for part in partsOfShared:
            sharedObjLib['MODULELIST'].extend(part['MODULELIST'])
    else:
        if args.ldlibs <> None:
            warningMessage("Ignoring option --ldlibs since --shared was not specified.")
        if args.shared_name <> None:
            warningMessage("Ignoring option --shared-name since --shared was not specified.")

    staticRelPath = "static"
    sharedRelPath = "shared"

    mkFileVerbosity = 1
    if not omits["static"] and len(staticLibs) > 0:
        if not allInOne:
            for staticLib in staticLibs:
                dirName = staticRelPath + "_" + staticLib['LIBNAME']
                lclDstDir = getDstPath(libPath, dirName)
                lclOutDir = getOutPath(libPath, dirName)
                if not os.path.exists(lclOutDir):
                    os.makedirs(lclOutDir)
                mkFileName = os.path.join(lclOutDir, "Android.mk")
                file = open(mkFileName, "wt")
                file.write(moduleMk(staticLib, build_params, staticLibs, None, depMgr, lclDstDir, args, localPath=localPath))
                file.close()
                infoMessage("Created %s" % (mkFileName), mkFileVerbosity)
        else:
            lclDstDir = getDstPath(libPath, staticRelPath)
            lclOutDir = getOutPath(libPath, staticRelPath)
            if not os.path.exists(lclOutDir):
                os.makedirs(lclOutDir)
            mkFileName = os.path.join(lclOutDir, "Android.mk")
            file = open(mkFileName, "wt")
            i = 0
            for staticLib in staticLibs:
                file.write(moduleMk(staticLib, build_params, staticLibs, None, depMgr, lclDstDir, args, localPath=localPath))
                file.write("#" * 60 + "\n")
                i += 1
            file.close()
            infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if sharedObjLib <> None and not omits["shared"]:
        lclDstDir = getDstPath(libPath, sharedRelPath)
        lclOutDir = getOutPath(libPath, sharedRelPath)
        if not os.path.exists(lclOutDir):
            os.makedirs(lclOutDir)
        mkFileName = os.path.join(lclOutDir, "Android.mk")
        file = open(mkFileName, "wt")
        file.write(moduleMk(sharedObjLib, build_params, staticLibs, None, depMgr, lclDstDir, args, localPath=localPath))
        file.close()
        if args.static_libs == None and len(staticLibs) > 0:
            warningMessage("Computed link order is very likely not accurate.")
            warningMessage("See %s." % (mkFileName))
        infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if not omits["top"]:
        if not os.path.isdir(getOutPath(libPath)):
            os.makedirs(getOutPath(libPath))
        topMkFileName = getOutPath(libPath, "Android.mk")
        file = open(topMkFileName, "wt")
        file.write("include $(call all-subdir-makefiles)")
        file.close()

    if not omits["app"]:
        if not os.path.isdir(applicationDir):
            os.makedirs(applicationDir)
        appMkFileName = os.path.join(applicationDir, "Application.mk")
        file = open(appMkFileName, "wt")
        libNames = [staticLib['LIBNAME'] for staticLib in staticLibs]
        if sharedObjLib <> None:
            libNames.append(sharedObjLib['LIBNAME'])
        file.write("APP_MODULES      := %s\n" % (" ".join(libNames)))
        if args.project <> None:
            file.write("APP_PROJECT_PATH := %s" % (absPath(getDstPath())))
        else:
            file.write("APP_PROJECT_PATH := $(call my-dir)/project\n")
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
Creates makefiles for building a set of contexo component files with the Android NDK.

Note that Contexo has a default bconf which likely is not
compatible with Android. Make sure to specify a bc-file in the
export.

The @ can be used to put arguments in a file.

Example usage:
<Contexo Export> | andkmk.py @args.txt --ndk C:/dev/android/android-ndk-1.6_r1 --project project --abs-sub C: /cygdrive/c
Content of args.txt = [
--app midemo
--shared albv_android
--ldlibs GLESv1_CM dl log
--static-libs deplib1 deplib2 deplib3 deplib4
--arm-mode arm
]
The example will create:
<NDK>/apps/midemo/Application.mk
<CWD>/project/jni/Android.mk
<CWD>/project/jni/static_<LIBNAME>/Android.mk (for each static library)
<CWD>/project/jni/shared/Android.mk

""",
 version="0.4.2", formatter_class=RawDescriptionHelpFormatter, fromfile_prefix_chars='@')

parser.set_defaults(func=cmd_parse)

parser.add_argument('-n', '--ndk',
 help="""Specifies the Android NDK root.""")

parser.add_argument('-a', '--app',
 help="""Specifies the name of the application.""")

parser.add_argument('-mp', '--mk-path', default="jni",
 help="""Specifies the relative path from project folder to where the
 makefiles are located. All created makefiles
 will be put in this directory or below it, except the
 Application.mk. Defaults to 'jni'.""")

parser.add_argument('-p', '--project', default=None,
 help="""The project directory.""")

parser.add_argument('-so', '--shared', default=None, nargs='+',
 help="""Specifies one or more libraries (libraries meaning the output specified
 in comp-files), that will be built into one shared object.
 A separate makefile will be generated for this shared object.""")

parser.add_argument('--static-libs', default=None, nargs='*',
 help="""Specifies which static libraries the shared object depends on.
 They must be specified in the order that they depend on each other, i.e. the dependant
 comes before the dependee. If this option is not used all static libraries
 generated (by the export) are assumed (this will produce a probably erroneous link order).
 Use this option with no arguments to have no dependencies.""")

parser.add_argument('--ldlibs', default=None, nargs='+',
 help="""Specifies additional libraries the shared object depends on.
 Par example:
 --ldlibs GLESv1_CM dl log.""")

parser.add_argument('--arm-mode', default=None,
 help="""Specifies the arm mode. Must be either 'thumb' or 'arm'.
 Par example:
 --arm-mode arm.""")
 
parser.add_argument('--no', default=None, nargs='+',
 help="""Omits creating the specified makefiles, which must be one or more of
 the following:
 static, shared, top and/or app.
 """)

parser.add_argument('--shared-name', default=None,
 help="""Specifies the name of the shared object. By default the shared object
 will be given the same name as the first argument to --shared.""")

parser.add_argument('--abs-sub', default=None, nargs='+',
 help="""Substitutes substrings in absolute paths. Must be followed by a 2-multiple of arguments, the second will replace
 the first (for each pair). Useful when building on Cygwin, par example: --abs-sub C: /cygdrive/c""")

parser.add_argument('--rel-sub', default=None, nargs='+',
 help="""Substitutes substrings in relative paths. Must be followed by a 2-multiple of arguments, the second will replace
 the first (for each pair). May be useful when building on Cygwin, par example: --rel-sub C: c""")

parser.add_argument('-o', '--output',
 help="""The output directory for the export. Use this option e.g not to
 to overwrite existing makefiles.
 Note that this option does not affect the source and include
 paths in the created makefiles. Without this option
 the makefiles will be generated at their true
 locations.""")
 
args = parser.parse_args()
args.func(args)
