###############################################################################
#                                                                             #
#   ctx_comp.py                                                               #
#   Component of Contexo Shell - (c) Scalado AB 2006                          #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#   License GPL v2. See LICENSE.txt.                                          #
#   ------------                                                              #
#                                                                             #
#   Handles the COMP format.                                                  #
#                                                                             #
#   Support:                                                                  #
#                                                                             #
#   20061101 - COMP format version 1                                          #
#                                                                             #
###############################################################################

import os
import shutil
#import sys
#import string
import config
import ctx_base
import ctx_log
import ctx_cmod
from ctx_common import *

output_dir         = str()
verbose_level      = 1
std_depends        = True
clean              = False
comp_files         = list()
bc_files           = list()

compsec_meta       = dict()
compsec_general    = dict()
compsec_libraries  = dict()
compsec_export     = dict()

comp_result        = {'TITLE':str(), 'DESCRIPTION':str(), 'NAME':str(), 'LIBRARIES':dict(), 'PUBLIC_HEADERS':list() }

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class COMPFile:
    def __init__( self, compFilePath, comp_paths):
        self.displayTitle    = str()
        self.description     = str()
        self.name            = str()
        self.libraries       = dict() # Dictionary where each key is a library name accessing a list of code module names.
        self.publicHeaders   = list()
        self.path            = compFilePath
        self.buildParams     = ctx_base.CTXBuildParams()
        self.msgSender       = 'COMPFile'
        self.moduleCache     = list()
        self.staticObjects   = dict() # The most recently built static objects, arranged under the library they produce.
        #

        self.__resolveCompFileLocation(comp_paths)
        self.__processCompFile()

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   Resolves the location of the comp file by searching in the given paths 
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def __resolveCompFileLocation( self,  comp_paths ):

        tried       = list()

        #
        # append extension if omitted by user.
        #

        if self.path[-5:].lower() != '.comp':
            self.path += '.comp'

        #
        # First try at calling location
        #

        candidate = os.path.abspath( self.path )
        if os.path.exists( candidate ):
            self.path = candidate
            return
        else:
            tried.append( candidate )

        #
        # Now try in system variable
        #

        if type(comp_paths) != list:
            comp_paths = [comp_paths,]

        for path in comp_paths:
            candidate = os.path.join( path, self.path )
            if os.path.exists( candidate ):
                self.path = candidate
                return
            else:
                tried.append( candidate )


        #
        # If we reach this point we have tried everything we can and failed.
        #

        errorMessage("COMP file '%s' not found."%self.path)
        infoMessage("Attempted following locations:", 0)
        for loc in tried:
            infoMessage('  %s'%loc, 0)
        ctxExit( 1 )



    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   Processes a single COMP file.
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def __processCompFile( self ):

        compsec_meta        = dict()
        compsec_general     = dict()
        compsec_libraries   = dict()
        #compsec_export      = dict()

        #
        ## Load Config sections from the COMP file.
        #

        compfile_path = self.path
        cfg = config.Config( compfile_path )

        #
        ## Go through existing sections.
        #

        cur_section = 'meta'
        if cfg.has_section( cur_section ):
            compsec_meta  = cfg.get_section( cur_section  )

        cur_section = 'general'
        if cfg.has_section( cur_section ):
            compsec_general  = cfg.get_section( cur_section  )
        else:
            errorMessage("Missing mandatory COMP section: %s"%cur_section)
            ctxExit(1)

        cur_section = 'libraries'
        if cfg.has_section( cur_section ):
            compsec_libraries  = cfg.get_section( cur_section  )
        else:
            error_output( "Missing mandatory COMP section: %s"%cur_section, 'COMPFile' )
            ctxExit(1)

        cur_section = 'exports'
        if cfg.has_section( cur_section ):
            compsec_exports  = cfg.get_section( cur_section  )

        #
        ## Extract options.
        #

        cur_option = 'TITLE'
        if compsec_meta.has_key( cur_option ):
            self.displayTitle = compsec_meta[cur_option]
        else:
            # Use component file-title if no name is set in meta section
            self.displayTitle = os.path.splitext(os.path.basename( self.path ))[0]

        cur_option = 'DESCRIPTION'
        if compsec_meta.has_key( cur_option ):
            self.description = compsec_meta[cur_option]

        cur_option = 'NAME'
        if compsec_general.has_key( cur_option ):
            self.name = compsec_general[cur_option]
        else:
            error_output( "Missing mandatory COMP option: %s"%cur_option, 'COMPFile' )
            ctxExit(1)

        cur_option = 'PUBLIC_HEADERS'
        if compsec_exports.has_key( cur_option ):
            self.publicHeaders = compsec_exports[cur_option]
            if type(self.publicHeaders) != list:
                self.publicHeaders = [self.publicHeaders,]

            # Expand lst files in public header list
            self.publicHeaders = expandLstFilesInList( self.publicHeaders, self.msgSender, os.path.dirname(compfile_path) )

        # Handle libraries section specially

        if len(compsec_libraries) == 0:
            userErrorExit("No library entries given in component definition.")

        libdict = compsec_libraries

        for libtitle in libdict.keys():
            if not type(libdict[libtitle]) is list:
                libdict[libtitle] = [libdict[libtitle], ]

            # Expand lst files
            libdict[libtitle] = expandLstFilesInList( libdict[libtitle], self.msgSender, os.path.dirname(compfile_path) )

        self.libraries = libdict

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __syncModuleCache( self ):
        if len(self.moduleCache) == 0:
            for library, modules in self.libraries.items():
                for module in modules:
                    cm = ctx_cmod.CTXCodeModule( module, pathlist = None, buildUnitTests = False, forceRebuild = False )
                    cm.addBuildParams( self.buildParams )
                    self.moduleCache.append( cm )


    def copyPublicHeaderFiles( self, dependPaths, outputPath, headerDir, nameAsSubDir ):

        #libPath       = outputPath
        headerPath    = outputPath

        if dependPaths == None:
            dependPaths = list()

        #
        # Verify and create all output directories
        #

        if not os.path.exists(outputPath):
            os.makedirs( outputPath )

        if headerDir != None and len(headerDir) != 0:
            headerPath = os.path.join( outputPath, headerDir )
        if not os.path.exists( headerPath ):
            os.makedirs( headerPath )



        #
        # Build code modules for each library. We also take the opportunity to
        # gather the paths to all public headers of all code modules built and map
        # them to the name of the public header. This will make accessing them
        # for exports much faster later on.
        #

        publicHeaderMap    = dict()

        for library, modules in self.libraries.items():

            #LOG
            ctx_log.ctxlogBeginLibrary( library )

            self.staticObjects[library] = list()

            for module in modules:
                cm = ctx_cmod.CTXCodeModule( module, pathlist = None, buildUnitTests = False, forceRebuild = False )
                cm.addBuildParams( self.buildParams )
                self.moduleCache.append( cm )

                # map module name to its root directory
                pubHeaders = os.listdir( cm.getRootPath() )
                for header in pubHeaders:
                    pubHeaderPath = os.path.join( cm.getRootPath(), header )
                    if os.path.isfile( pubHeaderPath ):
                        publicHeaderMap[header] = pubHeaderPath

            #LOG
            ctx_log.ctxlogEndLibrary()

        #
        # Produce all component libraries
        #

        #
        # Export public headers.
        #

        for publicHeader in self.publicHeaders:
            if publicHeader not in publicHeaderMap.keys():
                userErrorExit("Can't find public header '%s' for export."%publicHeader)

            src = publicHeaderMap[publicHeader]
            dst = os.path.join( headerPath, publicHeader )

            shutil.copyfile( src, dst )

            #LOG
            ctx_log.ctxlogAddExportHeader( os.path.basename(dst) )

        # LOG
        ctx_log.ctxlogEndComponent()

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def __cleanModule( self, codeModule, imDirs ):
        if len(imDirs) == 0:
            codeModule.clean()
        else:
            for imDir in imDirs:
                codeModule.clean( imDir )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def clean( self, bc = list() ):

        imDirsToClean  = list()

        self.__syncModuleCache()

        if type(bc) != list:
            imDirsToClean.append( bc.getTitle() )
        else:
            for bcfile in bc:
                imDirsToClean.append( bcfile.getTitle() )

        for module in self.moduleCache:
            self.__cleanModule( module, imDirsToClean )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def addBuildParams( self, buildParams ):
        self.buildParams.add( buildParams )

        # Empty module cache.
        self.moduleCache = list()
