###############################################################################
#                                                                             #
#   ctx_bc.py                                                                 #
#   Component of Contexo Shell - (c) Scalado AB 2006                          #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Handler classes for the BC format.                                        #
#                                                                             #
#   Support:                                                                  #
#                                                                             #
#   20061101 - BC format version 1                                            #
#                                                                             #
###############################################################################

import os
#import sys
import string
#import shutil
import config
#import platform.ctx_platform
from ctx_common import *
from ctx_base import *

#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
class BCFile:

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def __init__( self, bcFilename, bcFilePaths, cdefPaths, cfgFile ):
        self.path            = str()
        self.buildParams     = CTXBuildParams()
        self.bcTitle         = str()
        self.bcDescription   = str()
        self.dbgmode         = bool
        self.dbgmodeMemory   = bool
        self.dbgmodeFile     = bool
        self.charEncoding    = str()
        self.byteOrder       = str()
        self.cdefPath        = str()
        self.cdef            = str()
        self.compiler        = None
        self.msgSender       = 'BCFile'
        self.archPath        = list()
        #

        bcFilePaths = assureList( bcFilePaths )
        cdefPaths = assureList( cdefPaths )

        self.__resolveBCFileLocation( bcFilename, cfgFile, bcFilePaths )
        self.__process_bc( self.path, cfgFile, cdefPaths ) #TODO: __process_bc needs to be run before __updateBuildParams
        self.__updateBuildParams()
        self.compiler = CTXCompiler( os.path.join( self.cdefPath, self.cdef ) )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #   Resolves the location of the BC file by searching in the paths given
    #   by the system config variable CONTEXO_BC_PATHS.
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def __resolveBCFileLocation( self, bcFilename, cfgFile, bcFilePaths ):

        tried       = list()

        #
        # append extension if omitted by user.
        #

        if bcFilename[-3:].lower() != '.bc':
            bcFilename += '.bc'

        #
        # Try at each of the candidate locations provided to the constructor, then
        # try at calling location and last in config variable.
        #

        bcFilePaths.append( os.getcwd() )

        configBCPaths = cfgFile.getBConfPaths()
        if type(configBCPaths) != list:
            configBCPaths = [configBCPaths,]
        bcFilePaths.extend( configBCPaths )

        for pathCandidate in bcFilePaths:
            candidate = os.path.join( pathCandidate, bcFilename )
            infoMessage("Trying BC: %s"%(candidate), 2)
            if os.path.exists( candidate ):
                self.path = candidate
                infoMessage("Using BC: %s"%( self.path ), 1)
                return
            else:
                tried.append( candidate )

        #
        # If we reach this point we have tried everything we can and failed.
        #

        if not os.path.exists(self.path):
            userErrorExit("BC file '%s' not found."%(bcFilename))

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def __assert_correct_type( self, option, value, allowed_types ):
        option_type = type(value)
        if option_type not in allowed_types:
            userErrorExit("Option '%s' has illegal type (%s)"%(option, option_type))

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def __updateBuildParams( self ):

        # Update debug related parameters
        if self.dbgmode == True:
            self.buildParams.prepDefines.append( '_DEBUG' )
            self.buildParams.prepDefines.append( 'SCB_DEBUG' )
            self.buildParams.prepDefines.append( 'SCB_DBC' )

            if self.dbgmodeMemory == True:
                self.buildParams.prepDefines.append( 'SCB_DBGMODE_MEMORY' )
                self.buildParams.prepDefines.append( 'SCB_TLS' )

            if self.dbgmodeFile == True:
                self.buildParams.prepDefines.append( 'SCB_DBGMODE_FILE' )

        # Update byte order
        if self.byteOrder == 'LITTLE_ENDIAN':
            self.buildParams.prepDefines.append('BYTE_ORDER_LITTLE_ENDIAN')
        elif self.byteOrder == 'BIG_ENDIAN':
            self.buildParams.prepDefines.append('BYTE_ORDER_BIG_ENDIAN')
        else:
            errorMessage("Invalid byte order: %s"%self.byteOrder)
            ctxExit(1)

        # Update char encoding
        if self.charEncoding == 'ASCII':
            self.buildParams.prepDefines.append( 'SCB_CHARENC_ASCII' )
        elif self.charEncoding == 'UTF16':
            self.buildParams.prepDefines.append( 'SCB_CHARENC_UTF16' )
            self.buildParams.prepDefines.append( 'SCB_UNICODE' )
            self.buildParams.prepDefines.append( '_UNICODE' )
            self.buildParams.prepDefines.append( 'UNICODE' )
        else:
            errorMessage("Unknown character encoding: %s"%self.charEncoding)
            ctxExit(1)




    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def __process_bc( self, bcFilePath, cfgFile, cdefPaths ):

