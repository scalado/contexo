import os.path
###############################################################################
#                                                                             #
#   ctx_cmod.py                                                               #
#   Component of Contexo Core - (c) Scalado AB 2010                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   Modified by: Thomas Eriksson (thomas.eriksson@scalado.com)                #
#   ------------                                                              #
#                                                                             #
#   Classes and functions for Contexo code modules.                           #
#                                                                             #
###############################################################################

import os
#import sys
import string
import shutil
import ctx_log
import ctx_base
from ctx_common import *

#
# In earlier releases of Contexo, a contexo module was defined by a set of
# directories:
# "criteria dirs" ("src", "inc", "doc", "contexo", "test").
# This does not work well in practice since some popular version control systems
# such as git, hg and perforce does not support empty directories, and since we
# want old code to build
# the definition of a contexo module must change to:
#
# A directory which MUST reside in a module path as defined by <ctx-path ...>.
# Furthermore, such a directory MUST contain either:
# 1. One or more public header files.
# OR
# 2. One or more of the criteria dirs.
#
# (obviously when migrating to $popular_version_control system, no empty
# directories would be kept, so a spiffy recursive script putting placeholders
# all over the code base would not suffice in case we ever would like to check out
# an old revision)
#

contexo_dirname     = 'contexo'
src_dirname         = 'src'
inc_dirname         = 'inc'
doc_dirname			= 'doc'
output_dirname      = 'output'
test_dirname        = 'test'
xdep_filename       = 'xdepends'
srclist_filename    = 'sourcefiles'
unresolvedXdepends  = set()
criteriaDirs = [contexo_dirname, 'doc', inc_dirname, src_dirname, test_dirname]

#------------------------------------------------------------------------------
def resolveModuleLocation( modName, pathlist ):
    tried = [modName,]

    new_path   = str()

    for path in pathlist:
        candidate_path = os.path.join( path, modName )
        tried.append(candidate_path)

        if os.path.exists(candidate_path):
            new_path = candidate_path
            break

    if len(new_path) == 0:
        errorMessage("Can't find module '" + modName + "'")
        infoMessage("Attempted following locations:", 0)
        for loc in tried:
            infoMessage('  %s'%loc, 0)
        ctxExit( 1 )
    else:
        return new_path

def getSourceDir( baseDir ):
    return baseDir + os.sep + src_dirname

def getTestDir( baseDir ):
    return baseDir + os.sep + test_dirname

def getPrivHeaderDir(baseDir):
    return baseDir + inc_dirname

def getPubHeaderDir(baseDir):
    return baseDir 

#------------------------------------------------------------------------------
def isContexoCodeModule( path ):

    if not os.path.exists(path):
        return False

    if not os.path.isdir( path ):
	return False

    numPublicHeaderFiles = 0
    for entry in os.listdir( path ):
	entrypath = os.path.join( path, entry)
	if os.path.isfile( entrypath ) and ( entrypath.endswith('.h') or entrypath.endswith('.H') or entrypath.endswith('.hpp') ):
	    numPublicHeaderFiles+=1

    numCriteriaDirs = 0
    for d in criteriaDirs:
	criteriaDirPath = os.path.join( path, d)
        if os.path.isfile( criteriaDirPath ):
            userErrorExit("'%s' was found but is not a valid Contexo code module"%(path))
	    return False
	
	if os.path.isdir( criteriaDirPath ):
	    numCriteriaDirs+=1
    if numPublicHeaderFiles > 0 or numCriteriaDirs > 0:
        return True

    return False


#------------------------------------------------------------------------------
def assertValidContexoCodeModule( path, msgSender ):

    if not isContexoCodeModule( path ):
        userErrorExit("'%s' was found but is not a valid Contexo code module"%(path))

def getPubHeadersFromDir(pubHdrDir):
    pubHeaders = list()
    header_extensions = [ '.h','.hpp',]
    if os.path.exists( pubHdrDir ):
        dirlist = os.listdir( pubHdrDir )
        for entry in dirlist:
            if os.path.isfile( pubHdrDir + os.sep + entry ):
                root, ext = os.path.splitext( entry )
                if header_extensions.count( ext ) != 0:
                    pubHeaders.append(entry)
    return pubHeaders

def getPrivHeadersFromDir(privHdrDir):
    privHeaders = list()
    header_extensions = [ '.h','.hpp',]
    if os.path.exists(privHdrDir):
        dirlist = os.listdir(privHdrDir)
        for entry in dirlist:
            if os.path.isfile(privHdrDir + os.sep + entry):
                root, ext = os.path.splitext( entry )
                if header_extensions.count(ext) != 0:
                    privHeaders.append(entry)
    return privHeaders

