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
from contexo import ctx2_common
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
    assignCC = True
    buildItems = list()
    envFile = ""
    viewDir = ""
    bcFile = ""
    addInc = ""
    outputDir = ""

    linkHeaders = True

    nextArgIsEnv = False
    nextArgIsBC = False
    nextArgIsViewDir = False
    nextArgIsAdditionalIncludes = False
    nextArgIsOutputDir = False
    parsedAllOptions = False
    firstArg = True

    for arg in argv:
        if firstArg:
            firstArg = False
            continue
        if arg == '-h':
            print >>sys.stderr, 'help:'
            print >>sys.stderr, '-b <BCFILE>, .bc file to use'
            print >>sys.stderr, '-o <DIR>, output dir for Makefile, Makefile.cfg, Makefile.inc'
            print >>sys.stderr, '-ai <DIR>, additional includes'
            print >>sys.stderr, '-v <DIR>, override autodetection of view dir'
            print >>sys.stderr, '-e <ENVFILE>, envfile'
            print >>sys.stderr, '-nocc, disable setting the CC and CXX variables (use with scan-build)'
            print >>sys.stderr, '-t, build tests'
            sys.exit(1)
        if nextArgIsOutputDir:
            outputDir = arg
            outputDir = outputDir.replace('\\','/')
            if len(outputDir) > 0:
                if outputDir[-1] != '/':
                    outputDir = outputDir + '/'
            nextArgIsOutputDir = False
            continue
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
        if nextArgIsAdditionalIncludes:
            if len(addInc) > 0:
                print >>sys.stderr, 'only one \'-ai\' argument allowed'
                sys.exit(1)
            addInc = arg
            nextArgIsAdditionalIncludes = False
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

    genMakefile(outputDir = outputDir, viewDir = viewDir, envFile = envFile, bcFile = bcFile, buildItems = buildItems, buildTests = buildTests, linkHeaders = linkHeaders, assignCC = assignCC, addInc = addInc)

logging.basicConfig(format = '%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S',
                                level = logging.DEBUG);

def writeMakefile(outputDir = str(), librarySources = dict(), includes = list(), linkHeaders = False, bc = None, viewDir = str(), assignCC = False, addInc = str()):
    libPrefix = bc.getCompiler().cdef['LIBPREFIX']
    libSuffix = bc.getCompiler().cdef['LIBSUFFIX']
    objSuffix = bc.getCompiler().cdef['OBJSUFFIX']
    cppDefPrefix = bc.getCompiler().cdef['CPPDEFPREFIX']
    cppDefSuffix = bc.getCompiler().cdef['CPPDEFSUFFIX']
    arCommandLine = bc.getCompiler().cdef['ARCOM']   
    cxx = bc.getCompiler().cdef['CXX']
    ccCommandLine = bc.getCompiler().cdef['CCCOM']
    cxxCommandLine = bc.getCompiler().cdef['CXXCOM']

    cxxFileSuffix = bc.getCompiler().cdef['CXXFILESUFFIX']

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
        subCxxCommandLine = subCxxCommandLine.replace('%CXXFLAGS', '$('+ subBCName.upper() + '_CXXFLAGS) $(ADDFLAGS)')
        subCcCommandLine = subCcCommandLine.replace('%CC', '$(' + subBCName.upper() + '_CC)')
        subCcCommandLine = subCcCommandLine.replace("%SOURCES", "$<")
        subCcCommandLine = subCcCommandLine.replace("%TARGET", "$@")
        subCcCommandLine = subCcCommandLine.replace("%INCPATHS", subIncPrefix +  "$(LINKHEADERS)" + subIncSuffix)
        subCcCommandLine = subCcCommandLine.replace('\\','/')
        subCxx = subBCObject.getCompiler().cdef['CXX']
        subCxxCommandLine = subBCObject.getCompiler().cdef['CXXCOM']
        subCxxFileSuffix = subBCObject.getCompiler().cdef['CXXFILESUFFIX']

        break
    if not posixpath.isfile(outputDir + "Makefile.inc"):
        incmakefile = open(outputDir + "Makefile.inc", 'w')
        incmakefile.write("### inc_all is built after all other projects is built\n")
        incmakefile.write("### add dependencies for inc_all to add further build steps\n")
        incmakefile.write("inc_all: $(LIBS)\n")
        incmakefile.write("\ttouch $@\n\n")
        incmakefile.write("### add dependencies for inc_clean to add further clean steps\n")
        incmakefile.write("inc_clean:\n")
        incmakefile.write("\ttouch $@\n")
        incmakefile.close()

