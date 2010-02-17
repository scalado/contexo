###############################################################################
#                                                                             #
#   ctx_common.py                                                             #
#   Component of Contexo Core - (c) Scalado AB 2006                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Provides common helper functions used throughout the Contexo system.      #
#                                                                             #
###############################################################################

import os
import sys
import string
import shutil
import linecache
import compiler
import re
import config
import logging
import inspect
import os.path
cleanupFuncStack    = list()
globalVerboseLevel  = 1

def areURLsEqual(url1,  url2):
    import urllib
    if urllib.unquote(url1).rstrip(  '/' ) != urllib.unquote(url2).rstrip( '/'):
        return False
    else:
        return True

#------------------------------------------------------------------------------
def ctxExit( exitcode ):
    global cleanupFuncStack
    for func in cleanupFuncStack:
        func()
    sys.exit( exitcode )

#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
def errorMessage(errstr,  filename = None,  lineno = None ):
    import ctx_log

    if lineno == None:
        lineno = inspect.currentframe().f_back.f_lineno
    if filename == None:
        filename = inspect.currentframe().f_back.f_code.co_filename
    msg = " (%s:%d):  %s\n"%(filename,  lineno, errstr)
    logging.error( msg )

    # Include error messages in logfile
    ctx_log.ctxlogAddError( msg )

#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
def warningMessage(warningstr):
    import ctx_log

    lineno = inspect.currentframe().f_back.f_lineno
    filename = inspect.currentframe().f_back.f_code.co_filename
    msg = " (%s:%d):  %s\n"%(os.path.basename(filename),  lineno, warningstr)
    logging.warning(msg)


    # Include warning messages in logfile
    ctx_log.ctxlogAddMessage( msg )


#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
def userErrorExit(errStr):

    lineno = inspect.currentframe().f_back.f_lineno
    filename = inspect.currentframe().f_back.f_code.co_filename

    errorMessage(errStr,  filename,  lineno)
    ctxExit( 1 )

#------------------------------------------------------------------------------
def infoMessage(msg, msgVerboseLevel=0):
    import ctx_log

    global globalVerboseLevel

    if globalVerboseLevel == 0 or globalVerboseLevel < msgVerboseLevel:
        return

    lineno = inspect.currentframe().f_back.f_lineno
    filename = inspect.currentframe().f_back.f_code.co_filename
    msg = " (%s:%d):  %s\n"%(os.path.basename(filename),   lineno, msg)
    logging.info(msg)

    # Include info messages in log when verbose level is higher than standard
    if globalVerboseLevel > 1:
        ctx_log.ctxlogAddMessage( msg )

cachedConfigDict = None

#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
def getUserDir():
    import os
    if 'CONTEXO_HOME_DIR' in os.environ:
        return os.environ['CONTEXO_HOME_DIR']
    userDir = os.path.expanduser( '~' )
    if userDir == '~' or not os.path.exists ( userDir ):
        def valid(path) :
            if path and os.path.isdir(path) :
                return True
            return False
        def env(name) :
            return os.environ.get( name, '' )

        userDir = env( 'SYSTEMDRIVE' )
        if userDir and (not userDir.endswith(u'\\')) :
            userDir += u'\\'
        if not valid(userDir) :
            userDir = u'C:\\'
        if not valid(userDir):
            userErrorExit('Could not find an apprioriate user directory')

    return str(userDir)

#------------------------------------------------------------------------------
def getUserTempDir():
    userDir = getUserCfgDir()
    tempDir = os.path.join ( userDir, "temp" )

    if not os.path.exists ( tempDir ):
        os.mkdir ( tempDir )

    return str(tempDir)

#------------------------------------------------------------------------------
def getUserCfgDir():
    import os
    if 'CONTEXO_CONFIG_DIR' in os.environ:
        return os.environ['CONTEXO_CONFIG_DIR']
    userDir = getUserDir()
    cfgDir = os.path.join ( userDir, ".contexo" )

    if not os.path.exists ( cfgDir ):
        os.mkdir ( cfgDir )

    return str(cfgDir)

#------------------------------------------------------------------------------
def setInfoMessageVerboseLevel( level ):
    global globalVerboseLevel
    globalVerboseLevel = level

#------------------------------------------------------------------------------
def getVerboseLevel():
    global globalVerboseLevel
    return globalVerboseLevel

#------------------------------------------------------------------------------
def assureList( var ):
    if type(var) != list:
        if var != None:
            var = [var]
        else:
            var = []
    return var

#------------------------------------------------------------------------------
def ctxAssert( expression, comment=None ):
    import traceback

    if bool(expression) == False:

        # Get the stack frame where the call to this function was made
        frame = sys._getframe()
        frame = frame.f_back

        # Extract filename and line number of the assertion failure
        assert_file = frame.f_code.co_filename
        assert_line = frame.f_lineno

        # Extract the failed expression as text

        assert_call = linecache.getline( assert_file, assert_line )

        out_re = re.compile(r"^\s*(debug\s*\.\s*)?ctxAssert"
                            r"\s*\(\s*(.*)\s*\)\s*;?$")

        assert_expr = str()

        match = out_re.match( assert_call )

        if match:

            match_string = match.group(2)

            if comment != None:

                # cut away the 'comment' argument from the call
                commbeg = match_string.rfind( comment )
                beg = match_string[:commbeg].rfind( ',' )
                match_string = match_string[:beg]

            assert_expr = match_string

        else:
            assert_expr = "(error parsing expression)"


        # output
        print "\n***** CONTEXO ASSERTION FAILURE *****"
        print "          File: %s"%assert_file
        print "          Line: %d"%assert_line
        print "    Expression: %s"%assert_expr
        print "       Comment: %s"%comment
        print "\n*************************************\n"
        print "Callstack: \n"
        print traceback.print_stack()
        assert(42 in "answer to life, universe and everything")
        #ctxExit( 42 )