def getInlSourcesFromDir(inlSrcDir):
    inlSources = list()
    header_extensions = [ '.inl',]
    if os.path.exists( inlSrcDir ):
        dirlist = os.listdir( inlSrcDir )
        for entry in dirlist:
            if os.path.isfile( inlSrcDir + os.sep + entry ):
                root, ext = os.path.splitext( entry )
                if header_extensions.count( ext ) != 0:
                    inlSources.append(entry)
    return inlSources

def getSourcesFromDir( srcDir, archPath, subBCDict ):
    srcListDict = dict()
    objListDict = dict()
    # 'bc name': list()
    subBCListDict = dict()
    srcList = list ()
    objList = list()
    if not os.path.exists(srcDir):
	srcList = list()
	return srcList, objList,subBCListDict
    source_extensions = [ '.c', '.cpp']

    # Collect all source files.
    dirlist = os.listdir( srcDir )
    for entry in dirlist:
        if os.path.isfile( os.path.join(srcDir, entry) ):
            fileRoot, ext = os.path.splitext( entry )
            if source_extensions.count( ext ) != 0:
                baseFileName = os.path.basename(fileRoot)
                srcListDict[baseFileName] = entry
    
    archPathCopy = archPath[:]
    # thus we must reverse the list so the values with highest precedence
    # overrides earlier values
    archPathCopy.reverse()
    # override source files with architecture specific files
    arch_spec_source_extensions = [ '.c', '.cpp', '.asm', '.s']
    obj_file_extensions = [ '.o', '.obj']
    arch_srcDir = os.path.join(srcDir, 'arch')
    for archRelDirBase in archPathCopy:
        archRelDir = os.path.join(arch_srcDir, archRelDirBase )
        if os.path.isdir(archRelDir):
            archDirList = os.listdir( os.path.join(arch_srcDir, archRelDir ))
            for archDirEntry in archDirList:
                archFile = os.path.join(archRelDir, archDirEntry)
                if os.path.isfile( archFile ):
                    baseFileName, ext = os.path.splitext( archDirEntry )
                    if arch_spec_source_extensions.count( ext ) != 0:
                        for key in srcListDict.keys():
                            if key == baseFileName:
                                msg = 'Overriding source file '+os.path.join(srcDir, srcListDict[baseFileName])+' with architecture specific file: '+archFile
                                infoMessage(msg, 1)
                        srcListDict[baseFileName] = archFile[len(srcDir)+1:]
                    if obj_file_extensions.count( ext ) != 0:
                        for key in srcListDict.keys():
                            if key == baseFileName:
                                msg = 'Overriding source file '+os.path.join(srcDir, srcListDict[baseFileName])+' with prebuilt object file: '+ archFile
                                infoMessage(msg, 1)
                        srcListDict.pop(baseFileName)
                        # making object files a "first class citizen" in the dependency manager would mean that we'd have to add a whole lot of functions and extra stuff just to support object files which aren't used or referenced by any other source file anyway.
                        # TODO: If more languages are added to contexo in the future, this may need a cleanup.
                        # for now, bypass the dependency manager and add an absolute path directly
                        objListDict[baseFileName] = os.path.join( srcDir, archFile[len(srcDir)+1:])

    subBC_dir = os.path.join(srcDir, 'sub_bc')
    if os.path.isdir(subBC_dir):
        for subBC in os.listdir(subBC_dir):
	    subBCEntry = srcDir + os.sep + 'sub_bc' + os.sep + subBC
            if os.path.isdir(subBCEntry) and subBCDict.keys().count( subBC ) > 0:
                for subBC_sourceFile in os.listdir(subBCEntry):
                    baseFileName, ext = os.path.splitext( subBC_sourceFile )
                    # we accept assembly here
                    if arch_spec_source_extensions.count( ext ) > 0:
                        for key in srcListDict.keys():
                            if key == baseFileName:
                                msg = 'Overriding source file '+os.path.join(srcDir, srcListDict[baseFileName])+' with build configuration specific file: '+subBC_sourceFile + '. Specific build configuration: ' + subBCEntry + '.bc'
                                infoMessage(msg, 1)
                        srcListDict[baseFileName] = subBCEntry[len(srcDir)+1:] + os.sep + subBC_sourceFile
                        if not subBCListDict.has_key(subBC):
                            subBCListDict[subBC] = list()
                        
                        subBCListDict[subBC].append(subBCEntry + os.sep + subBC_sourceFile)

    for srcFile in srcListDict.values():
        srcList.append(srcFile)
    for objFile in objListDict.values():
        objList.append(objFile)
    return srcList,objList,subBCListDict