# Start writing to the file - using default settings for now
    makefile = open(outputDir + "Makefile", 'w')

# File header
    makefile.write("#############################################\n")
    makefile.write("### Makefile generated with contexo plugin.\n")
    makefile.write("ifeq ($(OSTYPE),cygwin)\n")
    makefile.write("\tCYGPREFIX=\"/cygdrive\"\n")
    makefile.write("else\n")
    makefile.write("\tCYGPREFIX=\n")
    makefile.write("endif\n")

# config settings
    if not posixpath.isfile(outputDir + "Makefile.cfg"):
        cfgmakefile = open(outputDir + "Makefile.cfg", 'w')
        cfgmakefile.write("### Compiler settings\n")
        if assignCC:
            cfgmakefile.write("CC=" + bc.getCompiler().cdef['CC'].replace('\\','/') + "\n")
            cfgmakefile.write("CXX=" + bc.getCompiler().cdef['CXX'].replace('\\','/') + "\n")
        cfgmakefile.write("CFLAGS="+bc.getBuildParams().cflags.replace('\\','/')+"\n")
        cfgmakefile.write("CXXFLAGS="+bc.getBuildParams().cxxflags.replace('\\','/') +"\n")
        cfgmakefile.write("LDFLAGS=\n")
        for subBCName,subBCObject in bc.getSubBC().iteritems():
            cfgmakefile.write(subBCName.upper() + '_CC=' + subBCObject.getCompiler().cdef['CC'].replace('\\','/') + '\n')
            cfgmakefile.write(subBCName.upper() + '_CXX=' + subBCObject.getCompiler().cdef['CXX'].replace('\\','/') + '\n')
            cfgmakefile.write(subBCName.upper() + '_CFLAGS = ' + subBCObject.getBuildParams().cflags.replace('\\','/') + '\n')
            cfgmakefile.write(subBCName.upper() + '_CXXFLAGS = ' + subBCObject.getBuildParams().cxxflags.replace('\\','/') + '\n')
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
        if addInc == "":
            localAddInc = "(nil)"
        else:
            localAddInc = addInc
        cfgmakefile.write("ADDINC=" + localAddInc + "\n")
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
            sourceDependencyName = ctx2_common.winPathToMsys(sourceDependency)
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
            sourceFileName = ctx2_common.winPathToMsys(sourceFile)
            makefile.write(" $(CYGPREFIX)" + sourceFileName)
    makefile.write("\n")
    for library in librarySources.keys():
        for sourceDependency in librarySources[library]:
            sourceDependencyName = ctx2_common.winPathToMsys(sourceDependency)
            basePath, ext = posixpath.splitext(sourceDependencyName)
            makefile.write("$(CYGPREFIX)$(OBJDIR)/" + posixpath.basename(basePath) + objSuffix + ": $(CYGPREFIX)" + sourceDependencyName + "\n")
            makefile.write("\tRAW_SRC=$@;SRC_NOPREFIX=$${FOO#/};DRIVE=$${SRC_NOPREFIX%%/*};UNC_SRC=$${DRIVE}:/$${SRC_NOPREFIX#*/};")
            makefile.write("OUTPUT=\"$<\";export CYGWIN=nodosfilewarning;SOURCEFILE=\"$*\";OBJFILE=\"$${SOURCEFILE%.*}\"" + objSuffix + ";makedepend -f-")
            makefile.write(" -I" + ctx2_common.privIncPathForSourceFile(sourceDependencyName) + " -I\"$(ADDINC)\" -I\"$(LINKHEADERS)\" $< 2>/dev/null | sed \"s,.*:,\\$$(OBJDIR)/$${SOURCEFILE##*/}" + objSuffix + ":,\" > $(DEPDIR)/$${OUTPUT##*/}.d\n")
