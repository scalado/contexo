###############################################################################
#                                                                             #
#   ctx_cmod.py                                                               #
#   Component of Contexo Core - (c) Scalado AB 2007                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Classes and functions for Contexo code modules.                           #
#                                                                             #
###############################################################################

import os
import sys
import string
import shutil
import config
import ctx_log
import ctx_base
from ctx_common import *

#
# Current Contexo module structure.
# Note: This can be dinamically created using XML in the future.
#
contexo_dirname     = 'contexo'
src_dirname         = 'src'
inc_dirname         = 'inc'
output_dirname      = 'output'
test_dirname        = 'test'
dep_filename        = 'depends'
xdep_filename       = 'xdepends'
srclist_filename    = 'sourcefiles'

criteriaDirs = ['contexo','doc','inc', 'src', 'test']


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
        errorMessage( "Can't find module '" + modName + "'", "resolveModuleLocation")
        infoMessage( "Attempted following locations:", 0 )
        for loc in tried:
            infoMessage( '  %s'%loc, 0 )
        ctxExit( 1 )
    else:
        return new_path

#------------------------------------------------------------------------------
def isContexoCodeModule( path ):

    if not os.path.exists(path):
        return False

    for d in criteriaDirs:
        if not os.path.exists( os.path.join( path, d) ):
            return False

    return True


#------------------------------------------------------------------------------
def assertValidContexoCodeModule( path, msgSender ):

    if not os.path.exists(path):
        userErrorExit( "Unable to locate code module '%s'"%(path), msgSender )

    for d in criteriaDirs:
        if not os.path.exists( os.path.join( path, d) ):
            userErrorExit( "'%s' was found but is not a valid Contexo code module"%(path), msgSender )