#------------------------------------------------------------------------------
# The representation of a raw code module is built around its directories
# only, without any complex resolve operations or settings for build operations
# etc.
#
# This class is recommended to use as a slimmed time efficient alternative to
# CTXCodeModule when the outline and contents of a code module needs to be
# queried or analyzed and time.
#
# This class is extended by CTXCodeModule.
#------------------------------------------------------------------------------
class CTXRawCodeModule:

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Initializes the object with all aspects of the code module. If the
    # moduleRoot argument can't be located as it is, the constructor assumes
    # that it specifies the pure name of the module and then tries to locate
    # the path to it by querying the system configuration. - NOT TRUE
    #
    # The constructor aborts execution with an error if the path doesn't
    # qualify as a code module when passing it to isContexoCodeModule().
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __init__( self, moduleRoot, pathlist = None, buildUnitTests = False ,archPath = list(), legacyCompilingMod = False, outputDir = None, bc = None):
        self.modName        = str()
        self.modRoot        = str()
        self.srcFiles       = list()
        self.prebuiltObjFiles = list()
        self.subBCSrcDict = dict()
        self.testSrcFiles   = list()
        self.testObjFiles   = list()
        self.pubHeaders     = list()
        self.testHeaders    = list()
        self.privHeaders    = list()
        self.msgSender      = 'CTXRawCodeModule'
        self.buildUnitTests = buildUnitTests
        self.archPath       = archPath
        self.legacyCompilingMod = legacyCompilingMod
        self.bc             = bc
	self.subBC          = bc.getSubBC()
        # TODO: cmod should not know about output dir, nor how to build itself. This data dependency should be removed in the future
        self.globalOutputDir = outputDir

        assert( os.path.isabs(moduleRoot) )
        moduleRoot = os.path.normpath(moduleRoot)
        if not os.path.exists(moduleRoot):
            self.modRoot = resolveModuleLocation( moduleRoot, pathlist )
        else:
            self.modRoot = moduleRoot

        assertValidContexoCodeModule( self.modRoot, self.msgSender )


        #
        # Now we're in the clear, get all module data/info.
        #

        self.modName = os.path.basename( self.modRoot );
        ctxAssert( os.path.exists(self.modRoot), 'Module path should be resolved at this point' )

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getName(self):
        return self.modName
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getRootPath(self):
        return self.modRoot
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getSourceFilenames(self):

        if len(self.srcFiles) == 0:
            srcDir = self.getSourceDir()
            self.srcFiles, self.prebuiltObjFiles, self.subBCSrcDict = getSourcesFromDir( srcDir, self.archPath, self.subBC )
        return self.srcFiles

    def getPreBuiltObjectFilenames(self):

        if len(self.srcFiles) == 0 or len(self.prebuiltObjFiles) == 0:
            srcDir = self.getSourceDir()
            self.srcFiles, self.prebuiltObjFiles,self.subBCSrcDict = getSourcesFromDir( srcDir, self.archPath, self.subBC )
        return self.prebuiltObjFiles

    def getSubBCSources(self):
        if len(self.subBCSrcDict) == 0 or len(self.prebuiltObjFiles) == 0:
            srcDir = self.getSourceDir()
            self.srcFiles, self.prebuiltObjFiles,self.subBCSrcDict = getSourcesFromDir( srcDir, self.archPath, self.subBC )
        return self.subBCSrcDict


    def getPreBuiltObjectAbsolutePaths(self):
        import functools
        return map ( functools.partial( os.path.join,  self.getSourceDir() ),  self.getPreBuiltObjectFilenames() )
 
    def getSourceAbsolutePaths(self):
        import functools
        #functional magic - bind an argument to join and map this bound function to filenames
        return map ( functools.partial( os.path.join,  self.getSourceDir() ),  self.getSourceFilenames() )

    def getTestSourceAbsolutePaths(self):
        import functools
        return map ( functools.partial( os.path.join,  self.getTestDir() ),  self.getTestSourceFilenames() )

    def getTestHeaderAbsolutePaths(self):
        import functools
        return map ( functools.partial( os.path.join,  self.getTestDir() ),  self.getTestHeaderFilenames() )

    def getTestSourceFilenames(self):
        if len(self.testSrcFiles) == 0:
            srcDir = self.getTestDir()
            self.testSrcFiles, self.testObjFiles,self.subBCSrcDict = getSourcesFromDir( srcDir, self.archPath, self.subBC )
        return self.testSrcFiles

    def getTestHeaderFilenames(self):
        # update if list is empty.
        if len(self.testHeaders) == 0:
            ### Assemble public header files
            header_extensions = [ '.h', '.hpp',]
            # Determine the path to the private header directory of the module.
            testHdrDir = self.getTestDir()
            #testHeaders = list( )
            if not os.path.exists( testHdrDir ):
		    return self.testHeaders
            # Collect all source files.
            dirlist = os.listdir( testHdrDir )
            for file in dirlist:
                if os.path.isfile( os.path.join(testHdrDir, file) ):
                    root, ext = os.path.splitext( file )
                    if header_extensions.count( ext ) != 0:
                        self.testHeaders.append(file)
        return self.testHeaders

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPrivHeaderFilenames(self):
        # update if list is empty.
        if len( self.privHeaders ) == 0:
            ### Assemble private header files
            header_extensions = [ '.h', '.hpp',]
            # Determine the path to the private header directory of the module.
            privHdrDir = self.getPrivHeaderDir()
	    if not os.path.exists( privHdrDir ):
	        return self.privHeaders
            # Collect all source files.
            dirlist = os.listdir( privHdrDir )
            for file in dirlist:
                if os.path.isfile( os.path.join(privHdrDir, file) ):
                    root, ext = os.path.splitext( file )
                    if header_extensions.count( ext ) != 0:
                        self.privHeaders.append(file)
        return self.privHeaders

    def getPrivHeaderAbsolutePaths(self):
        import functools
        return map ( functools.partial( os.path.join,  self.getPrivHeaderDir() ),  self.getPrivHeaderFilenames() )

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPubHeaderFilenames(self):
        if len(self.pubHeaders) == 0:
            header_extensions = [ '.h','.hpp',]
            pubHdrDir = self.getPubHeaderDir()
	    if not os.path.exists( pubHdrDir ):
	        return self.pubHeaders
            dirlist = os.listdir( pubHdrDir )
            for file in dirlist:
                if os.path.isfile( os.path.join(pubHdrDir, file) ):
                    root, ext = os.path.splitext( file )
                    if header_extensions.count( ext ) != 0:
                        self.pubHeaders.append(file)
        return self.pubHeaders

    def getPubHeaderAbsolutePaths(self):
        import functools
        return map ( functools.partial( os.path.join,  self.getPubHeaderDir() ),  self.getPubHeaderFilenames() )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getContexoDir( self ):
        return os.path.join( self.modRoot, contexo_dirname )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getSourceDir( self ):
        return os.path.join( self.modRoot, src_dirname )

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getTestDir( self ):
        return os.path.join( self.modRoot, test_dirname )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPrivHeaderDir(self):
        return os.path.join( self.modRoot, inc_dirname )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPubHeaderDir(self):
        return self.modRoot
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getDocDir(self):
        return os.path.join( self.modRoot, doc_dirname )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	# TODO: cmod should not know about output dir, nor how to build itself. This data dependency should be removed in the future
    def getOutputDir(self):
        return self.globalOutputDir
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def hasExternalDependencies( self ):
        xdepends_file = os.path.join( self.getContexoDir(), 'xdepends' )
        return os.path.exists( xdepends_file )

