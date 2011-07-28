###############################################################################
#                                                                             #
#   ctx_base.py                                                               #
#   Component of Contexo Core - (c) Scalado AB 2006                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Defines the foundation classes of the build system.                       #
#                                                                             #
###############################################################################
#import platform
import os
import sys
#import string
#import shutil
import ctx_config
from ctx_common import *
from ctx_log import *
#import ctx_depmgr
import hashlib
#import time

#------------------------------------------------------------------------------
# \class {CTXBuildParams}
#------------------------------------------------------------------------------
class CTXBuildParams:
    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __init__(self):
        # \member{ prepDefines }
        self.prepDefines     = list()

        # \member {asmflags}
        self.asmflags        = str()

        # \member {cflags}
        self.cflags          = str()

        # \member { incPaths }
        self.incPaths        = list()

        self.ldDirs = list()
        self.ldLibs = list()
        self.ldFlags = str()
        #

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def add( self, addParams ):
        self.prepDefines.extend(  addParams.prepDefines )
        self.cflags = "%s %s"%(self.cflags, addParams.cflags)
        self.asmflags = "%s %s"%(self.asmflags, addParams.asmflags)
        self.incPaths.extend(     addParams.incPaths )
        self.ldDirs.extend(addParams.ldDirs)
        self.ldLibs.extend(addParams.ldLibs)
        self.ldFlags = "%s %s"%(self.ldFlags,  addParams.ldFlags)

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeChecksum( self ):
        md = hashlib.md5()

        for item in self.prepDefines:
            md.update( str(item) )

        for item in self.incPaths:
            md.update( str(item) )

        for item in self.ldDirs:
            md.update( str(item) )

        for item in self.ldLibs:
            md.update( str(item) )

        md.update( self.ldFlags )
        md.update( self.cflags )
        md.update( self.asmflags )

        return md.hexdigest()

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def prepareCommandFile( commandline,  commandfileName, cdefPath ):

    marker = '%@'

    ix = commandline.find( marker )

    if ix == -1:
        # No commandfile specified.
        return commandline
    elif commandline.find( marker, ix + len(marker) ) != -1:
        # Multiple (nested) commandfiles is currently not supported.
        userErrorExit("Multiple '%s' symbols in ARCOM field is currently not supported.\n    File: %s"%(marker, cdefPath))

    #cmdfilename = time.strftime("%y%H%M%S.txt", time.localtime())
    cmdfilename = commandfileName

    # Extract the contents for the commandfile from commandline (everything superceeding the %@ symbol)
    sep = "\"\n\"" # CURRENTLY A HACK FOR IAR!
    cmdfile_contents = '"' + sep.join (commandline[ix+2:].split()) + sep;
    cmdfile_contents = cmdfile_contents.rstrip('"') # Remove the trailing quote

    # Exclude the contents we extracted from the commandline.
    commandline = commandline[0:ix+len(marker)]

    # Replace the %@ symbol with the commandfile's name
    commandline = commandline.replace( marker, cmdfilename )

    # write commandfile
    cmdfile = open( cmdfilename, 'w' )
    #cmdfile_contents = os.path.normpath(cmdfile_contents.replace('"',""))#<-new code
    cmdfile.write(cmdfile_contents)
    cmdfile.close()

    return commandline



#------------------------------------------------------------------------------
class CTXStaticObject:
    def __init__(self):
        self.source            = str
        self.filename          = str
        self.filepath          = str
        self.buildParams       = CTXBuildParams()
        self.commandline       = str

