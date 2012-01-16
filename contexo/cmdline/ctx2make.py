#!/usr/bin/env python

###############################################################################
#                                                                             #
#   ctx2make.py                                                               #
#   Generate GNU Makefiles from Contexo views - (c) Scalado AB 2010           #
#                                                                             #
#   Authors: Thomas Eriksson (thomas.eriksson@scalado.com)                    #
#            Ulf Holmstedt (ulf.holmstedt@scalado.com)                        #
#            Manuel Astudillo (manuel.astudillo@scalado.com)                  #
#   License GPL v2. See LICENSE.txt.                                          #
#   ------------                                                              #
#                                                                             #
#                                                                             #
###############################################################################
# coding=UTF-8

# TODO:
# * change output dir to absolute path, -o argument?
# * translate msys/cygwin path to ntpath
# * -ai additional includes ?
#


# cygwin make does not handle mixed paths in target definitions well:
#
# C:/foo/bar.obj: C:/foo/bar.c
#
# instead we need to write them as:
# $(CYGPREFIX)/c/foo/bar.obj: $(CYGPREFIX)/c/foo/bar.c
#
# CYGPREFIX is set to /cygdrive if in cygwin, empty string if in MSYS
# this makes makefiles work on both cygwin and msys
#
# the compiler cannot handle cygwin/msys paths, so we need to retranslate them
# to mixed mode: cc -c C:/foo/bar.c -o C:/foo/bar.o

import logging
import logging.handlers
import os
import os.path
import sys
import shutil
import platform
import posixpath
from contexo import ctx_view 
from contexo import ctx_cfg
from contexo import ctx_envswitch
from contexo import ctx_common
from contexo import ctx_comp
from contexo import ctx_sysinfo
from contexo import ctx_cmod
from contexo import ctx_base
from contexo import ctx_envswitch
from contexo import ctx_bc
from contexo import ctx_config


def main(argv):
    exearg = False
    buildTests = False
    exe = str()
    assignCC = True
    buildItems = list()
    envFile = ""
    viewDir = ""
    bcFile = ""

    linkHeaders = True

    nextArgIsEnv = False
    nextArgIsBC = False
    nextArgIsViewDir = False
    parsedAllOptions = False
    firstArg = True

    for arg in argv:
        if firstArg:
            firstArg = False
            continue
        if arg == '-h':
            print >>sys.stderr, 'help:'
            print >>sys.stderr, '-l, symlink all headers to one directory and use that for include path'
            print >>sys.stderr, '-t, build tests'
            sys.exit(1)
        if nextArgIsEnv:
            envFile = arg
            nextArgIsEnv = False
            continue
        if nextArgIsViewDir:
            viewDir = arg
            nextArgIsViewDir = False
            continue
        if nextArgIsBC:
            bcFile = arg
            nextArgIsBC = False
            continue
        if not parsedAllOptions:
            if arg == '-t':
                buildTests = True
                continue
            if arg == '-l':
                linkHeaders = True
                continue
            if arg == '-nocc':
                assignCC = False
                continue
            if arg == '-e':
                nextArgIsEnv = True
                continue
            if arg == '-b':
                nextArgIsBC = True
                continue
            if arg == '-v':
                nextArgIsViewDir = True
                continue
            parsedAllOptions = True
        if arg[-5:] != ".comp" and arg[0] != '@':
            print >>sys.stderr, 'arguments must be either comp(s) or listfile(s) containing comp(s)'
            sys.exit(1)
        buildItems.append(arg)
    if bcFile == "":
        print >>sys.stderr, 'must have -b argument'
        sys.exit(1)
    if len(buildItems) == 0:
        print >>sys.stderr, 'must have at least one listfile or comp file as argument'
        sys.exit(1)
    argDict = dict()

    genMakefile(viewDir = viewDir, envFile = envFile, bcFile = bcFile, buildItems = buildItems, buildTests = buildTests, linkHeaders = linkHeaders, assignCC = assignCC)

logging.basicConfig(format = '%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S',
                                level = logging.DEBUG);

def winPathToMsys(winPath):
    # C:\foo\bar to /C/foo/bar
    # with the /cygdrive prefix it will be compatible with cygwin
    if winPath[0] != '/':
        winPath = '/' + winPath
    return winPath.replace("\\","/").replace(":","")

