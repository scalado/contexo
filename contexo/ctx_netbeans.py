#!/usr/bin/python
###############################################################################
#                                                                             #
#   ctx_netbeans.py                                                           #
#   Component of Contexo Core - (c) Scalado AB 2010                           #
#                                                                             #
#   Author: Johannes Strömberg (johannes.stromberg@scalado.com)               #
#           Thomas Eriksson    (thomas.eriksson@scalado.com)                  #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Helper functions for the Netbeans export plugin: nbproj.py                #
#                                                                             #
###############################################################################
# -*- coding: utf-8 -*-

import os.path
import os
import ntpath
from xmltools import XMLGenerator
import uuid

def relntpath(path, start):
    import ntpath #the windows version of os.path #available in python 2.6
#    return ntpath.relpath(path,  start)
    if start == None:
        start = os.getcwd()
    path = ntpath.normpath(path)
    start = ntpath.normpath(start)

    (drivep,  tailp) = ntpath.splitdrive(path)
    (drives,  tails) = ntpath.splitdrive(start)
    #if one of the paths has no drive letter, treat both of them so
    if (drivep == '' or drives == ''):
        path = tailp
        start = tails
    elif(drivep != drives):
        #ntpath.relpath returns error if drive letters differ, but we wont
        return path

    pathl  = path.replace("/", "\\").split('\\')
    startl = start.replace("/", "\\").split('\\')
    #print "path: %s, start:%s"%(path, start )
    while len(pathl) and len(startl) and pathl[0] == startl[0]:
            #print "removing "+pathl[0]
            del pathl[0]
            del startl[0]
    for i in range(len(startl)):
        pathl.insert(0, '..')

    return ntpath.join('.',  *pathl).replace("\\","/")