#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
class CTXCodeModule( CTXRawCodeModule ):

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __init__( self, moduleRoot, pathlist = None, buildUnitTests = False, forceRebuild = False, archPath = list(), legacyCompilingMod = False, outputDir = None, bc = None ):
        outputDir_ = outputDir
        CTXRawCodeModule.__init__( self, moduleRoot, pathlist, buildUnitTests, archPath, False, outputDir_, bc = bc )
        self.moduleTag     = str()
        self.buildParams   = ctx_base.CTXBuildParams()
        self.buildDir      = str()
        self.rebuildAll    = forceRebuild
        self.msgSender     = 'CTXCodeModule'
        self.legacyCompilingMod = legacyCompilingMod
	self.bc             = bc
	self.subBC          = bc.getSubBC()

        # TODO: cmod should not know about output dir, nor how to build itself. This data dependency should be removed in the future
        self.globalOutputDir = outputDir

        # the preprocessor define COMPILING_MOD_ is a legacy definition,
        # initially created to make sure private headers were not included in a project.
        # today this makes no sense since contexo keeps track of private and public headers, it can also be problematic when some build systems (eg. Visual Studio 2005) have limits on the number of preprocessor defines passed on to it.
        # to build legacy code, and to activate this legacy code path, append the option --legacy-compiling-mod to the contexo tool in use
        if self.legacyCompilingMod:
            self.moduleTag     = 'COMPILING_MOD_' + string.upper( self.getName() )
            self.buildParams.prepDefines.append( self.moduleTag )



    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def resolveExternalDeps( self ):

        include_paths = list()

        #
        ## Locate external dependencies declaration file, and parse it if found.
        #

        xdep_filepath = os.path.join( self.getContexoDir(), xdep_filename )

        if os.path.exists( xdep_filepath ):
            xdep_vars = readLstFile( xdep_filepath )

            # We now have a list of environment variables or config option names.
            # Resolve each of them and append to the include paths.

            for xdep_var in xdep_vars:

                #xdep_not_found = True

                include_path_candidates = None

                xdep_val = os.environ.get (xdep_var, '')

                if xdep_val != '':
                    include_path_candidates = xdep_val
                    include_path_candidates = include_path_candidates.split( os.pathsep )
                    #xdep_not_found = False

                if include_path_candidates == None:
                    if xdep_var not in unresolvedXdepends:
                        unresolvedXdepends.add(xdep_var)
                        warningMessage("Cannot resolve item '%s' specified in '%s', ignoring further occurances."%( xdep_var, xdep_filepath))

                include_path_candidates = assureList( include_path_candidates )

                for cand in include_path_candidates:
                    # Remove trailing backslash and add quotes around it.
                    cand = cand.strip('\"')
                    cand = cand.rstrip('\\')

                    if not os.path.exists( cand ):
                        userErrorExit("Cannot find dependency location '%s' resolved from '%s'."%(cand, xdep_var))

                    #cand = '\"' + cand + '\"'
                    include_paths.append( cand )
        else:
            infoMessage("Module %s has no external depenencies."%self.getName(), 5)

        return include_paths

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: unused
    def addBuildParams( self, buildParams ):
        self.buildParams.add( buildParams )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def forceRebuild( self ):
        self.rebuildAll = True

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def buildStaticObjects( self, session, buildDir = None ):
        #LOG
        ctx_log.ctxlogBeginCodeModule( self.getName() )

        infoMessage("Building module '%s'"%(self.getName()), 2)

        buildParams = ctx_base.CTXBuildParams()
        buildParams.add( self.buildParams )

        # TODO: external dependencies must be revisited.
        xdepends = assureList( self.resolveExternalDeps() )
        if len(xdepends) != 0:
	    # assume that external dependencies never change, otherwise we get forced rebuilds whenever we've got external dependencies
	    ## contexo detects changes in the file xdepends elsewere
            #self.forceRebuild()
            buildParams.incPaths.extend( xdepends )

        #
        # Handle output directory settings
        #

        outputDir = self.getOutputDir()
        if buildDir != None:
            outputDir = os.path.join( outputDir, buildDir )
            if not os.path.exists( outputDir ):
                os.makedirs( outputDir )

        #
        # Build sources for this module.
        #
        srcFiles = self.getSourceAbsolutePaths()
        if self.buildUnitTests:
            srcFiles.extend( self.getTestSourceAbsolutePaths() )
    
        subBCSrcFiles = self.getSubBCSources()

        objlist = list()
        for src in srcFiles:
            bc = self.bc

            for srcList in subBCSrcFiles.values():
                if src in srcList:
                    for subBCSrc in srcList:
                        subBCName = os.path.basename(os.path.dirname(subBCSrc))
                        bc = self.subBC[subBCName]
            obj = session.buildStaticObject( os.path.normpath( src ), os.path.normpath( outputDir ), bc, self.rebuildAll )
            objlist.append( obj )
 
        for prebuiltObjectFile in self.prebuiltObjFiles:
            obj = session.copyPrebuiltObject( os.path.normpath( prebuiltObjectFile), outputDir)
            objlist.append( obj)
        #LOG
        for obj in objlist:
            ctx_log.ctxlogAddObjectFile( obj.filename, os.path.basename(obj.source) )

        #LOG
        ctx_log.ctxlogEndCodeModule()

        return objlist