def privIncPathForSourceFile(srcFile):
    # /foo/bar/src/baz.c to /foo/bar/inc/
    srcDirIndex = srcFile.rfind('/')
    modDirIndex = srcFile.rfind('/',0,srcDirIndex)
    return srcFile[0:modDirIndex] + '/inc/'

def dir_has_rspec(view_dir):
    view_filelist = os.listdir(view_dir)
    for entry in view_filelist:
        if entry.endswith('.rspec'):
            return True
    return False

def getBuildConfiguration(cview, bconf, cfgFile):

    bcFilePath = cview.locateItem(bconf, 'bconf')
    bcFilename = posixpath.basename(bcFilePath)
    bcPath = posixpath.dirname(bcFilePath)

    bcDict = ctx_config.CTXConfig(bcFilePath)
    section = bcDict.get_section('config')
    if not section.has_key('CDEF'):
        logging.userErrorExit("Mandatory BC option 'CDEF' is missing.")

    cdefFilename = section['CDEF']
    cdefFilePath = cview.locateItem(cdefFilename, 'cdef')
    cdefPath = posixpath.dirname(cdefFilePath)
    bc = ctx_bc.BCFile(bcFilename, bcPath, cdefPath, cfgFile)
    return bc

def expand_list_files(view, item_list):

    expanded_item_list = list()
    for item in item_list:
        item = item.strip(' ')
        if item.startswith('@'):
            infoMessage("Expanding list file '%s'"%item, 2)
            item = item.lstrip('@')
            list_file = view.locateItem(item, ctx_view.REPO_PATH_SECTIONS)
            list_file_items = ctx_common.readLstFile(list_file)
            expanded_item_list.extend(list_file_items)
        else:
            expanded_item_list.append(item)

    return expanded_item_list

def create_components(compFilenames, componentPaths, objDir, launchPath):
    components = list()
    for compFilename in compFilenames:
        comp = ctx_comp.COMPFile(comp_file = compFilename, component_paths = componentPaths, globalOutputDir = objDir, launchPath = launchPath)
        components.append(comp)
    return components

def get_view_dir(args_view):
    caller_dir = posixpath.abspath('.')
    view_dir = posixpath.abspath(args_view)
    os.chdir(view_dir)
    view_dir = posixpath.abspath('')
    while not dir_has_rspec(view_dir):
        os.chdir('..')
        if view_dir == posixpath.abspath(''):
            logging.userErrorExit('ctx could not find an rspec in the supplied argument or any subdirectory')
        view_dir = posixpath.abspath('')
    return view_dir
 
def parseComps(cview, viewDir, buildTests, bc, compsToBuild):
    librarySources = dict()
    includes = list()

    modulesToBuild = list()
    compDict = dict()
    moduleDict = dict()

    for comp in compsToBuild:
        for library, compModules in comp.libraries.items():
            compDict[library] = compModules
            for module in compModules:
                moduleDict[module] = library

    for moduleSearchDir in cview.getItemPaths('modules'):
        for module in os.listdir(moduleSearchDir):
            moduleDir = moduleSearchDir + os.sep + module
            if not posixpath.isdir(moduleDir):
                continue
            if module in moduleDict.keys():
                sourceDir = ctx_cmod.getSourceDir(moduleDir)
                sources, prebuiltObjFiles, subBCSrcDict = ctx_cmod.getSourcesFromDir(sourceDir, bc.getArchPath(), bc.getSubBC())

                libraryName = moduleDict[module] 
                if libraryName not in librarySources.keys():
                    librarySources[libraryName] = list()
                for baseSourceFile in sources:
                    librarySources[libraryName].append(sourceDir + os.sep + baseSourceFile)
                inlSources = ctx_cmod.getInlSourcesFromDir(sourceDir)
                for baseInlSource in inlSources:
                    includes.append(sourceDir + os.sep + baseInlSource)

            pubHeaderDir = ctx_cmod.getPubHeaderDir(moduleDir)
            pubHeaders = ctx_cmod.getPubHeadersFromDir(pubHeaderDir)
            for basePubHeader in pubHeaders:
                includes.append(pubHeaderDir + os.sep + basePubHeader)

            if buildTests:
                testSourceDir = ctx_cmod.getTestDir(moduleDir)
                testSources = ctx_cmod.getSourcesFromDir(testHeaderDir)
                libraryName = moduleDict[module] 
                if libraryName not in librarySources.keys():
                    librarySources[libraryName] = list()
                for baseTestSource in testSources:
                    librarySources[libraryName].append(testSourceDir + os.sep + baseTestSource)
                    root,ext = posixpath.splitext(baseTestSource)
                    if ext in ['.hpp', '.h', '.inl']:
                        includes.append(testSourceDir + os.sep + baseTestSource)
    return librarySources,includes