def make_libConfigurations(projectName, cflags, prepDefs, codeModules, outLib,
                    do_tests,  incPaths, projPath):
    
    from xml.etree import cElementTree as ET
    
    projPath = os.path.abspath(projPath)
    baseDir = os.path.join(projPath,projectName)
    outPath = os.path.join(baseDir,"nbproject")
    fileTitle = projectName
    
    if not os.path.isdir(outPath):
        os.makedirs(outPath)

    projFilePath  = os.path.join( outPath, "configurations.xml" )
    projFile      = open( projFilePath, 'w')

    #
    # Determine exe/lib
    #
    configurationTypeNbr = '0'

    project = ET.Element('configurationDescriptor',version = '69')

    rootFolder = ET.SubElement(project,'logicalFolder', name = "root", displayName = "root" , projectFiles = "true")

    lastfoldername = None
    for foldername, mod in codeModules:
        if foldername.strip() == "":
            rootFolder2 = rootFolder
        elif foldername != lastfoldername:
            lastfoldername = foldername
            rootFolder2 = ET.SubElement(rootFolder,'logicalFolder', name = foldername, displayName = foldername, projectFiles = "true")
        
        modFolder = ET.SubElement(rootFolder2, 'logicalFolder', name = mod['MODNAME'], displayName = mod['MODNAME'], projectFiles = "true")
        
        # Add all source files.
        srcFolder = ET.SubElement(modFolder,'logicalFolder', name = 'src', displayName = 'src', projectFiles = "true")
        for srcFile in mod['SOURCES']:
            ET.SubElement(srcFolder,'itemPath').text = relntpath(srcFile, baseDir)
            
        # Add private header files.
        hdrFolder = ET.SubElement(modFolder,'logicalFolder', name = 'inc', displayName = 'inc', projectFiles = "true")
        for incFile in mod['PRIVHDRS']:
            ET.SubElement(hdrFolder,'itemPath').text = relntpath(incFile, baseDir)
        
        if do_tests:
            srcFolder = ET.SubElement(modFolder,'logicalFolder', name = 'tests', displayName = 'tests', projectFiles = "true")
            for srcFile in mod['TESTSOURCES']:
                ET.SubElement(srcFolder,'itemPath').text = relntpath(srcFile, baseDir)

            for hdrFile in mod['TESTHDRS']:
                ET.SubElement(srcFolder,'itemPath').text = relntpath(srcFile, baseDir)
        
        # Add public headers to root.
        for hdrFile in mod['PUBHDRS']:
            ET.SubElement(modFolder,'itemPath').text = relntpath(hdrFile, baseDir)
    
    ET.SubElement(project,"projectmakefile").text = "Makefile"
    
    ## Configurations
    confs = ET.SubElement(project,"confs")

    #debug conf
    
    conf = ET.SubElement(confs,'conf',name = "Debug", type = '3')
    
    toolsSet = ET.SubElement(conf,'toolsSet')
    ET.SubElement(toolsSet,'developmentServer').text = 'localhost'
    ET.SubElement(toolsSet,'compilerSet').text = 'MinGW|MinGW'
    ET.SubElement(toolsSet,'platform').text = '3'
    
    compileType = ET.SubElement(conf,'compileType')
                
    cTool = ET.SubElement(compileType,'cTool')
    
    incDir = ET.SubElement(cTool,'incDir')
    for hdrDir in incPaths:
        ET.SubElement(incDir,'pElem').text = hdrDir
    
    if prepDefs:
        preprocessorList = ET.SubElement(cTool,'preprocessorList')
        for prepDef in prepDefs:
            ET.SubElement(preprocessorList,'Elem').text = prepDef
    
    ET.SubElement(conf,'archiverTool')
    
    # source dependencies
    
    for foldername, mod in codeModules:
        
        for srcFile in mod['SOURCES']:
            item = ET.SubElement(conf,'item', path = relntpath(srcFile, baseDir), ex = 'false', tool = '0')
            cTool = ET.SubElement(item,'cTool')
            incDir = ET.SubElement(cTool,'incDir')
            ET.SubElement(incDir,"pElem").text = relntpath(mod['PRIVHDRDIR'], baseDir)
            for hdrdir in mod['DEPHDRDIRS']:
                ET.SubElement(incDir,"pElem").text = relntpath(hdrdir, baseDir)
                
            if do_tests:
                for srcFile in mod['TESTSOURCES']:
                    item = ET.SubElement(conf,'item', path = relntpath(srcFile, baseDir), ex = 'false', tool = '0')
                    cTool = ET.SubElement(item,'cTool')
                    incDir = ET.SubElement(cTool,'incDir')
                    ET.SubElement(incDir,"pElem").text = relntpath(mod['PRIVHDRDIR'], baseDir)
                    for hdrdir in mod['DEPHDRDIRS']:
                        ET.SubElement(incDir,"pElem").text = relntpath(hdrdir, baseDir)
    
    #release conf
    
    conf = ET.SubElement(confs,'conf',name = "Release", type = '3')
    
    toolsSet = ET.SubElement(conf,'toolsSet')
    ET.SubElement(toolsSet,'developmentServer').text = 'localhost'
    ET.SubElement(toolsSet,'compilerSet').text = 'MinGW|MinGW'
    ET.SubElement(toolsSet,'platform').text = '3'
    
    compileType = ET.SubElement(conf,'compileType')
                
    cTool = ET.SubElement(compileType,'cTool')
    
    ET.SubElement(cTool,'developmentMode').text = "5"
    
    if prepDefs:
        preprocessorList = ET.SubElement(cTool,'preprocessorList')
        for prepDef in prepDefs:
            ET.SubElement(preprocessorList,'Elem').text = prepDef
    
    ET.SubElement(conf,'archiverTool')
    
    # source dependencies
    
    for foldername, mod in codeModules:
        for srcFile in mod['SOURCES']:
            item = ET.SubElement(conf,'item', path = relntpath(srcFile, baseDir), ex = 'false', tool = '0')
            cTool = ET.SubElement(item,'cTool')
            incDir = ET.SubElement(cTool,'incDir')
            ET.SubElement(incDir,"pElem").text = relntpath(mod['PRIVHDRDIR'], baseDir)
            for hdrdir in mod['DEPHDRDIRS']:
                ET.SubElement(incDir,"pElem").text = relntpath(hdrdir, baseDir)
                
    ET.ElementTree(project).write(projFile,'utf-8')
    
    projFile.close()