def getSourcesFromDir( self, srcDir ):
    srcList = list ()
    ctxAssert( os.path.exists(srcDir), 'Directory was assumed to exist' )
    source_extensions = [ '.c', '.cpp']

    # Collect all source files.
    dirlist = os.listdir( srcDir )
    for file in dirlist:
        if os.path.isfile( os.path.join(srcDir, file) ):
            root, ext = os.path.splitext( file )
            if source_extensions.count( ext ) != 0:
                srcList.append(file)
    return srcList


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
    # the path to it by querying the system configuration.
    #
    # The constructor aborts execution with an error if the path doesn't
    # qualify as a code module when passing it to isContexoCodeModule().
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __init__( self, moduleRoot, pathlist = None, buildUnitTests = False ):
        self.modName        = str()
        self.modRoot        = str()
        self.srcFiles       = list()
        self.testSrcFiles   = list()
        self.pubHeaders     = list()
        self.privHeaders    = list()
        self.msgSender      = 'CTXRawCodeModule'
        self.buildUnitTests = buildUnitTests

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
            self.srcFiles = getSourcesFromDir( self, srcDir )

        return self.srcFiles

    def getTestSourceFilenames(self):
        if len(self.testSrcFiles) == 0:
            srcDir = self.getTestDir()
            self.testSrcFiles = getSourcesFromDir( self, srcDir )

        return self.testSrcFiles

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPrivHeaderFilenames(self):
        # update if list is empty.
        if len( self.privHeaders ) == 0:
            ### Assemble private header files
            header_extensions = [ '.h',]
            # Determine the path to the private header directory of the module.
            privHdrDir = self.getPrivHeaderDir()
            ctxAssert( os.path.exists(privHdrDir), 'Directory was assumed to exist' )
            # Collect all source files.
            dirlist = os.listdir( privHdrDir )
            for file in dirlist:
                if os.path.isfile( os.path.join(privHdrDir, file) ):
                    root, ext = os.path.splitext( file )
                    if header_extensions.count( ext ) != 0:
                        self.privHeaders.append(file)
        return self.privHeaders

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getPubHeaderFilenames(self):
        # update if list is empty.
        if len(self.pubHeaders) == 0:
            ### Assemble public header files
            header_extensions = [ '.h',]
            # Determine the path to the private header directory of the module.
            pubHdrDir = self.getPubHeaderDir()
            ctxAssert( os.path.exists(pubHdrDir), 'Directory was assumed to exist' )
            # Collect all source files.
            dirlist = os.listdir( pubHdrDir )
            for file in dirlist:
                if os.path.isfile( os.path.join(pubHdrDir, file) ):
                    root, ext = os.path.splitext( file )
                    if header_extensions.count( ext ) != 0:
                        self.pubHeaders.append(file)
        return self.pubHeaders

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
    def getOutputDir(self):
        return os.path.join( self.modRoot, output_dirname )
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
    def __init__( self, moduleRoot, pathlist = None, buildUnitTests = False, forceRebuild = False  ):
        CTXRawCodeModule.__init__( self, moduleRoot, pathlist, buildUnitTests )
        self.moduleTag     = str()
        self.buildParams   = ctx_base.CTXBuildParams()
        self.srcCollection = ctx_base.CTXSourceCollection()
        self.testSrcCollection = ctx_base.CTXSourceCollection()
        self.buildDir      = str()
        self.rebuildAll    = forceRebuild
        self.msgSender     = 'CTXCodeModule'

        #

        srcList = self.getSourceFilenames()
        for name in srcList:
            self.srcCollection.addSource( os.path.join(self.getSourceDir(), name) )

        srcList = self.getTestSourceFilenames()
        for name in srcList:
            self.testSrcCollection.addSource ( os.path.join(self.getTestDir(), name) )

        self.moduleTag     = 'COMPILING_MOD_' + string.upper( self.getName() )
        self.buildParams.prepDefines.append( self.moduleTag )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Assembles a list of include directories based on the dependency
    # declaration in the given module. All paths in the depend_paths list is
    # searched and the first matching module is used.
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __resolveModuleDepends( self, modpath, depend_paths ):

        print "DEPRECATED FUNCTION: ", "__resolveModuleDepends"

        include_paths = list()

        ctxAssert( os.path.exists(modpath), 'Module path should be resolved at this point' )

        # Convert dependency paths to list if only single string is given

        if type(depend_paths) == str:
            depend_paths = [depend_paths,]

        #
        ## Do some input error checks.
        #

        for depend_path in depend_paths:
            if not os.path.exists( depend_path ):
                userErrorExit( "Can't find dependency search path '" + depend_path + "'", self.msgSender )


        #
        ## Add the module's own include directory to list of include paths.
        #

        inc_subdir = os.path.join( modpath, inc_dirname )
        if not os.path.exists( inc_subdir ):
            userErrorExit( "Invalid Contexo module, can't find 'inc' subdirectory '" + inc_subdir + "'", self.msgSender )

        include_paths.append( inc_subdir )

        #
        ## Add the module's root directory to list of include paths, so it may use the public header.
        #

        modroot = modpath
        if not os.path.exists( modroot ):
            userErrorExit( "Internal failure to locate root of module. This may be a bug.", self.msgSender )

        include_paths.append( modroot )

        #
        ## Determine the path to the contexo directory of the module.
        #

        contexo_subdir = os.path.join( modpath, contexo_dirname )

        if not os.path.exists( contexo_subdir ):
            userErrorExit( "Invalid Contexo module, can't find 'contexo' subdirectory '" + contexo_subdir + "'", self.msgSender )

        #
        ## Locate dependency declaration file, and parse it if found.
        #

        dep_filepath = os.path.join( contexo_subdir, dep_filename )

        if os.path.exists( dep_filepath ):
            dep_modules = readLstFile( dep_filepath )
            for dep_module in dep_modules:
                for depend_path in depend_paths:
                    include_path_candidate = os.path.join( depend_path, dep_module )
                    if os.path.exists( include_path_candidate ):
                        include_paths.append( include_path_candidate )
                        break
        else:
            infoMessage( "WARNING: No module dependency file (depends) found in module '%s'"%modpath, 2 )

        return include_paths

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

                xdep_not_found = True

                include_path_candidates = None

                xdep_val = os.environ.get (xdep_var, '')

                if xdep_val != '':
                    include_path_candidates = xdep_val
                    include_path_candidates = include_path_candidates.split( os.pathsep )
                    xdep_not_found = False

                if include_path_candidates == None:
                    warningMessage( "Cannot resolve item '%s' specified in '%s'"%( xdep_var, xdep_filepath), self.msgSender )

                include_path_candidates = assureList( include_path_candidates )

                for cand in include_path_candidates:
                    # Remove trailing backslash and add quotes around it.
                    cand = cand.strip('\"')
                    cand = cand.rstrip('\\')

                    if not os.path.exists( cand ):
                        userErrorExit( "Cannot find dependency location '%s' resolved from '%s'."%(cand, xdep_var), self.msgSender )

                    #cand = '\"' + cand + '\"'
                    include_paths.append( cand )
        else:
            infoMessage( "Module %s has no external depenencies."%self.getName(), 4, self.msgSender )

        return include_paths

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addBuildParams( self, buildParams ):
        self.buildParams.add( buildParams )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def forceRebuild( self ):
        self.rebuildAll = True

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def buildStaticObjects( self, session, dependPaths, buildDir = None ):
        #LOG
        ctx_log.ctxlogBeginCodeModule( self.getName() )

        infoMessage( "Building module '%s'"%(self.getName()), 2 )
        
        tempBuildParams = ctx_base.CTXBuildParams()

        #
        # TODO: Resolve external dependencies. This is not in line with modern contexo... ehh.. line.
        # resolveExternalDeps still uses the old config

        xdepends = assureList( self.resolveExternalDeps() )
        if len(xdepends) != 0:
            # We curently can't detect modifications on external dependencies.
            self.forceRebuild()

            tempBuildParams.incPaths.extend( xdepends )

        #
        # Retrieve module depend paths from the build session object.
        #

        tempBuildParams.incPaths.extend( assureList( session.getModIncludePaths(self.getName()) ) )

        #
        # Output dependencies on high verbose level.
        #

        infoMessage( "Dependency paths for module '%s':"%self.getName(), 4)
        for path in tempBuildParams.incPaths:
            infoMessage( "  - %s"%path, 4 )

        #
        # Handle output directory settings
        #

        outputDir = self.getOutputDir()
        if buildDir != None:
            outputDir = os.path.join( outputDir, buildDir )
            if not os.path.exists( outputDir ):
                os.makedirs( outputDir )

        joinedBuildParams = ctx_base.CTXBuildParams()
        joinedBuildParams.add( self.buildParams )
        joinedBuildParams.add( tempBuildParams )

        #
        # Build the source collection of this module.
        #

        objlist = session.buildStaticObjects( self.srcCollection, outputDir, joinedBuildParams, self.rebuildAll )

        if self.buildUnitTests:
            objlist.extend ( session.buildStaticObjects( self.testSrcCollection, outputDir, joinedBuildParams, self.rebuildAll ) )


        #LOG
        for obj in objlist:
            ctx_log.ctxlogAddObjectFile( obj.filename, os.path.basename(obj.source) )

        #LOG
        ctx_log.ctxlogEndCodeModule()

        return objlist

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def clean( self, buildDir = None ):
        imDirs = list()
        outputDir = self.getOutputDir()

        if buildDir == None:
            imDirs = os.listdir( outputDir )
        else:
            imDirs = [buildDir,]

        for imDir in imDirs:

            if imDir == '.svn':
                continue

            imPath = os.path.join( outputDir, imDir )

            if os.path.exists( imPath ):
                infoMessage( "Removing %s"%imPath, 2 )
                if os.path.isfile(imPath):
                    os.remove( imPath )
                else:
                    shutil.rmtree( imPath )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getSourceCollection(self):
        return self.srcCollection
