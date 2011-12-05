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
import ctx_view
import ctx_cfg
import ctx_envswitch
import ctx_common
import ctx_comp
import ctx_sysinfo
import ctx_cmod
import ctx_base
import ctx_envswitch

exearg = False
buildTests = False
linkHeaders = False
exe = str()
assignCC = True
buildItems = list()
envFile = str()
viewDir = str()

def parseArgs():
    nextArgIsEnv = False
    nextArgIsBC = False
    nextArgIsViewDir = False
    parsedAllOptions = False

    for arg in sys.argv:
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

logging.basicConfig(format = '%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S',
                                level = logging.DEBUG);

def dir_has_rspec(view_dir):
    view_filelist = os.listdir(view_dir)
    for entry in view_filelist:
        if entry.endswith('.rspec'):
            return True
    return False

def getBuildConfiguration(cview, args):
    import ctx_bc
    import ctx_config

    if args.bconf != None:
        bcFile = args.bconf
    else:
        if CTX_DEFAULT_BCONF != None:
            infoMessage("Using default build configuration '%s'"%(CTX_DEFAULT_BCONF), 2)
            bcFile = CTX_DEFAULT_BCONF
        else:
            logging.userErrorExit("No build configuration specified.")

    bcFilePath = cview.locateItem(bcFile, 'bconf')
    bcFilename = os.path.basename(bcFilePath)
    bcPath = os.path.dirname(bcFilePath)

    bcDict = ctx_config.CTXConfig(bcFilePath)
    section = bcDict.get_section('config')
    if not section.has_key('CDEF'):
        logging.userErrorExit("Mandatory BC option 'CDEF' is missing.")

    cdefFilename = section['CDEF']
    cdefFilePath = cview.locateItem(cdefFilename, 'cdef')
    cdefPath = os.path.dirname(cdefFilePath)
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
        comp = ctx_base.COMPFile(comp_file = compFilename, component_paths = componentPaths, globalOutputDir = objDir, launchPath = launchPath)
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
 
def cmd_export(viewDir = str(), envFile = str(), buildItems = list()):
    launch_path = os.path.abspath('.')
    view_dir = get_view_dir(viewDir)
    obj_dir = view_dir + os.sep + '.ctx/obj'

    envLayout = None
    oldEnv = None
    if envFile != "":
        envLayout = ctx_envswitch.EnvironmentLayout(cfgFile, envFile)
        oldEnv = ctx_envswitch.switchEnvironment(envLayout, True)

    cview = ctx_view.CTXView(view_dir, validate=False)
    bc = getBuildConfiguration(cview, args)

    comps = expand_list_files(cview, buildItems)

    components = list()
    modules = list()
    components = create_components(comps, cview.getItemPaths('comp'), obj_dir, launch_path)
    for comp in components:
        for library, compModules in comp.libraries.items():
            modules.extend(compModules)
    print modules

    if envFile != "":
        switchEnvironment(oldEnv, False)

cmd_export(viewDir = viewDir, envFile = envFile, comps = comps)


