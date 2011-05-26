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
    def _preProcPath(_path):
        if os.path.isfile(_path):
            _p, _name = os.path.split(_path)
            if len(_p) == 0:
                userErrorExit( "Bad path '%s'." % (_path))
            return absPath(_p)
        else:
            return absPath(_path)
    paths = [reg.split(_preProcPath(path)) for path in paths]
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

def writeVars(argList, argName):
    outData = []
    args = []
    whspc = re.compile(r"\s+")
    for arg in argList:
        tmpArgs = []
        for tmpArg in whspc.split(arg):
            if tmpArg[0] == '"' and tmpArg[-1] == '"':
                args.append(tmpArg[1:-1])
            else:
                args.append(tmpArg)
        args.extend(filter(lambda x : len(x) > 0, tmpArgs))
    i = 0
    while i < len(args):
        if i + 1 >= len(args) or not (args[i + 1] == ":=" or args[i + 1] == "+="):
            userErrorExit( "Missing assigmnet operator for '%s' for %s." % (args[i], argName))
        j = i + 2
        while j < len(args) and args[j] != ":=" and args[j] != "+=":
            j += 1
        if j < len(args):
            k = j - 1
        else:
            k = j
        spcLen = len(args[i]) + len(args[i + 1]) + 2
        values = [a.replace("$(_HYPHEN_)", "-") for a in args[i + 2:k]]
        assignment = "%s %s %s" % (args[i], args[i + 1], (" \\\n" + spcLen * " ").join(values))
        outData.append(assignment)
        outData.append("\n\n")
        i = k
    return "".join(outData)
			
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
    moduleName = module['LIBNAME']
    if args.mydroid <> None and not moduleName.find("lib") == 0:
        moduleName = "lib" + moduleName
    outData.append("# Locale module [%s]\n" % (moduleName))
    outData.append("include $(CLEAR_VARS)\n\n")
    outData.append("LOCAL_MODULE := %s\n\n" % (moduleName))

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
        # TODO: the preprocessor define COMPILING_MOD_ is a legacy definition,
        # initially created to make sure private headers were not included in a
        # project.
        # DO NOT REMOVE until all previous releases compiles without it.
        # /thomase
        localFlags.append(prepDefPrefix + "COMPILING_MOD_" + ctxMod["MODNAME"].upper() + prepDefSuffix)
    localFlags.extend ( build_params.cflags.split() )
    localFlags.extend ( build_params.asmflags.split() )
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
            depMods = []
            for staticLib in staticLibs:
                if args.mydroid <> None and not staticLib.find("lib") == 0:
                    depMods.append("lib" + staticLib)
                else:
                    depMods.append(staticLib)
        if len(depMods) > 0:
            outData.append("LOCAL_STATIC_LIBRARIES := %s\n\n" % (" ".join(depMods)))
        if ldlibs <> None and len(ldlibs) > 0:
            ldlibs = [("-l" + ldlib) for ldlib in ldlibs]
            if len(ldlibs) > 0:
                outData.append("LOCAL_LDLIBS := %s\n\n" % (" ".join(ldlibs)))

    if args.arm_mode <> None:
        outData.append("LOCAL_ARM_MODE := %s\n\n" % (args.arm_mode))

    # Custom variables
    if args.vars_android <> None:
        outData.append(writeVars(args.vars_android, "--vars-android"))

    #
    # Library type specific.
    #
    if module.has_key('SHAREDOBJECT') and module['SHAREDOBJECT']:
        if args.vars_shared <> None:
            outData.append(writeVars(args.vars_shared, "--vars-shared"))
        outData.append("include $(BUILD_SHARED_LIBRARY)\n\n")
    else:
        if args.vars_static <> None:
            outData.append(writeVars(args.vars_static, "--vars-static"))
        outData.append("include $(BUILD_STATIC_LIBRARY)\n\n")

    return "".join(outData)

#------------------------------------------------------------------------------
def prebuiltMk(args):
    content = []
    def _localPath(path):
        return absPath(path.replace("\\", "/"))
    for preb in args.prebuilt:
        if not os.path.isabs(preb):
            preb = os.path.join(os.getcwd(), preb)
        if not os.path.isfile(preb):
            userErrorExit("Prebuilt library '%s' doesn't exist." % (preb))
        name, ext = os.path.splitext(preb)
        name = os.path.basename(name)
        content.append("include $(CLEAR_VARS)\n")
        content.append("LOCAL_PATH := %s\n" % (_localPath(os.path.dirname(preb))))
        content.append("LOCAL_MODULE := %s\n" % (name))
        content.append("LOCAL_PREBUILT_LIBS := %s\n" % (name + ext))
        content.append("include $(BUILD_MULTI_PREBUILT) \n")
    return "".join(content)
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

