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
import tempfile
import logging
import logging.handlers
import os
import os.path
import sys
import shutil
import platform
import posixpath
import subprocess

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
    buildItems = list()
    envFile = ""
    bcFile = ""
    addInc = ""
    outputDir = ""
    outputFile = ""
    outputName = ""
    inputName = ""
    viewDir = ""
    nextArgIsBC = False

    linkHeaders = True

    nextArgIsInputName = False
    nextArgIsOutputName = False
    nextArgIsOutputFile = False

    parsedAllOptions = False
    firstArg = True

    for arg in argv:
        if firstArg:
            firstArg = False
            continue
        if arg == '-h':
            print >>sys.stderr, 'help:'
            print >>sys.stderr, '-b <BCFILE>, .bc file to use'
            print >>sys.stderr, '-in <INPUT_NAME>, input name'
            print >>sys.stderr, '-on <OUTPUT_NAME>, output name'
            print >>sys.stderr, '-o <OUTPUT_FILE>, resulting output file'
            sys.exit(1)
        if nextArgIsOutputName:
            outputName = arg
            nextArgIsOutputName = False
            continue
        if nextArgIsBC:
            bcFile = arg
            nextArgIsBC = False
            continue
        if nextArgIsInputName:
            inputName = arg
            nextArgIsInputName = False
            continue
        if nextArgIsOutputFile:
            outputFile = arg
            nextArgIsOutputFile = False
            continue
        if not parsedAllOptions:
            if arg == '-on':
                nextArgIsOutputName = True
                continue
            if arg == '-in':
                nextArgIsInputName = True
                continue
            if arg == '-o':
                nextArgIsOutputFile = True
                continue
            if arg == '-b':
                nextArgIsBC = True
                continue
            parsedAllOptions = True
        if outputFile == "":
            print >>sys.stderr, 'must have \'-o\' argument'
            sys.exit(1)
        if bcFile == "":
           print >>sys.stderr, 'must have -b argument'
           sys.exit(1)

        if outputName == "":
            print >>sys.stderr, 'must have \'-on\' argument'
            sys.exit(1)

        if inputName == "":
            print >>sys.stderr, 'must have \'-in\' argument'
            sys.exit(1)

        if arg[-5:] != ".comp" and arg[0] != '@':
            print >>sys.stderr, 'arguments must be either comp(s) or listfile(s) containing comp(s)'
            sys.exit(1)
        buildItems.append(arg)
    if len(buildItems) == 0:
        print >>sys.stderr, 'must have at least one listfile or comp file as argument'
        sys.exit(1)
    argDict = dict()

    genTengilFile(outputFile = outputFile, viewDir = viewDir, outputName = outputName, inputName = inputName, buildItems = buildItems, bcFile = bcFile)

logging.basicConfig(format = '%(asctime)s %(levelname)-8s %(message)s',
                                datefmt='%H:%M:%S',
                                level = logging.DEBUG);

def genTengilFile(outputFile = str(), viewDir = str(), outputName = str(), inputName = str(), buildItems = list(), bcFile = str()):
    launch_path = posixpath.abspath('.')
    view_dir = ctx2_common.get_view_dir(viewDir)
    obj_dir = view_dir + os.sep + '.ctx/obj'

    envLayout = None
    oldEnv = None

    contexo_config_path = posixpath.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
    cfgFile = ctx_cfg.CFGFile( contexo_config_path )

    cview = ctx_view.CTXView(view_dir, validate=False)
    bc = ctx2_common.getBuildConfiguration(cview, bcFile, cfgFile)

    comps = ctx2_common.expand_list_files(cview, buildItems)

    components = list()
    modules = list()
    components = ctx2_common.create_components(comps, cview.getItemPaths('comp'), obj_dir, launch_path)
    for comp in components:
        for library, compModules in comp.libraries.items():
            modules.extend(compModules)

    buildTests = True
    librarySources, includes = ctx2_common.parseComps(cview, view_dir, buildTests, bc, components)
    tempdir = tempfile.mkdtemp(prefix='ctx2tengil')

    for file in includes:
        shutil.copy(file, tempdir)
    for sources in librarySources.values():
        for file in sources:
            shutil.copy(file, tempdir)

    args = " ".join(['grep', '-h', inputName, tempdir + os.sep + '*',  '|', 'grep', '-v', '"#define"' + '>', outputFile])
    print args
    if subprocess.call(args, shell=True) != 0:
        sys.exit()
    
    args = " ".join(['sed', '-i', 's/' + inputName + '/' + outputName + '/g', outputFile])
    print args
    if subprocess.Popen(args, shell=True) != 0:
        sys.exit()
 
    shutil.rmtree(tempdir)

main(sys.argv)