def expand_list_files(view, item_list):

    expanded_item_list = list()
    for item in item_list:
        item = item.strip(' ')
        if item.startswith('@'):
            infoMessage("Expanding list file '%s'"%item, 2)
            item = item.lstrip('@')
            list_file = view.locateItem(item, ctx_view.REPO_PATH_SECTIONS)
            list_file_items = ctx_common.readLstFile(list_file)
            expanded_item_list.extend(list_file_items)
        else:
            expanded_item_list.append(item)

    return expanded_item_list

def create_components(compFilenames, componentPaths, objDir, launchPath):
    components = list()
    for compFilename in compFilenames:
        comp = ctx_comp.COMPFile(comp_file = compFilename, component_paths = componentPaths, globalOutputDir = objDir, launchPath = launchPath)
        components.append(comp)
    return components

def get_view_dir(args_view):
    caller_dir = posixpath.abspath('.')
    view_dir = posixpath.abspath(args_view)
    os.chdir(view_dir)
    view_dir = posixpath.abspath('')
    while not dir_has_rspec(view_dir):
        os.chdir('..')
        if view_dir == posixpath.abspath(''):
            logging.userErrorExit('ctx could not find an rspec in the supplied argument or any subdirectory')
        view_dir = posixpath.abspath('')
    return view_dir
 
def genMakefile(viewDir = str(), envFile = str(), bcFile = str(), buildItems = list(), buildTests = False, linkHeaders = False, assignCC = False):
    launch_path = posixpath.abspath('.')
    view_dir = get_view_dir(viewDir)
    obj_dir = view_dir + os.sep + '.ctx/obj'

    envLayout = None
    oldEnv = None

    contexo_config_path = posixpath.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
    cfgFile = ctx_cfg.CFGFile( contexo_config_path )
    if envFile != "":
        envLayout = ctx_envswitch.EnvironmentLayout(cfgFile, envFile)
        oldEnv = ctx_envswitch.switchEnvironment(envLayout, True)

    cview = ctx_view.CTXView(view_dir, validate=False)
    bc = getBuildConfiguration(cview, bcFile, cfgFile)

    comps = expand_list_files(cview, buildItems)

    components = list()
    modules = list()
    components = create_components(comps, cview.getItemPaths('comp'), obj_dir, launch_path)
    for comp in components:
        for library, compModules in comp.libraries.items():
            modules.extend(compModules)

    librarySources, includes = parseComps(cview, view_dir, buildTests, bc, components)

    if linkHeaders:
        dest = 'output' + os.sep + 'linkheaders'
        linkIncludes(includes, dest, view_dir)

    writeMakefile(librarySources = librarySources, includes = includes, linkHeaders = linkHeaders, bc = bc, viewDir = view_dir, assignCC = assignCC)

    if envFile != "":
        switchEnvironment(oldEnv, False)

def linkIncludes(includes, dest, viewDir):
    for includeFile in includes:
        if not os.path.isdir(dest):
            os.makedirs(dest)
        linkFile = open(dest + os.sep + os.path.basename(includeFile), 'w')
        linkFile.write("/* Autogenerated by Contexo\n * changes to this file WILL BE LOST\n */\n")
        linkFile.write("#include \"../../" + includeFile + "\"\n\n")
        linkFile.close()