def createFile(filename, content, args):
    file = open(filename, "wt")
    file.write(content)
    file.close()
#------------------------------------------------------------------------------
omits = {"static" : False, "shared" : False, "top" : False, "app" : False, "prebuilt" : False}
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

    # Basic argument checks
    if args.ndk == None and args.mydroid == None:
        userErrorExit("Must specify either --ndk or --mydroid.")
    elif args.ndk <> None and args.mydroid <> None:
        userErrorExit("Specified both --ndk and --mydroid.")
    elif args.ndk <> None:
        if not os.path.isdir(args.ndk):
            userErrorExit("'%s' specified by --ndk does not exist or is not a directory." % (args.ndk))
    else:
        if not os.path.isdir(args.mydroid):
            userErrorExit("'%s' specified by --mydroid does not exist or is not a directory." % (args.mydroid))
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
        elif args.ndk <> None:
            return os.path.join(args.ndk, "apps", args.app, "project", *pathComps).replace("\\", "/")
        else:
            return os.path.join(args.mydroid, args.app, *pathComps).replace("\\", "/")

    # Returns a path that locates where to actually put a file.
    def getOutPath(*pathComps):
        if args.output <> None:
            if not os.path.isabs(args.output):
                return os.path.join(os.getcwd(), args.output, "apps", args.app, "project", *pathComps).replace("\\", "/")
            else:
                return os.path.join(args.output, "apps", args.app, "project", *pathComps).replace("\\", "/")
        else:
            return getDstPath(*pathComps)

    if args.ndk <> None:
        # Determine location of the Application.mk.
        if args.output == None:
            applicationDir = os.path.join(args.ndk, "apps", args.app)
        else:
            if not os.path.isabs(args.output):
                applicationDir = os.path.join(os.getcwd(), args.output, "apps", args.app).replace("\\", "/")
            else:
                applicationDir = os.path.join(args.output, "apps", args.app).replace("\\", "/")
        libPath = args.mk_path
    else:
        # Source tree build, determine location of the main Android.mk.
        if args.output == None:
            applicationDir = os.path.join(args.mydroid, args.app)
        else:
            if not os.path.isabs(args.output):
                applicationDir = os.path.join(os.getcwd(), args.output, args.app).replace("\\", "/")
            else:
                applicationDir = os.path.join(args.output, args.app).replace("\\", "/")
        libPath = ""


    # Determine if anything is to be omitted.
    if args.no <> None:
        argOmits = [no.lower() for no in args.no]
        for omit in argOmits:
            if not omits.has_key(omit):
                userErrorExit("'%s' is not a valid argument to --no." % (omit))
            else:
                omits[omit] = True
    if args.mydroid <> None and args.project == None:
        omits["top"] = True

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
                content = moduleMk(staticLib, build_params, staticLibs, None, depMgr, lclDstDir, args, localPath=localPath)
                createFile(mkFileName, content, args)
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
        content = moduleMk(sharedObjLib, build_params, staticLibs, None, depMgr, lclDstDir, args, localPath=localPath)
        createFile(mkFileName, content, args)
        if args.static_libs == None and len(staticLibs) > 0:
            warningMessage("Computed link order is very likely not accurate.")
            warningMessage("See %s." % (mkFileName))
        infoMessage("Created %s" % (mkFileName), mkFileVerbosity)

    if args.prebuilt <> None and not omits["prebuilt"]:
        name = "prebuilt"
        lclDstDir = getDstPath(libPath, name)
        lclOutDir = getOutPath(libPath, name)
        if not os.path.exists(lclOutDir):
            os.makedirs(lclOutDir)
        mkFileName = os.path.join(lclOutDir, "Android.mk")
        content = prebuiltMk(args)
        createFile(mkFileName, content, args)

    if not omits["top"]:
        if not os.path.isdir(getOutPath(libPath)):
            os.makedirs(getOutPath(libPath))
        topMkFileName = getOutPath(libPath, "Android.mk")
        createFile(topMkFileName, "include $(call all-subdir-makefiles)", args)

    if not omits["app"]:
        if not os.path.isdir(applicationDir):
            os.makedirs(applicationDir)
        outData = []
        if args.ndk <> None:
            appMkFileName = os.path.join(applicationDir, "Application.mk")
            libNames = [staticLib['LIBNAME'] for staticLib in staticLibs]
            if sharedObjLib <> None:
                libNames.append(sharedObjLib['LIBNAME'])
            outData.append("APP_MODULES      := %s\n" % (" ".join(libNames)))
            if args.project <> None:
                outData.append("APP_PROJECT_PATH := %s\n" % (absPath(getDstPath())))
            else:
                outData.append("APP_PROJECT_PATH := $(call my-dir)/project\n")
            if bc_file.dbgmode:
                outData.append("APP_OPTIM      := debug\n")
            if args.vars_app <> None:
                outData.append(writeVars(args.vars_app, "--vars-app"))
        else:
            appMkFileName = os.path.join(applicationDir, "Android.mk")
            if args.project <> None:
                outData.append("include $(call all-makefiles-under,%s)\n"  % (absPath(getDstPath())))
            else:
                outData.append("include $(call all-subdir-makefiles)\n")
        content = "".join(outData)
        createFile(appMkFileName, content, args)
		
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