#------------------------------------------------------------------------------
class CTXCompiler:

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __init__(self, cdefPath ):
        self.cdefPath  = str()
        self.cdef      = dict()
        self.msgSender = 'CTXCompiler'
        self.cdefTitle = str()
        self.cdefDesc  = str()
        self.usingCommandfile = False
        self.stdCommandfileName = 'ctxcmdfile7363616c61646f.txt'
        self.validatedTools = list()
        #


        self.cdefPath = os.path.abspath( cdefPath )
        if not os.path.exists( self.cdefPath ):
            userErrorExit("Compiler definition '%s' not found."%self.cdefPath)

        cdef_config = ctx_config.CTXConfig( self.cdefPath )

        #
        # Read meta section
        #

        meta = cdef_config.get_section( 'meta' )
        self.cdefTitle = meta['TITLE']

        if meta.has_key('DESCRIPTION'):
            self.cdefDesc = meta['DESCRIPTION']

        #
        # Read the actual compiler setup.
        #

        self.cdef = cdef_config.get_section( 'setup' )

        cdefKeys = "LDCOM LD LDDIR LDLIB LDDIRPREFIX LDDIRSUFFIX LDLIBPREFIX CCCOM CXXCOM ASM ASMCOM AR ARCOM ARCOM_METHOD ASMCOM CC CXX ECHO_SOURCES ASMFILESUFFIX CFILESUFFIX CXXFILESUFFIX OBJSUFFIX CPPDEFPREFIX CPPDEFSUFFIX INCPREFIX INCSUFFIX LIBPREFIX LIBSUFFIX RANLIB".split()
        for key in cdefKeys:
            if self.cdef.has_key(key) and type(self.cdef[key]) is str:
                # strip quotation. Note that we only strip the outer quotations.

                if self.cdef[key][0] == '"' or self.cdef[key][0] == "'":
                    self.cdef[key] = self.cdef[key][1:]

                if self.cdef[key][-1:] == '"' or self.cdef[key][-1:] == "'":
                    self.cdef[key] = self.cdef[key][0:-1]

                #self.cdef[key] = self.cdef[key].strip('\"\'')

        #
        # Handle default values for omitted options.
        #

        option = 'ARCOM_METHOD'
        if option not in self.cdef:
            self.cdef[option] = "REPLACE"

        option = 'ECHO_SOURCES'
        if option not in self.cdef:
            self.cdef[option] = False

        option = 'ASMFILESUFFIX'
        if option not in self.cdef:
            self.cdef[option] = '.s'

        # this is sufficient for gcc, but will break on others
        option = 'ASM'
        if option not in self.cdef:
            key = 'CC'
            if not self.cdef.has_key( key ):
                userErrorExit("Missing mandatory CDEF option '%s'"%key)
            asmcom_cmdline = self.cdef[key]
            self.cdef[option] = asmcom_cmdline

        option = 'ASMCOM'
        if option not in self.cdef:
            key = 'CCCOM'
            if not self.cdef.has_key( key ):
                userErrorExit("Missing mandatory CDEF option '%s'"%key)
            asmcom_cmdline = self.cdef[key]
            asmcom_cmdline = self.cdef['CCCOM'].replace('%CC', '%ASM')
            asmcom_cmdline = asmcom_cmdline.replace('%CFLAGS', '%ASMFLAGS')
            self.cdef[option] = asmcom_cmdline

        #
        # Assert presence of mandatory options
        #

        mandatory = "CCCOM ASM ASMCOM AR ARCOM ARCOM_METHOD CC ECHO_SOURCES CFILESUFFIX OBJSUFFIX CPPDEFPREFIX CPPDEFSUFFIX INCPREFIX INCSUFFIX LIBPREFIX LIBSUFFIX".split()
        for key in mandatory:
            if not self.cdef.has_key( key ):
                userErrorExit("Missing mandatory CDEF option '%s'"%key)

        #
        # Check for unknown options (typos or backward compatibility issues)
        #

        for key, value in self.cdef.iteritems():
            if key not in cdefKeys:
                warningMessage("Ignoring unrecognized CDEF option '%s', found in '%s'"%(key, cdefPath))

        #
        # Do logic error checks.
        #

        if self.cdef['CCCOM'].find( '%CC' ) == -1:
            warningMessage("CDEF field 'CC' not found in field 'CCCOM'")

        if self.cdef['CXXCOM'].find( '%CXX' ) == -1:
            warningMessage("CDEF field 'CXX' not found in field 'CXXCOM'")

        if self.cdef['ARCOM'].find( '%AR' ) == -1:
            warningMessage("CDEF field 'AR' not found in field 'ARCOM'")

        if self.cdef['ASMCOM'].find( '%ASM' ) == -1:
            warningMessage("CDEF field 'ASM' not found in field 'ASMCOM'")

    def executeCommandline( self, commandline ):
        infoMessage("Executing: %s"%commandline, 5)
        self.setColor('yellow')
        ret = os.system( commandline )
        self.setColor(None)
        return ret


    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def _win32_set_color(self, code):
        import ctypes
        # Constants from the Windows API
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def setColor( self, color):
        if sys.platform == 'win32':
            FOREGROUND_BLUE      = 0x0001 # text color contains blue.
            FOREGROUND_GREEN     = 0x0002 # text color contains green.
            FOREGROUND_RED       = 0x0004 # text color contains red.
            FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
            FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
            FOREGROUND_YELLOW    = 0x0006
            # winbase.h
            STD_INPUT_HANDLE = -10
            STD_OUTPUT_HANDLE = -11
            STD_ERROR_HANDLE = -12

            code=FOREGROUND_WHITE
            if color == 'yellow':
                code=FOREGROUND_YELLOW
            if color == 'green':
                code=FOREGROUND_GREEN
            import ctypes
            # Constants from the Windows API
            self.STD_OUTPUT_HANDLE = -11
            hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
            ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)
        else:
            if color == 'yellow':
                print >>sys.stderr, '\x1b[A',
                print >>sys.stderr, '\x1b[33m'# yellow
            elif color == 'green':
                print >>sys.stderr, '\x1b[A',
                print >>sys.stderr, '\x1b[32m' # green
            else:
                print >>sys.stderr, '\x1b[0m' # reset


    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def validateTool( self, cdefItem ):
        if cdefItem in self.validatedTools:
            return
        else:
            self.validatedTools.append( cdefItem )

        if sys.platform == 'win32':
            delimiter = ';'
            tool_ext = '.exe'
        else:
            delimiter = ':'
            tool_ext = ''

        cands = [os.getcwd(),]
        cands.extend( os.environ['PATH'].split(delimiter) )

        for cand in cands:
            if self.cdef.has_key(cdefItem) and len(self.cdef[cdefItem]) != 0:
                toolPath = os.path.join( cand, self.cdef[cdefItem] )
                if os.path.isfile( toolPath ):
                    break
                else:
                    toolPath += tool_ext
                    if not os.path.isfile( toolPath ):
                        toolPath = None
                    else:
                        break
            else:
                toolPath = None

        ctxAssert( toolPath == None or os.path.isfile(toolPath), "Internal error here.." )

        if toolPath == None:

            warningMessage("Unresolved tool: '%s'"%(cdefItem))
            print >>sys.stderr, 'searched:'
            print >>sys.stderr, cands
        else:
            infoMessage("Tool defined by '%s' resolved at '%s'"%(cdefItem, toolPath), 2)

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def isSourceType( self, sourceType, sourceFile ):

        suffix_len = len(sourceType)
        if sourceFile[ -suffix_len : ] == sourceType:
            return True
        else:
            return False



    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeObjFileName( self, srcFileName, objFileTitle = None ):

        if objFileTitle == None:
            objFileTitle = os.path.basename( srcFileName )
            if self.isSourceType( self.cdef['CXXFILESUFFIX'] , srcFileName ):
                objFileTitle = objFileTitle[ 0:-len(self.cdef['CXXFILESUFFIX']) ]
            elif self.isSourceType( self.cdef['CFILESUFFIX'] , srcFileName ):
                objFileTitle = objFileTitle[ 0:-len(self.cdef['CFILESUFFIX']) ]
            elif self.isSourceType( self.cdef['ASMFILESUFFIX'], srcFileName ):
                objFileTitle = objFileTitle[ 0:-len(self.cdef['ASMFILESUFFIX']) ]

        objFilename = "%s%s"%( objFileTitle, self.cdef['OBJSUFFIX'] )
        return objFilename

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeStaticObjectCommandline( self, sourceFile, buildParams, outputDir, objFilename ):

        cmdline = str()
        tool = 'UNKNOWN'
        if self.isSourceType(self.cdef['CXXFILESUFFIX'], sourceFile ):
            cmdline = self.cdef['CXXCOM']
            tool = 'CXX'
        elif self.isSourceType(self.cdef['CFILESUFFIX'], sourceFile):
            cmdline = self.cdef['CCCOM']
            tool = 'CC'
        elif self.isSourceType(self.cdef['ASMFILESUFFIX'], sourceFile):
            cmdline = self.cdef['ASMCOM']
            tool = 'ASM'

        if tool == 'UNKNOWN':
            print >>sys.stderr, 'Unknown source type of file: '+sourceFile
            print >>sys.stderr, 'Please update your .cdef files CXXFILESUFFIX, CFILESUFFIX or ASMFILESUFFIX field'
            userErrorExit('Cannot continue, unknown source file.')

        #
        # Prepare preproessor definitions
        #
        cppdefines_cmdline = str()
        for cppdef in buildParams.prepDefines:
            cppdef_dec = " %s%s%s"%( self.cdef['CPPDEFPREFIX'], cppdef, self.cdef['CPPDEFSUFFIX'] )
            cppdefines_cmdline += cppdef_dec


        #
        # Prepare compiler flags
        #

        cflags_cmdline = str()
        for cflag in buildParams.cflags:
            cflag_dec = "%s"%( cflag )
            cflags_cmdline += cflag_dec

        asmflags_cmdline = str()
        for asmflag in buildParams.asmflags:
            asmflag_dec = "%s"%( asmflag )
            asmflags_cmdline += asmflag_dec

        # use cflags if asmflags are not available, handy when falling back to
        # gcc and rvct
        if asmflags_cmdline == '':
            asmflags_cmdline = cflags_cmdline

        #
        # Prepare include paths
        #

        incpaths_cmdline = str()
        for incpath in buildParams.incPaths:
            incpath_dec = " %s%s%s"%( self.cdef['INCPREFIX'], incpath, self.cdef['INCSUFFIX'] )
            incpaths_cmdline += incpath_dec


        #
        # Prepare sourcefile spec
        #

        srcfile_cmdline = " %s"%( sourceFile )


        #
        # Prepare object file spec
        #

        objfile_cmdline = os.path.join( outputDir, objFilename )


        #
        # Assemble commandline
        #


        # Require all mandatory variables in commandline mask
        if tool == 'ASM':
            for var in ['%ASMFLAGS', '%SOURCES', '%TARGET']:
                if cmdline.find( var ) == -1:
                    userErrorExit("'%s' variable not found in commandline mask"%( var ))
        else:
            for var in ['%CFLAGS', '%CPPDEFINES', '%INCPATHS', '%SOURCES', '%TARGET']:
                if cmdline.find( var ) == -1:
                    userErrorExit("'%s' variable not found in commandline mask"%( var ))

        # Expand all commandline mask variables to the corresponding items we prepared.
        cmdline = cmdline.replace( '%CC'          ,   self.cdef['CC']     )
        cmdline = cmdline.replace( '%CXX'         ,   self.cdef['CXX']    )
        cmdline = cmdline.replace( '%ASMFLAGS'    ,   asmflags_cmdline    )
        cmdline = cmdline.replace( '%ASM'         ,   self.cdef['ASM']    )
        cmdline = cmdline.replace( '%CFLAGS'      ,   cflags_cmdline      )
        cmdline = cmdline.replace( '%CPPDEFINES'  ,   cppdefines_cmdline  )
        cmdline = cmdline.replace( '%INCPATHS'    ,   incpaths_cmdline    )
        cmdline = cmdline.replace( '%SOURCES'     ,   srcfile_cmdline     )
        cmdline = cmdline.replace( '%TARGETDIR'   ,   outputDir           )
        cmdline = cmdline.replace( '%TARGETFILE'  ,   objFilename         )
        cmdline = cmdline.replace( '%TARGET'      ,   objfile_cmdline     )

        # self.validateTool( self.cdef[tool] )

        return cmdline

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def wrapStaticObject( self, sourceFilePath, objectFilename, objectPath, buildParams, commandline ):
        obj = CTXStaticObject()
        obj.source            = sourceFilePath
        obj.filename          = objectFilename
        obj.filepath          = objectPath
        obj.buildParams       = buildParams
        obj.commandline       = commandline
        return obj

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def prebuiltObject( self, prebuiltObjFile, outputDir ):
        import os.path
        shutil.copy( prebuiltObjFile, outputDir)
        obj = self.wrapStaticObject( os.path.dirname( prebuiltObjFile), os.path.basename( prebuiltObjFile), outputDir, '<PREBUILT OBJECT>', 'copy from ' + prebuiltObjFile + ' to '+ outputDir )
        return obj

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def staticObject( self, sourceFile, buildParams, outputDir, objFileTitle = None ):
        if not os.path.exists( sourceFile ):
            userErrorExit("Sourcefile not found: %s"%sourceFile)

        if self.cdef['ECHO_SOURCES'] == True:
            self.setColor('green')
            print >>sys.stderr, os.path.basename( sourceFile )
            self.setColor(None)

        objFileName = self.makeObjFileName( sourceFile, objFileTitle )
        commandline = self.makeStaticObjectCommandline(sourceFile, buildParams, outputDir, objFileName )
        
        ret = self.executeCommandline( commandline )
        if ret != 0:
            userErrorExit("\nFailed to create static object '%s'\nCompiler return code: %d"%(objFileName, ret))

        obj = self.wrapStaticObject( sourceFile, objFileName, outputDir, buildParams, commandline )

        return obj

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeStaticLibraryCommandline( self, objectFiles, libTitle, outputDir ):

        # Prepare object files
        objfiles_cmdline = str()
        for objectFile in objectFiles:
            objPath = os.path.normpath(os.path.join(objectFile.filepath, objectFile.filename))
            objfiles_cmdline += " %s"%objPath

        # Prepare library
        lib_cmdline = "%s%s%s"%( self.cdef['LIBPREFIX'], libTitle, self.cdef['LIBSUFFIX'] )
        lib_cmdline = os.path.normpath(os.path.join( outputDir, lib_cmdline ))

        cmdline = self.cdef['ARCOM']

        cmdline = cmdline.replace( '%AR'     , self.cdef['AR'] )
        # workaround for contexo writing control characters instead of backslashes on windows
        # this seems to work with msvc LIB.EXE and GCC ar
        if sys.platform == 'win32' or sys.platform == 'win64':
            lib_cmdline = lib_cmdline.replace('\\','\\\\')
            objfiles_cmdline = objfiles_cmdline.replace('\\','\\\\')

        cmdline = cmdline.replace( '%TARGET' , lib_cmdline )
        cmdline = cmdline.replace( '%SOURCES', objfiles_cmdline )

        self.validateTool( 'AR' )

        cmdline = prepareCommandFile( cmdline,  self.stdCommandfileName, self.cdefPath )

        return cmdline

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def staticLibrary( self, objectFiles, libraryTitle, outputDir ):

        libName = "%s%s%s"%( self.cdef['LIBPREFIX'], libraryTitle, self.cdef['LIBSUFFIX'] )
        libPath = os.path.join( outputDir, libName )

        if self.cdef['ARCOM_METHOD'].upper() == 'APPEND':
            if os.path.exists( libPath ):
                os.remove( libPath )

            for objectFile in objectFiles:
                commandline = self.makeStaticLibraryCommandline( [objectFile,], libraryTitle, outputDir )
                ret = self.executeCommandline( commandline )
                if ret != 0:
                    userErrorExit("\nFailed to append '%s' to static library '%s'\nar return code: %d"%(objectFile.filename, libPath, ret))

        elif self.cdef['ARCOM_METHOD'].upper() == 'REPLACE':
            commandline = self.makeStaticLibraryCommandline( objectFiles, libraryTitle, outputDir )
            ret = self.executeCommandline( commandline )
            if ret != 0:
                userErrorExit("\nFailed to create static library '%s'\nar command line:\n%s\nar return code: %d"%(libPath, commandline,  ret))
        else:
            userErrorExit("Unsupported value '%s' for CDEF option 'ARCOM_METHOD'"%( self.cdef['ARCOM_METHOD'] ))

        # Handle RANLIB if the CDEF defines it.
        if self.cdef.has_key( 'RANLIB' ) and len(self.cdef['RANLIB']) != 0:

            self.validateTool( 'RANLIB' )

            commandline = "%s %s"%(self.cdef['RANLIB'], libPath)
            # Returnvalue is ignored since RANLIB by "de facto" always returns 0.
            self.executeCommandline( commandline )

        if os.path.exists( self.stdCommandfileName ):
            os.remove( self.stdCommandfileName )

        return ret

