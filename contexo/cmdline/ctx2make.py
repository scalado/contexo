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

import logging
import logging.handlers
import os
import os.path
import sys
import shutil
import platform
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
    

    if platform.system() == 'Windows':
        relPath = True
        linkHeaders = True
    else:
        relPath = False
        linkHeaders = True # for now

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

    genMakefile(viewDir = viewDir, envFile = envFile, bcFile = bcFile, buildItems = buildItems, buildTests = buildTests, linkHeaders = linkHeaders, relPath = relPath, assignCC = assignCC)

logging.basicConfig(format = '%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S',
                                level = logging.DEBUG);

def dir_has_rspec(view_dir):
    view_filelist = os.listdir(view_dir)
    for entry in view_filelist:
        if entry.endswith('.rspec'):
            return True
    return False

def getBuildConfiguration(cview, bconf):

    bcFilePath = cview.locateItem(bconf, 'bconf')
    bcFilename = os.path.basename(bcFilePath)
    bcPath = os.path.dirname(bcFilePath)

    bcDict = ctx_config.CTXConfig(bcFilePath)
    section = bcDict.get_section('config')
    if not section.has_key('CDEF'):
        logging.userErrorExit("Mandatory BC option 'CDEF' is missing.")

    cdefFilename = section['CDEF']
    cdefFilePath = cview.locateItem(cdefFilename, 'cdef')
    cdefPath = os.path.dirname(cdefFilePath)
    bc = ctx_bc.BCFile(bcFilename, bcPath, cdefPath)
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
    caller_dir = os.path.abspath('.')
    view_dir = os.path.abspath(args_view)
    os.chdir(view_dir)
    view_dir = os.path.abspath('')
    while not dir_has_rspec(view_dir):
        os.chdir('..')
        if view_dir == os.path.abspath(''):
            logging.userErrorExit('ctx could not find an rspec in the supplied argument or any subdirectory')
        view_dir = os.path.abspath('')
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
            if not os.path.isdir(moduleDir):
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

            privHeaderDir = ctx_cmod.getPrivHeaderDir(moduleDir)
            privHeaders = ctx_cmod.getPrivHeadersFromDir(privHeaderDir)
            for basePrivHeader in privHeaders:
                includes.append(privHeaderDir + os.sep + basePrivHeader)

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
                    root,ext = os.path.splitext(baseTestSource)
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
    caller_dir = os.path.abspath('.')
    view_dir = os.path.abspath(args_view)
    os.chdir(view_dir)
    view_dir = os.path.abspath('')
    while not dir_has_rspec(view_dir):
        os.chdir('..')
        if view_dir == os.path.abspath(''):
            logging.userErrorExit('ctx could not find an rspec in the supplied argument or any subdirectory')
        view_dir = os.path.abspath('')
    return view_dir
 
def genMakefile(viewDir = str(), envFile = str(), bcFile = str(), buildItems = list(), buildTests = False, linkHeaders = False, relPath = False, assignCC = False):
    launch_path = os.path.abspath('.')
    view_dir = get_view_dir(viewDir)
    obj_dir = view_dir + os.sep + '.ctx/obj'

    envLayout = None
    oldEnv = None
    if envFile != "":
        envLayout = ctx_envswitch.EnvironmentLayout(cfgFile, envFile)
        oldEnv = ctx_envswitch.switchEnvironment(envLayout, True)

    cview = ctx_view.CTXView(view_dir, validate=False)
    bc = getBuildConfiguration(cview, bcFile)

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

    writeMakefile(librarySources = librarySources, includes = includes, linkHeaders = linkHeaders, bc = bc, viewDir = view_dir, relPath = relPath, assignCC = assignCC)

    if envFile != "":
        switchEnvironment(oldEnv, False)

def linkIncludes(includes, dest, viewDir):
    for includeFile in includes:
        linkFile = open(dest + os.sep + os.path.basename(includeFile), 'w')
        linkFile.write("/* Autogenerated by Contexo\n * changes to this file WILL BE LOST\n */\n")
        linkFile.write("#include \"../../" + includeFile[len(viewDir)+1:].replace('\\','/') + "\"\n\n")
        linkFile.close()
def writeMakefile(librarySources = dict(), includes = list(), linkHeaders = False, bc = None, viewDir = str(), relPath = False, assignCC = False):
    # TODO: hardcoded for now
    libPrefix = bc.getCompiler().cdef['LIBPREFIX']
    libSuffix = bc.getCompiler().cdef['LIBSUFFIX']
    objSuffix = bc.getCompiler().cdef['OBJSUFFIX'] 

    if not os.path.isfile("Makefile.inc"):
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