Example, exporting to a the android source tree:
$ python /usr/local/bin/ctx.py export mycomp.comp  --bconf android_mk_rel.bc --view . --tolerate-missing-headers > exported.txt
$ cat exported.txt | python andkmk.py @args.txt --mydroid /home/user/android/eclair
Content of args.txt = [
--app mymodule
--shared mysharedmodule
--static-libs mystaticmodule
--vars-android
LOCAL_C_INCLUDES += $(JNI_H_INCLUDE)
                    frameworks/base/include/binder
                    external/skia/include/core
                    frameworks/base/core/jni/android/graphics
--vars-shared
LOCAL_SHARED_LIBRARIES := libandroid_runtime
                          libnativehelper
                          libcutils
                          libutils
                          libui
                          libbinder
                          libskia
                          libmedia
LOCAL_PRELINK_MODULE := false
]
The example will create a number of Android.mk files under /home/user/android/eclair/mymodule.
""",
 version="0.5", formatter_class=RawDescriptionHelpFormatter, fromfile_prefix_chars='@')

parser.set_defaults(func=cmd_parse)

parser.add_argument('-n', '--ndk',
 help="""Specifies the Android NDK root.""")

parser.add_argument('-m', '--mydroid',
 help="""Specifies the mydroid root. (Android source tree build.)""")
 
parser.add_argument('-a', '--app',
 help="""Specifies the name of the application. For a source tree build this will be the name of
 the subfolder of mydroid to put the main Android.mk in.""")

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

parser.add_argument('--prebuilt', default=None, nargs='+',
 help="""Specifies prebuilt libraries.""")

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
 the following set:
 {%s}.
 """ % (", ".join(omits.keys())))

parser.add_argument('--shared-name', default=None,
 help="""Specifies the name of the shared object. By default the shared object
 will be given the same name as the first argument to --shared.""")

parser.add_argument('--abs-sub', default=None, nargs='+',
 help="""Substitutes substrings in absolute paths. Must be followed by a 2-multiple of arguments, the second will replace
 the first (for each pair). Useful when building on Cygwin, par example: --abs-sub C: /cygdrive/c""")

parser.add_argument('--rel-sub', default=None, nargs='+',
 help="""Substitutes substrings in relative paths. Must be followed by a 2-multiple of arguments, the second will replace
 the first (for each pair). May be useful when building on Cygwin, par example: --rel-sub C: c""")

parser.add_argument('--vars-android', default=None, nargs='+',
 help="""Adds variables to all generated Android.mk files (both static and shared).
 Arguments must be given as one or more sequences of name, assignment operator and then zero or more values.
 Example: --vars-android MY_VAR1 := A B C MY_VAR2 += D E.
 If := is used these variables will override any generated variables, since they will be appended after them.
 Therefore, in case you want to add includes to LOCAL_C_INCLUDES you should use +=.
 If you want to assign things starting with hyphens, like -O3 you must surround them with quotation marks ("-O3").""")

parser.add_argument('--vars-static', default=None, nargs='+',
 help="""Adds variables to all generated static library Android.mk files.
 See description of --vars-android.""")

parser.add_argument('--vars-shared', default=None, nargs='+',
 help="""Adds variables to all generated shared library Android.mk files.
 See description of --vars-android.""")

parser.add_argument('--vars-app', default=None, nargs='+',
 help="""Adds variables to the generated Application.mk file.
 See description of --vars-android.""")

parser.add_argument('-o', '--output',
 help="""The output directory for the export. Use this option e.g not to
 to overwrite existing makefiles.
 Note that this option does not affect the source and include
 paths in the created makefiles. Without this option
 the makefiles will be generated at their true
 locations.""")
 
args = parser.parse_args()
args.func(args)