#------------------------------------------------------------------------------
def mergeChecksums( checksumList ):
    md = hashlib.md5()
    for c in assureList(checksumList):
        md.update( c )
    return md.hexdigest()

#------------------------------------------------------------------------------
class CTXBuildSession:

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __init__(self, bc ):
        self.bc = bc
        self.cdefPath       = bc.cdefPath
        self.compiler       = bc.getCompiler()
        self.buildParams    = CTXBuildParams()
        self.preloadModules = list()
        self.depMgr         = None #ctx_depmgr.CTXDepMgr()
        #self.sysVars        = getSystemConfig()
        #self.msgSender      = 'CTXBuildSession'
        self.delete_dirs   = set()
        self.setBuildParams( bc.getBuildParams() )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getBCFile( self ):
        return self.bc

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def setBuildParams( self, buildParams ):
        self.buildParams = buildParams

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addBuildParams( self, buildParams ):
        self.buildParams.add( buildParams )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def preloadDependencies( self, codeModules ):
        self.depMgr.addCodeModules( codeModules )

    def setDependencyManager( self, depMgr ):
        self.depMgr = depMgr

    def getDependencyManager(self):
        return self.depMgr

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeStaticObjectChecksum( self, sourceFile, buildParamsChecksum ):
        checksumList = list()

        includeFiles = self.depMgr.getDependencies( sourceFile )

        for incFile in includeFiles:
            ctxAssert( os.path.exists(incFile), "incFile: " + incFile )

            checksum = self.depMgr.getDependenciesChecksum( incFile )
            checksumList.append( checksum )

        checksumList.append( buildParamsChecksum )
        return mergeChecksums( checksumList )

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def makeChecksumPath( self, objectFilename ):
        checksumPath    = objectFilename + ".ctx"
        return checksumPath

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def readStaticObjectChecksum( self, objectFilename ):
        oldChecksum = str()
        checksumPath = self.makeChecksumPath( objectFilename )
        if os.path.exists(checksumPath) and os.path.isfile(checksumPath):
            f = open( checksumPath, "r" )
            oldChecksum = f.read()
            f.close()
            #found = True
        else:
            oldChecksum = '0'

        return oldChecksum

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def setColor( self, color):
        if sys.platform == 'win32':
            FOREGROUND_BLUE      = 0x0001 # text color contains blue.
            FOREGROUND_GREEN     = 0x0002 # text color contains green.
            FOREGROUND_RED       = 0x0004 # text color contains red.
            FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
            FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
            FOREGROUND_YELLOW    = 0x0006
            # winbase.h
            STD_INPUT_HANDLE = -10
            STD_OUTPUT_HANDLE = -11
            STD_ERROR_HANDLE = -12

            code=FOREGROUND_WHITE
            if color == 'yellow':
                code=FOREGROUND_YELLOW
            if color == 'green':
                code=FOREGROUND_GREEN
            import ctypes
            # Constants from the Windows API
            self.STD_OUTPUT_HANDLE = -11
            hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE)
            ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)
        else:
            if color == 'yellow':
                print >>sys.stderr, '\x1b[33m',# green
            elif color == 'green':
                print >>sys.stderr, '\x1b[32m',# green
            else:
                print >>sys.stderr, '\x1b[0m', # reset


    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def executeCommandline( self, commandline ):
        infoMessage("Executing: %s"%commandline, 5)
        self.setColor('yellow')
        ret = os.system( commandline )
        self.setColor(None)
        return ret

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def writeStaticObjectChecksum( self, objectFilename, checksum ):
        checksumPath = self.makeChecksumPath( objectFilename )
        f = open( checksumPath, "w" )
        f.write(checksum)
        #oldChecksum = f.write(checksum)
        f.close()

    def linkExecutable(self,  objects,  outputDir,   exeFilename):
        #objects
        lddirs_cmdline = str()
        buildParams = self.buildParams
        buildParams.ldDirs

        for ldpath in buildParams.ldDirs:
            ldpath_dec = " %s%s%s"%( self.compiler.cdef['LDDIRPREFIX'], os.path.normpath(ldpath), self.compiler.cdef['LDDIRSUFFIX'] )
            lddirs_cmdline += ldpath_dec

        ldlibs_cmdline = str()
        for lib in buildParams.ldLibs:
            ldpath_dec = " %s%s"%( self.compiler.cdef['LDLIBPREFIX'], lib )
            ldlibs_cmdline += ldpath_dec

        exefile_cmdline = os.path.normpath( os.path.join( outputDir, exeFilename ) )

        objfiles_cmdline = str()
        for object in objects:
            #libFile = "%s%s%s"%( self.compiler.cdef['LIBPREFIX'], object, self.compiler.cdef['LIBSUFFIX'] )
            #libPath = os.path.join( outputDir, libFile )
            #objfiles_cmdline += " %s"%libPath
            objfiles_cmdline += " %s"%( os.path.normpath(os.path.join( object.filepath,  object.filename )) )

        # Expand all commandline mask variables to the corresponding items we prepared.
        # this is a fix for gcc, where compiler arguments may include , which the python config doesn't seem to handle
        if type(self.compiler.cdef['LDCOM']) == list and len(self.compiler.cdef['LDCOM']) > 1:
            cmdline = (''.join("%s," % (k) for k in self.compiler.cdef['LDCOM']))[0:-1]
        else:
            cmdline = self.compiler.cdef['LDCOM']

        # Require all mandatory variables in commandline mask

        for var in ['%LD', '%SOURCES']:
            if cmdline.find( var ) == -1:
                userErrorExit("'%s' variable not found in commandline mask"%( var ))