def writeMakefile(librarySources = dict(), includes = list(), linkHeaders = False, bc = None, viewDir = str(), assignCC = False):
    # TODO: hardcoded for now
    libPrefix = bc.getCompiler().cdef['LIBPREFIX']
    libSuffix = bc.getCompiler().cdef['LIBSUFFIX']
    objSuffix = bc.getCompiler().cdef['OBJSUFFIX']
    cppDefPrefix = bc.getCompiler().cdef['CPPDEFPREFIX']
    cppDefSuffix = bc.getCompiler().cdef['CPPDEFSUFFIX']
    arCommandLine = bc.getCompiler().cdef['ARCOM']   
    cxx = bc.getCompiler().cdef['CXX']
    ccCommandLine = bc.getCompiler().cdef['CCCOM']
    cxxCommandLine = bc.getCompiler().cdef['CXXCOM']

    ccCommandLine = ccCommandLine.replace('%CFLAGS', '$(CFLAGS) $(ADDFLAGS)')
    ccCommandLine = ccCommandLine.replace('%CC', '$(CC)')
    incPrefix = bc.getCompiler().cdef['INCPREFIX']
    incSuffix = bc.getCompiler().cdef['INCSUFFIX']
    ccCommandLine = ccCommandLine.replace("%SOURCES", "$<")
    ccCommandLine = ccCommandLine.replace("%TARGET", "$@")

    for subBCName,subBCObject in bc.getSubBC().iteritems():
        subIncPrefix = subBCObject.getCompiler().cdef['INCPREFIX']
        subIncSuffix = subBCObject.getCompiler().cdef['INCSUFFIX']
        subCcCommandLine = subBCObject.getCompiler().cdef['CCCOM']
        subCxxCommandLine = subBCObject.getCompiler().cdef['CXXCOM']
        subCppDefPrefix = subBCObject.getCompiler().cdef['CPPDEFPREFIX']
        subCppDefSuffix = subBCObject.getCompiler().cdef['CPPDEFSUFFIX']
        subCcCommandLine = subCcCommandLine.replace('%CFLAGS', '$('+ subBCName.upper() + '_CFLAGS) $(ADDFLAGS)')
        subCcCommandLine = subCcCommandLine.replace('%CC', '$(' + subBCName.upper() + '_CC)')
        subCcCommandLine = subCcCommandLine.replace("%SOURCES", "$<")
        subCcCommandLine = subCcCommandLine.replace("%TARGET", "$@")
        subCcCommandLine = subCcCommandLine.replace("%INCPATHS", subIncPrefix +  "$(LINKHEADERS)" + subIncSuffix)
        subCcCommandLine = subCcCommandLine.replace('\\','/')
        subCxx = subBCObject.getCompiler().cdef['CXX']
        subCxxCommandLine = subBCObject.getCompiler().cdef['CXXCOM']

        break
    if not posixpath.isfile("Makefile.inc"):
        incmakefile = open("Makefile.inc", 'w')
        incmakefile.write("### inc_all is built after all other projects is built\n")
        incmakefile.write("### add dependencies for inc_all to add further build steps\n")
        incmakefile.write("inc_all: $(LIBS)\n")
        incmakefile.write("\ttouch $@\n\n")
        incmakefile.write("### add dependencies for inc_clean to add further clean steps\n")
        incmakefile.write("inc_clean:\n")
        incmakefile.write("\ttouch $@\n")
        incmakefile.close()

# Start writing to the file - using default settings for now
    makefile = open("Makefile", 'w')

# File header
    makefile.write("#############################################\n")
    makefile.write("### Makefile generated with contexo plugin.\n")
    makefile.write("ifeq ($(OSTYPE),cygwin)\n")
    makefile.write("\tCYGPREFIX=\"/cygdrive\"\n")
    makefile.write("else\n")
    makefile.write("\tCYGPREFIX=\n")
    makefile.write("endif\n")