# -e '/^C:/d'
            if sourceDependencyName.count("/sub_bc/") > 0:
                if sourceDependencyName[-len(subCxxFileSuffix):] == subCxxFileSuffix:
                    subCommandLine = "\t" + subCcCommandLine
                else:
                    subCommandLine = "\t" + subCxxCommandLine

                subCommandLine = subCommandLine.replace("%INCPATHS", subIncPrefix + "$(ADDINC)" + subIncSuffix + " " + subIncPrefix + ctx2_common.privIncPathForSourceFile(sourceDependencyName) + subIncSuffix + " " + subIncPrefix + "$(LINKHEADERS)" + subIncSuffix)
                subCommandLine = subCommandLine.replace('%CPPDEFINES','$(SUB_PREP_DEFS)')
                makefile.write(subCommandLine)
            else:
                if sourceDependencyName[-len(cxxFileSuffix):] == cxxFileSuffix:
                    commandLine = "\t" + ccCommandLine
                else:
                    commandLine = "\t" + ccCommandLine

                commandLine = commandLine.replace("%INCPATHS", incPrefix + "$(ADDINC)" + incSuffix + " " + incPrefix + ctx2_common.privIncPathForSourceFile(sourceDependencyName) + incSuffix + " " + incPrefix + "$(LINKHEADERS)" + incSuffix)
                commandLine = commandLine.replace("%CPPDEFINES","$(PREP_DEFS)")
                makefile.write(commandLine)
            makefile.write("\n")

    makefile.write("-include \"$(DEPDIR)\"/*.d\n")
    makefile.write("\n")

    makefile.close()

def genMakefile(outputDir = str(), viewDir = str(), envFile = str(), bcFile = str(), buildItems = list(), buildTests = False, linkHeaders = False, assignCC = False, addInc = str()):
    launch_path = posixpath.abspath('.')
    view_dir = ctx2_common.get_view_dir(viewDir)
    obj_dir = view_dir + os.sep + '.ctx/obj'

    envLayout = None
    oldEnv = None

    contexo_config_path = posixpath.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
    cfgFile = ctx_cfg.CFGFile( contexo_config_path )
    if envFile != "":
        envLayout = ctx_envswitch.EnvironmentLayout(cfgFile, envFile)
        oldEnv = ctx_envswitch.switchEnvironment(envLayout, True)

    cview = ctx_view.CTXView(view_dir, validate=False)
    bc = ctx2_common.getBuildConfiguration(cview, bcFile, cfgFile)

    comps = ctx2_common.expand_list_files(cview, buildItems)

    components = list()
    modules = list()
    components = ctx2_common.create_components(comps, cview.getItemPaths('comp'), obj_dir, launch_path)
    for comp in components:
        for library, compModules in comp.libraries.items():
            modules.extend(compModules)

    librarySources, includes = ctx2_common.parseComps(cview, view_dir, buildTests, bc, components)

    if linkHeaders:
        dest = 'output' + os.sep + 'linkheaders'
        ctx2_common.linkIncludes(includes, dest, view_dir)

    writeMakefile(librarySources = librarySources, includes = includes, linkHeaders = linkHeaders, bc = bc, viewDir = view_dir, assignCC = assignCC, addInc = addInc)

    if envFile != "":
        switchEnvironment(oldEnv, False)

main(sys.argv)