#------------------------------------------------------------------------------
#
#   readLstFile( file_path )
#
#   Reads each line of the given file into a list and returns it. Lines
#   beginning with '#' are ignored.
#
#------------------------------------------------------------------------------
def readLstFile( file_path ):

    file_path = file_path.strip( ' @' )

    file = open( file_path, "r" )
    thelist = list()
    for line in file.readlines():
        line = string.rstrip( line, " \n\r" )
        line = string.lstrip( line, " \n\r" )
        if line != "" and line[0] != '#':
            thelist.append( line )

    file.close()

    return thelist

#------------------------------------------------------------------------------
#
#   writeLstFile( the_list, file_path )
#
#   Writes all elements of the given list to a file, each element on a separate
#   eow. The resulting list file can be read back into a list using
#   "readLstFile()".
#
#------------------------------------------------------------------------------
def writeLstFile( the_list, file_path, header = None ):

    file = open( file_path, "w" )

    if header != None:
        file.write( header + "\n" )

    for item in the_list:
        file.write( str(item) + "\n" )

    file.close()

#------------------------------------------------------------------------------
#
#   Searches the give list for lst files and expands their contents into the
#   list at the same location.
#
#   The function tries to locate lst files first by opening them as they are
#   given in the list, then by concatenating them with each candidate in the
#   given searcPaths argument.
#
#------------------------------------------------------------------------------
def expandLstFilesInList( theList, msgSender, searchPaths ):

    ctxAssert( type(theList) == list )
    ctxAssert( type(searchPaths) == list or type(searchPaths) == str or type(searchPaths) == unicode)

    if type(searchPaths) != list:
        searchPaths = [searchPaths,]

    theExpandedList = list()
    for item in theList:

        ctxAssert( type(item) == str )

        if item.strip()[0] == '@':
            tried       = list()
            lstFile     = item.strip(' @')
            lstFilePath = str()
            searchPaths.insert( 0, "" )

            for path in searchPaths:
                testLoc = os.path.join( path, lstFile )
                if os.path.exists( testLoc ):
                    lstFilePath = testLoc
                    break
                else:
                    tried.append( testLoc )

            if len(lstFilePath) == 0:
                errorMessage("Cannot find lstfile '%s'."%( item ))
                infoMessage("Attempted following locations:", 0)
                for loc in tried:
                    infoMessage("-> \t%s"%loc, 0)
                ctxExit(1)

            lstList = readLstFile( lstFilePath )
            theExpandedList.extend( lstList )
        else:
            theExpandedList.append( item )

    return theExpandedList

#------------------------------------------------------------------------------
#
#
#------------------------------------------------------------------------------
def dumpToFile( data, filePath ):
    file = open( filePath, "w" )
    file.write( str(data) )
    file.close()

#------------------------------------------------------------------------------
#
#
#------------------------------------------------------------------------------
def replaceInFile( file_path, existing, replacement ):
    tmp_file = file_path + ".tmp"
    if os.path.exists( file_path ):
        inputFile   = file(file_path)
        outputFile  = file(tmp_file, "w")

        for l in inputFile.readlines():
            l = string.replace(l, existing, replacement)
            outputFile.write(l)

        inputFile.close()
        outputFile.close()
        os.remove( file_path )
        os.rename( tmp_file, file_path )

#------------------------------------------------------------------------------
#
#
#------------------------------------------------------------------------------
def replaceMatchingLineInFile( file_path, existing, replacement ):
    tmp_file = file_path + ".tmp"
    if os.path.exists( file_path ):
        inputFile   = file(file_path)
        outputFile  = file(tmp_file, "w")

        for l in inputFile.readlines():
            if l.find( existing ) != -1:
                l = replacement
            outputFile.write(l)

        inputFile.close()
        outputFile.close()
        os.remove( file_path )
        os.rename( tmp_file, file_path )

#------------------------------------------------------------------------------
#
#   getEnvironPathList()
#
#   Returns a list of all paths defined in the PATH environment variable.
#
#------------------------------------------------------------------------------
def getEnvironPathList():
    path_list = string.split( os.environ['PATH'], ';' )
    return path_list

#------------------------------------------------------------------------------
#
#   replaceTree()
#
#   Equivalent to shutil.copytree() except for that it allows dst to exist,
#   i which case it is replaced.
#
#------------------------------------------------------------------------------
def replaceTree(src, dst):

    names = os.listdir(src)
    if os.path.isdir( dst ) == False:
        os.mkdir(dst)

    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(srcname):
                replaceTree( srcname, dstname)
            else:
                shutil.copyfile(srcname, dstname)
        except (IOError, os.error), why:
            errors.append((srcname, dstname, why))
    if errors:
        raise Error, errors

#------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------
def expandOptionFile( optFile ):

    expandedOptions = str()

    if not os.path.exists( optFile ):
        userErrorExit("Cannot find option file '%s'"%optFile)

    file = open( optFile, "r" )
    for line in file.readlines():

        line = line.strip( " \n\r" )
        expandedOptions += ' ' + line

    file.close()

    return expandedOptions.strip()