# config settings
    if not posixpath.isfile("Makefile.cfg"):
        cfgmakefile = open("Makefile.cfg", 'w')
        cfgmakefile.write("### Compiler settings\n")
        if assignCC:
            cfgmakefile.write("CC=" + bc.getCompiler().cdef['CC'].replace('\\','/') + "\n")
            cfgmakefile.write("CXX=" + bc.getCompiler().cdef['CXX'].replace('\\','/') + "\n")
        cfgmakefile.write("CFLAGS="+bc.getBuildParams().cflags.replace('\\','/')+"\n")
        cfgmakefile.write("LDFLAGS=\n")
        for subBCName,subBCObject in bc.getSubBC().iteritems():
            cfgmakefile.write(subBCName.upper() + '_CC=' + subBCObject.getCompiler().cdef['CC'].replace('\\','/') + '\n')
            cfgmakefile.write(subBCName.upper() + '_CXX=' + subBCObject.getCompiler().cdef['CXX'].replace('\\','/') + '\n')
            cfgmakefile.write(subBCName.upper() + '_CFLAGS = ' + subBCObject.getBuildParams().cflags.replace('\\','/') + '\n')
            break
        cfgmakefile.write("\n# Additional compiler parameters, such as include paths\n")
        cfgmakefile.write("ADDFLAGS=\n")
        cfgmakefile.write("\n")
        cfgmakefile.write("AR=" + bc.getCompiler().cdef['AR'] + "\n")
        cfgmakefile.write("RANLIB=" "\n")
        cfgmakefile.write("\n")
        cfgmakefile.write("OUTPUT=" + viewDir + os.sep + "output\n")
        cfgmakefile.write("LIBDIR=$(OUTPUT)/lib\n")
        cfgmakefile.write("OBJDIR=$(OUTPUT)/obj\n")
        cfgmakefile.write("HDRDIR=$(OUTPUT)/inc\n")
        cfgmakefile.write("LINKHEADERS=$(OUTPUT)/linkheaders\n")
        cfgmakefile.write("DEPDIR=$(OUTPUT)/makedeps\n")
        cfgmakefile.write("\n")
        
        cfgmakefile.write("EXPORT_CMD=cp\n")
        cfgmakefile.write("RM=rm -rf\n")
        cfgmakefile.write("MKDIR=mkdir -p\n")
        cfgmakefile.write("TOUCH=touch\n")
        cfgmakefile.write("\n")

    makefile.write("\n")
    makefile.write("### include user configured settings\n")
    makefile.write("include Makefile.cfg\n")
    makefile.write("\n")

    if linkHeaders == True:
            makefile.write("### symlinked headers output dir\n")
            makefile.write("INCLUDES=-I" + "$(OUTPUT)/hdrlinks")
            makefile.write("\n")

    makefile.write("### Standard defines\n")
    makefile.write("PREP_DEFS=")
    for prepDefine in bc.getBuildParams().prepDefines:
            makefile.write(" " + cppDefPrefix+prepDefine+cppDefSuffix)
    makefile.write("\n\n")

    for subBCName,subBCObject in bc.getSubBC().iteritems():
        makefile.write("SUB_PREP_DEFS=")
        for prepDefine in subBCObject.getBuildParams().prepDefines:
            makefile.write(" " + subCppDefPrefix+prepDefine+subCppDefSuffix)
        makefile.write("\n\n")
        break

    makefile.write("### Build-all definition\n")
    makefile.write("LIBS =")
    for lib in librarySources.keys():
            makefile.write(" $(LIBDIR)/" + libPrefix + lib + libSuffix)
    makefile.write("\n")

    makefile.write("\n")
    makefile.write("### Build-all definition\n")
    makefile.write("all: $(OBJDIR) $(HDRDIR) $(LIBDIR) $(DEPDIR) $(LINKHEADERS) $(LIBS)")

    makefile.write(" inc_all")
    makefile.write("\n")
    makefile.write("clean: inc_clean\n")
    makefile.write("\t$(RM) $(OBJDIR)/*" + objSuffix + "\n")
    makefile.write("\t$(RM) $(LIBDIR)/*" + libSuffix + "\n")
    makefile.write("\t$(RM) $(DEPDIR)/*\n")
    makefile.write("\t$(RM) $(HDRDIR)/*\n")
    makefile.write("\n")

    makefile.write("\n")
    makefile.write("### include user configured targets\n")
    makefile.write("include Makefile.inc\n")
    makefile.write("\n")

    makefile.write("\n")
    makefile.write("### create directories\n")
    makefile.write("$(OBJDIR):\n")
    makefile.write("\t$(MKDIR) $@\n")
    makefile.write("$(LIBDIR):\n")
    makefile.write("\t$(MKDIR) $@\n")
    makefile.write("$(HDRDIR):\n")
    makefile.write("\t$(MKDIR) $@\n")
    makefile.write("$(LINKHEADERS):\n")
    makefile.write("\t$(MKDIR) $@\n")
    makefile.write("$(DEPDIR):\n")
    makefile.write("\t$(MKDIR) $@\n")
    makefile.write("\n")

    makefile.write("\n")
    makefile.write("### Component definitions\n")
