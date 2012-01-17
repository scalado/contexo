#!/usr/bin/env python

###############################################################################
#                                                                             #
#   ctx2_common.py                                                            #
#   common stuff for ctx2make and ctx2tengil                                  #
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
                testSources = ctx_cmod.getSourcesFromDir(srcDir = testSourceDir, archPath = [], subBCDict = dict())
                if module in moduleDict.keys():
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
 
def linkIncludes(includes, dest, viewDir):
    for includeFile in includes:
        if not os.path.isdir(dest):
            os.makedirs(dest)
        linkFile = open(dest + os.sep + os.path.basename(includeFile), 'w')
        linkFile.write("/* Autogenerated by Contexo\n * changes to this file WILL BE LOST\n */\n")
        linkFile.write("#include \"../../" + includeFile + "\"\n\n")
        linkFile.close()