#        msgSender    = 'BCFile'
        option_name  = str()
        bcsec_meta   = dict()
        bcsec_config = dict()
        illegal_title_chars = ['&',]

        cfg = config.Config( bcFilePath )

        if cfg.has_section( 'meta' ):
            bcsec_meta  = cfg.get_section( 'meta'  )

        if cfg.has_section( 'config' ):
            bcsec_config = cfg.get_section( 'config'  )


        #
        #
        ## Process 'meta' section. ---------------------------
        #
        #

        if len(bcsec_meta) == 0:
            pass # This is not a mandatory section.
        else:

            # BC description

            option_name = 'DESCRIPTION'

            if bcsec_meta.has_key( option_name ):
                self.bcDescription = bcsec_meta[ option_name ]

            self.__assert_correct_type( option_name, self.bcDescription, [str,] )

            # BC title

            option_name = 'TITLE'

            if bcsec_meta.has_key( option_name ):
                self.bcTitle = bcsec_meta[ option_name ]
                for char in illegal_title_chars:
                    if self.bcTitle.find(char) != -1:
                        userErrorExit("Illegal character '%s' found in BC title '%s'"%(char,self.bcTitle))

                self.bcTitle = self.bcTitle.replace( ' ', '_' )

            self.__assert_correct_type( option_name, self.bcTitle, [str,] )

        #
        #
        ## Process 'config' section. ---------------------------
        #
        #

        section = bcsec_config
        if len(section) == 0:
            userErrorExit("Mandatory BC section '%s' is missing."%('config'))

        #
        # Compiler definition
        #

        option_name = 'CDEF'

        if not section.has_key( option_name ):
            userErrorExit("Mandatory BC option '%s' is missing."%option_name)

        self.cdef = section[ option_name ]

        configCDefPaths = cfgFile.getCDefPaths()
        if type(configCDefPaths) != list:
            configCDefPaths = [configCDefPaths,]

        if len(cfgFile.getCDefPaths()) != 0:
            cdefPaths.extend( configCDefPaths )

        if section.has_key( 'CDEF_PATH' ):
            warningMessage("BC/BConf section 'CDEF_PATH' is deprecated and may produce unexpected results when working with views and RSpecs")
            cdefPaths.append( section['CDEF_PATH'] )

        tried_cdefs = list()
        for pathCandidate in cdefPaths:
            candidate = os.path.join( pathCandidate, self.cdef )
            infoMessage("Trying CDEF: %s"%(candidate), 2)
            if os.path.exists( candidate ):
                self.cdefPath = pathCandidate
                infoMessage("Using CDEF: %s"%( candidate ), 1)
                break
            else:
                tried_cdefs.append( candidate )

        if not os.path.exists( os.path.join( self.cdefPath, self.cdef) ):
            userErrorExit("CDEF file '%s' not found. Attempted following locations:\n  %s"%(self.cdef, string.join(tried_cdefs, '\n  ')))


        # Notes:
        #
        # If DEBUG_BUILD option is omitted, no further debug options can be specified.
        # In this case both DEBUGMODE_MEMORY and DEBUGMODE_MEMORY are set to false.
        #
        # If DEBUG_BUILD is set to NO, any further specified debug options are discarded (warning displayed).
        #
        #

        if not section.has_key( 'DEBUG_BUILD' ):

            if section.has_key( 'DEBUGMODE_MEMORY' ):
                userErrorExit("Option '%s' requires option '%s' to be set."%('DEBUGMODE_MEMORY', 'DEBUG_BUILD'))

            if section.has_key( 'DEBUGMODE_FILE' ):
                userErrorExit("Option '%s' requires option '%s' to be set."%('DEBUGMODE_FILE', 'DEBUG_BUILD'))

            section[ 'DEBUG_BUILD'      ]   = False
            section[ 'DEBUGMODE_MEMORY' ]   = False
            section[ 'DEBUGMODE_FILE'   ]   = False

        else:

            if section['DEBUG_BUILD'] is False:

                if not section.has_key( 'DEBUGMODE_MEMORY' ):
                    section['DEBUGMODE_MEMORY'] = False

                if not section.has_key( 'DEBUGMODE_FILE' ):
                    section['DEBUGMODE_FILE'] = False


        self.dbgmode         = section[ 'DEBUG_BUILD'      ]
        self.dbgmodeMemory   = section[ 'DEBUGMODE_MEMORY' ]
        self.dbgmodeFile     = section[ 'DEBUGMODE_FILE'   ]

        self.__assert_correct_type( 'DEBUG_BUILD',      self.dbgmode,       [bool,] )
        self.__assert_correct_type( 'DEBUGMODE_MEMORY', self.dbgmodeMemory, [bool,] )
        self.__assert_correct_type( 'DEBUGMODE_FILE',   self.dbgmodeFile,   [bool,] )


        #
        # Unicode
        #

        option_name = 'CHAR_ENCODING'

        if not section.has_key( option_name ):
            userErrorExit("Mandatory BC option '%s' is missing."%option_name)

        self.charEncoding = section[ option_name ]

        self.__assert_correct_type( option_name, self.charEncoding, [str,] )


        #
        # Endianess
        #

        option_name = 'BYTE_ORDER'

        if not section.has_key( option_name ):
            userErrorExit("Mandatory BC option '%s' is missing."%option_name)

        if section[option_name] != 'LITTLE_ENDIAN' and section[option_name] != 'BIG_ENDIAN':
            userErrorExit("BC option '%s' must be set to either 'LITTLE_ENDIAN' or 'BIG_ENDIAN'"%option_name)

        self.byteOrder = section[ option_name ]

        self.__assert_correct_type( option_name, self.byteOrder, [str,] )

        #
		# ARCH_PATH
		#

        ## ARCH_PATH specifies a path with architecture specific files
		## its implementation was motivated by the need to include specific asm
        ## (.s) files because of bugs in GCC, which attributed to so many lines
        ## of assembly that it wasn't feasable to write compiler specific
        ## inlined assembler for each compiler.
		## additionally arch specific .c files may be placed here too
		## Since several architectures can share some arch specific code,
        ## several arch specific directories may be specified, and
        ## separated by ';'.
		## By not forcing a naming convention on the architectures future 
        ## architecture specific code will be simple to support without modifing
        ## Contexo
		## The ARCH_PATH is relative to the [CONTEXO_MODULE]/src folder.

        option_name = 'ARCH_PATH'
        if section.has_key( option_name ):
            for pathElem in section[ option_name ]:
                self.archPath.append(pathElem)

        #
        # Colormodes
        #

        option_name = 'COLORMODES' # currently not implemented


        #
        # Additional compiler flags
        #

        option_name = 'ASMFLAGS'

        if section.has_key( option_name ):
            self.buildParams.asmflags = section[ option_name ]

        self.__assert_correct_type( option_name, self.buildParams.asmflags, [str,] )

        option_name = 'CFLAGS'

        if section.has_key( option_name ):
            self.buildParams.cflags = section[ option_name ]

        self.__assert_correct_type( option_name, self.buildParams.cflags, [str,] )


        #
        # Additional preprocessor defines
        #


        option_name = 'PREP_DEFINES'

        if section.has_key( option_name ):
            if type( section[ option_name ]) is str:
                self.buildParams.prepDefines = [ section[option_name], ]
            else:
                self.buildParams.prepDefines = section[option_name]

        self.__assert_correct_type( option_name, self.buildParams.prepDefines, [list] )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def getCompiler( self ):
        return self.compiler

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def getBuildParams( self ):
        return self.buildParams

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def getTitle( self ):
        return self.bcTitle

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - -
    def getArchPath( self ):
        return self.archPath