# config settings
    if not os.path.isfile("Makefile.cfg"):
        cfgmakefile = open("Makefile.cfg", 'w')
        cfgmakefile.write("### Compiler settings\n")
        if assignCC:
            cfgmakefile.write("CC=" + bc.getCompiler().cdef['CC'] + "\n")
            cfgmakefile.write("CXX=g++\n")
        cfgmakefile.write("CFLAGS="+bc.getBuildParams().cflags+"\n")
        cfgmakefile.write("LDFLAGS=\n")
        for subBCName,subBCObject in bc.getSubBC().iteritems():
            cfgmakefile.write(subBCName.upper() + '_CC=' + subBCObject.getCompiler().cdef['CC'] + '\n')
            cfgmakefile.write(subBCName.upper() + '_CFLAGS = ' + subBCObject.getBuildParams().cflags + '\n')
        cfgmakefile.write("\n# Additional compiler parameters, such as include paths\n")
        cfgmakefile.write("ADDFLAGS=\n")
        cfgmakefile.write("\n")
        cfgmakefile.write("AR=ar\n")
        cfgmakefile.write("RANLIB=ranlib\n")
        cfgmakefile.write("\n")
        cfgmakefile.write("OUTPUT=output\n")
        cfgmakefile.write("LIBDIR=$(OUTPUT)/lib\n")
        cfgmakefile.write("OBJDIR=$(OUTPUT)/obj\n")
        cfgmakefile.write("HDRDIR=$(OUTPUT)/inc\n")
        cfgmakefile.write("LINKHEADERS=$(OUTPUT)/linkheaders\n")
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
            makefile.write("-D"+prepDefine+" ")
    makefile.write("\n\n")

    makefile.write("### Build-all definition\n")
    makefile.write("LIBS =")
    for lib in librarySources.keys():
            makefile.write(" $(LIBDIR)/" + libPrefix + lib + libSuffix)
    makefile.write("\n")

    makefile.write("\n")
    makefile.write("### Build-all definition\n")
    makefile.write("all: $(OBJDIR) $(HDRDIR) $(LIBDIR) $(LIBS)")

    makefile.write(" inc_all")
    makefile.write("\n")
    makefile.write("clean: inc_clean\n")
    makefile.write("\t$(RM) $(OBJDIR)/*" + objSuffix + "\n")
    makefile.write("\t$(RM) $(LIBDIR)/*" + libSuffix + "\n")
    makefile.write("\t$(RM) $(HDRDIR)/*.h\n")
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
            baseName, ext = os.path.splitext(sourceDependency)
            makefile.write(" $(OBJDIR)/" + os.path.basename(baseName) + objSuffix)
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
            sourceFileName = sourceFile.replace('\\', '/')
            if relPath:
                sourceFileName = sourceFileName[len(viewDir) + 1:]
            makefile.write(" " + sourceFileName)
    makefile.write("\n")
    for library in librarySources.keys():
        for sourceDependency in librarySources[library]:
            basePath, ext = os.path.splitext(sourceDependency)
            if relPath:
                basePath = basePath[len(viewDir)+1:]
            makefile.write("$(OBJDIR)/" + os.path.basename(basePath) + objSuffix + ": " + sourceDependency[len(viewDir)+1:].replace('\\','/') + "\n")
            makefile.write("\tmakedepend -f-")
            if platform.system() == 'Windows':
                makefile.write(" -D_WIN32")
                if os.environ.has_key("INCLUDE"):
                    for vsIncDir in os.environ['INCLUDE'].split(';'):
                        if len(vsIncDir) == 0:
                            continue
                        vsIncDirMsys = vsIncDir.replace('\\', '/')
                        vsIncDirCygwin = '/cygdrive/' + vsIncDir.replace('\\', '/').replace(':','')
                        makefile.write(" -I\"" + vsIncDirMsys + "\"")
                        makefile.write(" -I\"" + vsIncDirCygwin + "\"")
            makefile.write(" -I\"$(LINKHEADERS)\" $< | sed 's,\($*\\" + objSuffix +"\)[ :]*\(.*\),$@: $$\(wildcard \\2\)\\n\\1: \\2,g' > $*.d\n")
            #makefile.write("\t@$(COMPILE.c) -o $@ $<\n")
            makefile.write("\t@case $< in ")
            for subBCName,subBCObject in bc.getSubBC().iteritems():
                makefile.write("*/sub_bc/" + subBCName + "/*) $(" + subBCName.upper() + "_CC) -I$(LINKHEADERS) $(" + subBCName.upper() + "_CFLAGS) -o $@ $< ;; ")
            makefile.write("*) $(CC) -I\"$(LINKHEADERS)\" $(CFLAGS) -o $@ $<;;esac\n")

    makefile.write("-include $(SRCS:.c=.d)\n")
    makefile.write("\n")

    makefile.close()

main(sys.argv)