#TODO: replace is primitive. It will blindly replace each n first occurances
        cmdline = cmdline.replace( '%LD'          ,   self.compiler.cdef['LD']  , 1   )
        #cmdline = cmdline.replace( '%CXX'         ,   self.cdef['CXX']    )
        cmdline = cmdline.replace( '%LDDIRS'    ,   lddirs_cmdline    )
        cmdline = cmdline.replace( '%LDLIBS'    ,     ldlibs_cmdline  )
        cmdline = cmdline.replace( '%SOURCES'     ,   objfiles_cmdline     )
       # cmdline = cmdline.replace( '%TARGETDIR'   ,   outputDir           )
       # cmdline = cmdline.replace( '%TARGETFILE'  ,   objFilename         )
        cmdline = cmdline.replace( '%TARGET'      ,   exefile_cmdline     )

        #tool = 'LD' #'CXX' if cplusplus else 'CC'
        infoMessage('from ' + os.getcwd() + ' executing: ' + cmdline,  6)
        linkCommandFileName = 'linkCmdFileName096848hf434qas.file'
        cmdline = prepareCommandFile( cmdline,  linkCommandFileName, self.cdefPath)
        ret = self.executeCommandline( cmdline )
        if ret != 0:
            userErrorExit("\nFailed to link: '%s'\nCompiler return code: %d"%(cmdline, ret))
        if os.path.exists(linkCommandFileName):
            os.remove(linkCommandFileName)
        #self.validateTool( 'LD' )

        pass


    #
    # Builds a source file and returns a CTXStaticObject.
    #
    def buildStaticObject( self, srcFile, outputDir, bc = None, forceRebuild = False ):
        objFileTitle = None

        joinedBuildParams = CTXBuildParams()
        joinedBuildParams.incPaths.extend( self.depMgr.getIncludePaths( [srcFile] ) )

        buildParams = bc.getBuildParams()
        compiler = bc.getCompiler()

        #joinedBuildParams.add( self.buildParams )
        if buildParams != None:
            joinedBuildParams.add( buildParams )
        infoMessage("Joined include paths: %s"%(", ".join(joinedBuildParams.incPaths)), 7)

        buildParamsChecksum = joinedBuildParams.makeChecksum()

        needRebuild     = True

        srcFile = self.depMgr.getFullPathname( srcFile )

        objChecksum     = self.makeStaticObjectChecksum( srcFile, buildParamsChecksum )
        objectFilename  = compiler.makeObjFileName( srcFile, objFileTitle )


        if forceRebuild == False:
            objectFilePath  = os.path.join( outputDir, objectFilename )
            oldChecksum     = self.readStaticObjectChecksum( objectFilePath )
            if oldChecksum == objChecksum:
                needRebuild = False
                infoMessage("Reusing '%s'"%(objectFilename), 3)
            else:
                infoMessage("Object '%s' invalidated by checksum.\nNew: %s\nOld: %s"\
                              %(objectFilename, objChecksum, oldChecksum), 4)

        if needRebuild:
            obj = compiler.staticObject( srcFile, joinedBuildParams, outputDir, objFileTitle )
            self.writeStaticObjectChecksum( os.path.join(obj.filepath,obj.filename), objChecksum )
        else:
            obj = compiler.wrapStaticObject( srcFile, objectFilename, outputDir, buildParams, "n/a" )

        return obj

    def copyPrebuiltObject( self, prebuiltObjFile, outputDir):
        return self.compiler.prebuiltObject( prebuiltObjFile, outputDir)


    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def buildStaticLibrary( self, objectFiles, libraryTitle, outputDir ):
        ret = self.compiler.staticLibrary( objectFiles, libraryTitle, outputDir )
        return ret

    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