# arch obj files
# libraries with libprefix and libsuffix
# handle export headers
    libraryBuildRules = list()
    for library in librarySources.keys():
        libraryBuildRule = "$(LIBDIR)/" + libPrefix + library + libSuffix
        makefile.write( libraryBuildRule + ":")
        for sourceDependency in librarySources[library]:
            sourceDependencyName = winPathToMsys(sourceDependency)
            baseName, ext = posixpath.splitext(sourceDependencyName)
            makefile.write(" $(CYGPREFIX)$(OBJDIR)/" + posixpath.basename(baseName) + objSuffix)
        makefile.write("\n")
        libraryBuildRules.append(libraryBuildRule)
    makefile.write("\n")
    makefile.write(".PHONY: all\n")
    makefile.write("all: ")
    for libraryBuildRule in libraryBuildRules:
        makefile.write(libraryBuildRule + " ")
    makefile.write("\n")
    
    makefile.write("SRCS =")
    for library in librarySources.keys():
        for sourceFile in librarySources[library]:
            sourceFileName = winPathToMsys(sourceFile)
            makefile.write(" $(CYGPREFIX)" + sourceFileName)
    makefile.write("\n")
    for library in librarySources.keys():
        for sourceDependency in librarySources[library]:
            sourceDependencyName = winPathToMsys(sourceDependency)
            basePath, ext = posixpath.splitext(sourceDependencyName)
            makefile.write("$(CYGPREFIX)$(OBJDIR)/" + posixpath.basename(basePath) + objSuffix + ": $(CYGPREFIX)" + sourceDependencyName + "\n")
            makefile.write("\tRAW_SRC=$@;SRC_NOPREFIX=$${FOO#/};DRIVE=$${SRC_NOPREFIX%%/*};UNC_SRC=$${DRIVE}:/$${SRC_NOPREFIX#*/};")
            makefile.write("OUTPUT=\"$<\";export CYGWIN=nodosfilewarning;SOURCEFILE=\"$*\";OBJFILE=\"$${SOURCEFILE%.*}\"" + objSuffix + ";makedepend -f-")
            makefile.write(" -I" + privIncPathForSourceFile(sourceDependencyName) + " -I\"$(LINKHEADERS)\" $< 2>/dev/null | sed \"s,.*:,\\$$(OBJDIR)/$${SOURCEFILE##*/}" + objSuffix + ":,\" > $(DEPDIR)/$${OUTPUT##*/}.d\n")
# -e '/^C:/d'
            if sourceDependencyName.count("/sub_bc/") > 0:
                subCommandLine = "\t" + subCcCommandLine
                subCommandLine = subCommandLine.replace("%INCPATHS", subIncPrefix + privIncPathForSourceFile(sourceDependencyName) + subIncSuffix + " " + subIncPrefix + "$(LINKHEADERS)" + subIncSuffix)
                subCommandLine = subCommandLine.replace('%CPPDEFINES','$(SUB_PREP_DEFS)')
                makefile.write(subCommandLine)
            else:
                commandLine = "\t" + ccCommandLine
                commandLine = commandLine.replace("%INCPATHS", incPrefix + privIncPathForSourceFile(sourceDependencyName) + incSuffix + " " + incPrefix + "$(LINKHEADERS)" + incSuffix)
                commandLine = commandLine.replace("%CPPDEFINES","$(PREP_DEFS)")
                makefile.write(commandLine)
            makefile.write("\n")

    makefile.write("-include \"$(DEPDIR)\"/*.d\n")
    makefile.write("\n")

    makefile.close()

main(sys.argv)