def make_libProject( projectName, cflags, prepDefs, codeModules, outLib,
                    do_tests,  incPaths, projPath):
    
    from xml.etree import cElementTree as ET

    projPath = os.path.abspath(projPath)
    outPath = os.path.join(projPath,projectName,"nbproject")
    fileTitle = projectName
    
    if not os.path.isdir(outPath):
        os.makedirs(outPath)

    projFilePath  = os.path.join( outPath, "project.xml" )
    projFile      = open( projFilePath, 'w')

    #
    # Determine exe/lib
    #
    configurationTypeNbr = '0'

    project = ET.Element('project',xmlns = 'http://www.netbeans.org/ns/project/1')
    
    ET.SubElement(project,'type').text = 'org.netbeans.modules.cnd.makeproject'
    
    configuration = ET.SubElement(project,'configuration')
    
    data = ET.SubElement(configuration,'data',xmlns = 'http://www.netbeans.org/ns/make-project/1')

    ET.SubElement(data,'name').text = projectName
    ET.SubElement(data,'make-project-type').text = '0'
    ET.SubElement(data,'c-extensions').text = 'c'
    ET.SubElement(data,'cpp-extensions')
    ET.SubElement(data,'header-extensions').text = 'h'
    ET.SubElement(data,'sourceEncoding').text = 'UTF-8'
    ET.SubElement(data,'make-dep-projects')
    ET.SubElement(data,'sourceRootList')
    confList = ET.SubElement(data,'confList')
    ET.SubElement(confList,'confElem').text = "Debug"
    ET.SubElement(confList,'confElem').text = "Release"

    ET.ElementTree(project).write(projFile,'utf-8')
    
    projFile.close()
    

def make_libproj( projectName, cflags, prepDefs, codeModules, outLib,
                    do_tests,  incPaths, projPath):
    make_libConfigurations( projectName, cflags, prepDefs, codeModules, outLib,
                            do_tests,  incPaths, projPath )
    
    make_libProject( projectName, cflags, prepDefs, codeModules, outLib,
                            do_tests,  incPaths, projPath )
    
    projPath = os.path.abspath(projPath)
    outPath = os.path.join(projPath,projectName)
    projFilePath  = os.path.join( outPath, "Makefile" )
    projFile      = open( projFilePath, 'w')
    projFile.write(makeFile)
    projFile.close()
    
makeFile = """#
#  There exist several targets which are by default empty and which can be 
#  used for execution of your targets. These targets are usually executed 
#  before and after some main targets. They are: 
#
#     .build-pre:              called before 'build' target
#     .build-post:             called after 'build' target
#     .clean-pre:              called before 'clean' target
#     .clean-post:             called after 'clean' target
#     .clobber-pre:            called before 'clobber' target
#     .clobber-post:           called after 'clobber' target
#     .all-pre:                called before 'all' target
#     .all-post:               called after 'all' target
#     .help-pre:               called before 'help' target
#     .help-post:              called after 'help' target
#
#  Targets beginning with '.' are not intended to be called on their own.
#
#  Main targets can be executed directly, and they are:
#  
#     build                    build a specific configuration
#     clean                    remove built files from a configuration
#     clobber                  remove all built files
#     all                      build all configurations
#     help                     print help mesage
#  
#  Targets .build-impl, .clean-impl, .clobber-impl, .all-impl, and
#  .help-impl are implemented in nbproject/makefile-impl.mk.
#
#  Available make variables:
#
#     CND_BASEDIR                base directory for relative paths
#     CND_DISTDIR                default top distribution directory (build artifacts)
#     CND_BUILDDIR               default top build directory (object files, ...)
#     CONF                       name of current configuration
#     CND_PLATFORM_${CONF}       platform name (current configuration)
#     CND_ARTIFACT_DIR_${CONF}   directory of build artifact (current configuration)
#     CND_ARTIFACT_NAME_${CONF}  name of build artifact (current configuration)
#     CND_ARTIFACT_PATH_${CONF}  path to build artifact (current configuration)
#     CND_PACKAGE_DIR_${CONF}    directory of package (current configuration)
#     CND_PACKAGE_NAME_${CONF}   name of package (current configuration)
#     CND_PACKAGE_PATH_${CONF}   path to package (current configuration)
#
# NOCDDL


# Environment 
MKDIR=mkdir
CP=cp
CCADMIN=CCadmin
RANLIB=ranlib


# build
build: .build-post

.build-pre:
# Add your pre 'build' code here...

.build-post: .build-impl
# Add your post 'build' code here...


# clean
clean: .clean-post

.clean-pre:
# Add your pre 'clean' code here...

.clean-post: .clean-impl
# Add your post 'clean' code here...


# clobber
clobber: .clobber-post

.clobber-pre:
# Add your pre 'clobber' code here...

.clobber-post: .clobber-impl
# Add your post 'clobber' code here...


# all
all: .all-post

.all-pre:
# Add your pre 'all' code here...

.all-post: .all-impl
# Add your post 'all' code here...


# help
help: .help-post

.help-pre:
# Add your pre 'help' code here...

.help-post: .help-impl
# Add your post 'help' code here...



# include project implementation makefile
include nbproject/Makefile-impl.mk

# include project make variables
include nbproject/Makefile-variables.mk
"""
