
import os
import sys
import re
import hashlib
import cPickle

from stat import *

from ctx_common import *
from ctx_cmod import *



C_IDENTIFIER_REGEXP     = '[a-zA-Z_]+([a-zA-Z_]|[0-9])*'
C_COMMENT_REGEXP        = '(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)'
C_STRING_REGEXP         = '".*"'
C_USER_INCLUDE_REGEXP   = '#include\s*"\S*"'
C_SYSTEM_INCLUDE_REGEXP = '#include\s*<\S*>'
C_SYS_INC_FILE_REGEXP   = '<.*>'
C_SEPARATORS            = '[%&\^\|#><\+\-&!;{},=\(\)\[\]\:\.!~\*/\?]'

regexp_identifier = re.compile (C_IDENTIFIER_REGEXP)

#------------------------------------------------------------------------------
def is_C_identifier ( token ):
    if regexp_identifier.match (token):
        return 1
    else:
        return 0

#------------------------------------------------------------------------------
def purge_comments ( src ):
    return re.sub( C_COMMENT_REGEXP,'', src )


#------------------------------------------------------------------------------
def purge_strings ( src ):
    return re.sub (C_STRING_REGEXP,'', src)

#------------------------------------------------------------------------------
def parseIncludes ( src ):

    src = purge_comments( src )

    purged_src = purge_strings (src)

    includes = re.findall  (C_USER_INCLUDE_REGEXP, src)

    user_includes = []
    regexp = re.compile (C_STRING_REGEXP)
    for i in includes:
        user_includes.append (regexp.findall (i)[0][1:-1])

    includes = re.findall (C_SYSTEM_INCLUDE_REGEXP, src)

    system_includes = []
    regexp = re.compile ( C_SYS_INC_FILE_REGEXP)
    for i in includes:
        system_includes.append (regexp.findall (i)[0][1:-1])

    return (user_includes, system_includes)

#------------------------------------------------------------------------------
def getModulePrivHeaderDir( modulePath ):
    return CTXRawCodeModule(modulePath).getPrivHeaderDir()

#------------------------------------------------------------------------------
def getModulePubHeaderDir( modulePath ):
    return CTXRawCodeModule(modulePath).getPubHeaderDir()

#------------------------------------------------------------------------------
def getModuleSourceDir( modulePath ):
    return CTXRawCodeModule(modulePath).getSourceDir()

#------------------------------------------------------------------------------
def getPath( src_file, pathList ):

    for path in pathList:
        src_path = os.path.join( path, src_file)
        if os.path.exists(src_path):
            return src_path

    userErrorExit( "'%s' cannot be resolved in current path list: \n  %s"%( src_file, "  \n".join(pathList)))

    return None

#------------------------------------------------------------------------------
def getMD5( buf ):
    md = hashlib.md5()
    md.update( buf )
    return md.hexdigest()

#------------------------------------------------------------------------------
def getFileContents( inputFilePath ):
    f = open( inputFilePath, 'rb' )
    contents = f.read()
    f.close()
    return contents

inputFileContents = ""
stack       = 0
maxStack    = 0
tabs        = ""

#------------------------------------------------------------------------------
def generateChecksum( inputFilePath, checksumMethod ):
    global inputFileContents

    ctxAssert ( os.path.exists ( inputFilePath ), "inputFilePath: " + inputFilePath )

    checksum    = None
    method      = checksumMethod.upper()

    if method == 'MD5':#.........................
        if len(inputFileContents) == 0:
            inputFileContents = getFileContents(inputFilePath)

        checksum = getMD5( inputFileContents )

    elif method == 'MTIME':#......................
        modTime = os.stat( inputFilePath )[ST_MTIME]
        checksum = getMD5( str(modTime) )

    ctxAssert( checksum != None )
    return checksum


#
# Appends the absolute path to a given source file.
# If the path is not available in the dictionary, add it.

def appendPath ( incFilePathDict, pathList, includeFile ):

    if includeFile in incFilePathDict:
        absPath = incFilePathDict[includeFile]
    else:
        absPath = getPath( includeFile, pathList )

    ctxAssert ( absPath != None )
    ctxAssert ( os.path.exists ( absPath ), "Path does not exist")

    incFilePathDict[includeFile] = absPath

    return absPath

#
# Checks that the current cached path is still valid, and if not,
# update it accordingly.
#

def checkPath ( incFilePathDict, pathList, includePath ):
    if os.path.exists ( includePath ):
        return includePath
    else:
        return appendPath ( incFilePathDict, pathList, os.path.basename (includePath) )

def updatePath ( inputFile, inputFilePathDict, pathList ):
    inputFilePath = getPath ( inputFile, pathList )
    inputFilePathDict[inputFile] = inputFilePath
    return inputFilePath






#------------------------------------------------------------------------------
# path_list must be correct paths to source codes.
#
# This is a recursive dependency search algoritm.
#
# General note: The term "source file" is used in this documentation and in
# the naming convetions of the function implementation. It should however be
# noted that both source files (.c/.cpp) and header files (.h) are treated
# identically. Basically any files with "#include" statements are allowed.
#
# One of the key features of this algoritm is that it dynamically updates
# information in the sequence types forwarded in each call. Please read
# documentation for each argument for more information.
#
# @param inputFile
# The file from which to retrieve dependencies (includes).
#
# @param pathList
# List of all paths were source and header files can be obtained from. This
# list is static during the recursion, i.e it is provided by the caller to the
# first call to this function, and then it will remain unmodified throughout
# the search.
#
# @param dependencies
#
# @param inputFilePathHash
# Dictionary mapping source files to the complete path of where they are
# located (including the filename). This dictionary is dynamically updated
# during the search. When a path can't be located in the dictionary, we try
# to find it by concatenating the source filename with all paths in path_list.
# When found, it is also added to this dictionary for future queries.
#
# @param checksumHash
#
# @return
# The function returns False if the input file doesn't need rebuild, i.e the
# dependency tree is already up to date. Oterwise it returns True.
#
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------

def makeSearchPathId( searchPath ):
    m = hashlib.md5()
    m.update( searchPath )
    os.path.getmtime( searchPath )
    return m.hexdigest()
    
def makeSearchPathFilename( searchPath ):
    return "%s.dat" % makeSearchPathId( searchPath )
    
def cacheCodeModulePaths( searchPath, codeModulePaths ):
    filename = makeSearchPathFilename( searchPath )
    
    userDir = getUserTempDir()
    if os.path.exists( userDir ):
        p = os.path.join( userDir, filename )
        f = file( p, "wb" )
        cPickle.dump( codeModulePaths, f, cPickle.HIGHEST_PROTOCOL )
        f.close()

def getCachedCodeModulePaths( searchPath ):
    filename = makeSearchPathFilename( searchPath )
    
    codeModulePaths = list()
    
    userDir = getUserTempDir()
    if os.path.exists( userDir ):
        p = os.path.join( userDir, filename )
        if os.path.exists( p ):
            f = file( p, "rb" )
            codeModulePaths = cPickle.load( f )
            f.close()
            
    return codeModulePaths

#------------------------------------------------------------------------------
#def clearCachedPathLists(searchPaths):
#    global global_path_cache
#
#    cacheId = makeCacheId( searcPaths )
#
#    if global_path_cache.has_key( cacheId ):
#        del global_path_cache[cacheId]
#        print global_path_cache[cacheId]
#
#    userDir = getUserDir()
#
#    if os.path.exists( userDir ):
#        p = os.path.join( userDir, makeCacheIdFilename(cacheId) )
#        os.remove( p )

#------------------------------------------------------------------------------



#------------------------------------------------------------------------------
# Finds all possible dependency locations (include directories) within the
# paths in searchPaths.
#
# For each directory found which evaluates to a valid contexo module, the
# private and public header directories are added to location list.
#
# Directories not evaluated as valid contexo modules will not be further
# processed. This implies that all paths in searchPaths are not traversed
# beyond the first level.
#
#------------------------------------------------------------------------------

def finAllCodeModuleLocations( searchPaths ):
    from ctx_cmod import isContexoCodeModule, CTXRawCodeModule
    
    searchPaths = assureList ( searchPaths )
    
    pathList = list ()
    for path in searchPaths:
        codeModulePaths = getCachedCodeModulePaths( path )
        
        if len(codeModulePaths) == 0:
            pathCandidates = os.listdir( path )
            for cand in pathCandidates:
                candPath = os.path.join( path, cand )
                if isContexoCodeModule( candPath ) == True:
                    mod = CTXRawCodeModule(candPath)
                    codeModulePaths.append( mod.getPubHeaderDir() )
            cacheCodeModulePaths( path, codeModulePaths )
            
        pathList.extend( codeModulePaths )

    return pathList

def finAllCodeModules( searchPaths ):
    from ctx_cmod import isContexoCodeModule, CTXRawCodeModule
    
    searchPaths = assureList ( searchPaths )
    
    modules = list ()
    for path in searchPaths:
        pathCandidates = os.listdir( path )
        for candidate in pathCandidates:
            candPath = os.path.join( path, candidate )
            if isContexoCodeModule( candPath ) == True:
                modules.append( (candidate, candPath) )
                
    return modules

# These are explicit indexes for accessing the tuple indexes in dependencies.
INC_FILELIST        = 0
CHECKSUM            = 1

#------------------------------------------------------------------------------
class CTXDepMgr: # The dependency manager class.
#------------------------------------------------------------------------------
    def __init__(self, codeModules = None, codeModulePaths = list(), unitTests = False ):
        self.msgSender                = 'CTXDepMgr'
        self.depRoots                 = list()
        self.supportedChecksumMethods = ['MTIME', 'MD5']
        self.checksumMethod           = self.supportedChecksumMethods[0]

        self.cmods                    = dict() # Dictionary mapping mod name to raw mod.
        self.depPaths                 = list() # Paths to be used for dep. search
        self.xdepPaths                = list() # Paths to be used for xdep. search.
        
        self.inputFilePathDict        = dict() # { src_file : absfilepath } 
        
        self.processed                = set () # Set containing processed files in this session.
        self.dependencies             = dict() # { src_file : (set( deps ), md5)}
        self.moduleDependencies       = dict() # { module : set( d0, d1, ..., dN) }

        self.useDiskCaching           = True
        
        self.needUpdate               = True
        self.codeModulePaths          = codeModulePaths
        self.unitTests                = unitTests

        self.addDependSearchPaths( codeModulePaths )

        if codeModules != None:
            self.addCodeModules( codeModules, unitTests )
            self.updateDependencyHash()

    def _CTXDepMgr__updateDependencies ( self, inputFileList, pathList ):

        inputFilePath       = str()
        incFileList         = list()
        checksum            = str()

        for inputFile in inputFileList:
            #
            # Resolve full path to the given input file. First try to locate it in
            # our path dictionary, otherwise we search it using the pathList.
            #

            if inputFile in self.inputFilePathDict:
                inputFilePath = self.inputFilePathDict[inputFile]
                if not os.path.exists ( inputFilePath ):
                    inputFilePath = getPath ( inputFile, pathList )
            else:
                inputFilePath = getPath ( inputFile, pathList )

            if inputFilePath == None:
                infoMessage( "WARNING: Dependency manager cannot locate input file: %s"%inputFile, 2 )
                return

            self.inputFilePathDict[inputFile] = inputFilePath

            #
            # Create checksum used to determine if the input file has changed
            # from stored checksum in dependencies
            #

            if inputFile not in self.processed:
                checksum = generateChecksum( inputFilePath, self.checksumMethod )

                if inputFile in self.dependencies and \
                    self.dependencies[inputFile][CHECKSUM] == checksum:
                    incFileList = self.dependencies[inputFile][INC_FILELIST]
                else:
                    inputFileContents = getFileContents( inputFilePath )
                    incFileList = parseIncludes(inputFileContents)[0]

                    self.dependencies[inputFile] = (incFileList, checksum)

                self.processed.add ( inputFile )

            #
            # We now have a list of the files on which our input file depend on,
            # we process each of them by a recursive call to this function.
            #

            self.__updateDependencies( incFileList, pathList )


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def updateModuleDependencies( self, cmod ):
        from ctx_cmod import isContexoCodeModule
        from ctx_cmod import CTXCodeModule

        self.moduleDependencies[cmod.getName()] = set()

        #
        # Add private header dir of the current module to path list.
        # Also add external dependency paths if any.
        #
        pathList  = assureList ( self.depPaths )
        pathList += assureList ( cmod.getPubHeaderDir() )
        pathList += assureList ( cmod.getPrivHeaderDir() )
        pathList += assureList ( cmod.getSourceDir () )

        if cmod.hasExternalDependencies():
            pathList += assureList( CTXCodeModule(cmod.modRoot).resolveExternalDeps() )

        if len(pathList) == 0:
            infoMessage( "WARNING: List of dependency search paths is empty.", 2, self.msgSender )

        # Add all sources for this module
        inputFileList = cmod.getSourceFilenames()

        # Add sources for unit tests
        if cmod.buildUnitTests:
            inputFileList.extend ( cmod.getTestSourceFilenames() )
            pathList += assureList ( cmod.getTestDir () )

        self.__updateDependencies ( inputFileList, pathList )

        for inputFile in inputFileList:
            self.moduleDependencies[cmod.getName()].update ( self.dependencies[inputFile][0] )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def updateDependencyHash( self ):

        #
        # Try to load dependency dictionary from disk.
        #
        self.dependencies = self.loadDependencies()
        self.processed = set()

        #
        # Go through all provided code modules and update the main dependency
        # dictionary.
        #
        for cmod in self.cmods.itervalues():
            self.updateModuleDependencies( cmod )

        self.storeDependencies()
        self.needUpdate = False

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -

    def makeDependenciesPickleFilename( self ):
        pickleFilenameMD5 = hashlib.md5()

        for path in self.depRoots:
            pickleFilenameMD5.update( path )

        pickleFilename = "%s.ctx"%pickleFilenameMD5.hexdigest()
        return pickleFilename

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def loadDependencies( self ):
        dependencies = dict ()

        storageLocation = getUserTempDir()

        p = os.path.join( storageLocation, self.makeDependenciesPickleFilename() )
        if os.path.exists( p ):
            f = file( p, "rb" )
            dependencies = cPickle.load( f )
            f.close()

        return dependencies

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def storeDependencies( self ):
        storageLocation = getUserTempDir()

        if os.path.exists( storageLocation ):
            p = os.path.join( storageLocation, self.makeDependenciesPickleFilename())
            f = file( p, "wb" )
            cPickle.dump( self.dependencies, f, cPickle.HIGHEST_PROTOCOL )
            f.close()

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def addCodeModules( self, codeModulePaths, unitTests = False ):
        from ctx_cmod import assertValidContexoCodeModule
        from ctx_cmod import CTXRawCodeModule

        codeModulePaths = assureList(codeModulePaths)

        #
        # Append CTXRawCodeModule objects for all given modules.
        #
        for mod in codeModulePaths:

            modPath = mod

            if not os.path.exists( modPath ):
                for path in self.depRoots:
                    modPath = os.path.join( path, mod )
                    if os.path.exists( modPath ):
                        break
                    else:
                        modPath = str()
                if len(modPath) == 0:
                    userErrorExit( "Unable to locate code module: '%s'"%mod, self.msgSender )

            assertValidContexoCodeModule( modPath, self.msgSender )

            rawmod = CTXRawCodeModule(modPath, buildUnitTests = unitTests)
            self.cmods[rawmod.getName()] = rawmod

        self.needUpdate = True

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def addDependSearchPaths( self, paths ):
        if len(paths) != 0:
            self.depRoots += assureList( paths )
            self.depPaths = finAllCodeModuleLocations( self.depRoots )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def enableDiskCaching( self ):
        self.useDiskCache = True

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def disableDiskCaching( self ):
        self.useDiskCache = False

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def setChecksumMethod( self, method ):
        if method not in self.supportedChecksumMethods:
            userErrorExit( "Unsupported checksum method: '%s'"%method, self.msgSender )

        self.checksumMethod = method
        self.needUpdate = True

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #
    # Returns all include filenames that the input files depend on.
    #
    def _CTXDepMgr__getDependentIncludes ( self, includeFiles, pathList, processedFiles ):

        for incFile in includeFiles:

            if incFile not in self.dependencies:
                self.__updateDependencies ( [incFile], pathList  )
                ctxAssert ( incFile in self.dependencies, "incFile= " + incFile )

            if incFile not in processedFiles:
                depIncludes = set ( self.dependencies[incFile][0] )
                processedFiles.add ( incFile )
                self.__getDependentIncludes ( depIncludes, pathList, processedFiles )

        return processedFiles

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def hasModule( self, moduleName ):
        return self.cmods.has_key(moduleName)

    #
    # returns all paths required to find the dependent includes of filenames.
    #
    def getIncludePaths ( self, filenames, extraPaths ):

        pathList = self.depPaths
        pathList.extend ( extraPaths )

        depIncludes = self.__getDependentIncludes ( filenames, pathList, set() )

        includePaths = set ()
        for f in depIncludes:
            if f not in self.inputFilePathDict:
                incPath = updatePath ( f, self.inputFilePathDict, pathList )
            elif not os.path.exists (self.inputFilePathDict[f]):
                incPath = updatePath ( f, self.inputFilePathDict, pathList )
            else:
                incPath = self.inputFilePathDict[f]


            includePaths.add ( os.path.dirname (incPath) )

        return list ( includePaths )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getModuleIncludePaths( self, moduleName ):
        from ctx_cmod import CTXCodeModule

        if self.needUpdate:
            self.updateDependencyHash()
        
        if moduleName not in self.moduleDependencies:
            cmod = CTXCodeModule ( moduleName, self.codeModulePaths, False )
            self.cmods[moduleName] = cmod
            self.updateModuleDependencies ( cmod )

        cmod = self.cmods[moduleName]
        filenames = set(cmod.getSourceFilenames())
        filenames.update ( cmod.getPrivHeaderFilenames() )
        filenames.update ( cmod.getPubHeaderFilenames() )

        pathList = assureList ( cmod.getPrivHeaderDir() )
        pathList += assureList ( cmod.getSourceDir () )

        return self.getIncludePaths ( filenames, pathList )


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -

    #
    # Returns a list of files depending on sourceFile ( with abs. paths )
    #
    def getDependencies( self, sourceFile ):

        if self.needUpdate:
            self.updateDependencyHash()

        includeFiles = self.__getDependentIncludes ( [sourceFile], self.depPaths, set() )

        return [self.inputFilePathDict[f] for f in includeFiles ]

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getDependenciesChecksum( self, inputFile ):

        if self.needUpdate:
            self.updateDependencyHash()

        filename = os.path.basename ( inputFile )

        if filename in  self.dependencies:
            return self.dependencies[filename][1]
        else:
            userErrorExit( "Given input file %s is not a valid hash key"%filename, self.msgSender )

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Returns a closed set with all the dependent modules.
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getCodeModules( self ):
        from ctx_cmod import isContexoCodeModule

        if self.needUpdate:
            self.updateDependencyHash()

        processed_set = set ()
        modules = set (self.cmods.keys())  
 
        while modules != processed_set:
            for module in modules - processed_set:
                incPathSet = self.getModuleIncludePaths(module)

                for path in incPathSet:
                    if isContexoCodeModule ( path ):
                        modules.add ( os.path.basename ( path ) )

                processed_set.add ( module )

        return list (modules)


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Returns a closed set with all modules depending on given module.
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getDependentModules( self, module ):
        from ctx_cmod import CTXRawCodeModule, isContexoCodeModule
        
        modules = list ()
        
        if not self.cmods.has_key(module):
            cmod = CTXRawCodeModule( module )
            self.updateModuleDependencies( cmod )
       
        modulePubFiles = set(self.cmods[module].getPubHeaderFilenames())
        
        candidates = finAllCodeModules( self.codeModulePaths )
        for candidate in candidates:
            if not self.moduleDependencies.has_key( candidate[0] ):
                if isContexoCodeModule( candidate[1] ):
                    cmod = CTXRawCodeModule( candidate[1] )
                    self.updateModuleDependencies( cmod )
                    
            dependentFiles = self.moduleDependencies[candidate[0]]
            if not modulePubFiles.isdisjoint (dependentFiles):
                modules.append( candidate[0] )
                
        return modules

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getCodeModulePaths( self ):
        return self.codeModulePaths

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Returns a list of headers depending on the public headers of
    # given modules.
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getPublicHeaders(self, module_name_list,  full_path = False):
        # dependencies = [ src_file : ([ deps ], md5, module_name )]
        header_set  = set ()
        for module_name in module_name_list:
            if self.cmods.has_key ( module_name ):
                pubHeaders = self.cmods[ module_name ].getPubHeaderFilenames()

                for header in pubHeaders:
                    if full_path:
                        header_set.add(self.inputFilePathDict [ header ])
                    else:
                        header_set.add ( header )

                    for dep_header in self.dependencies[header][0]:
                        if (full_path):
                            header_set.add ( self.inputFilePathDict [ dep_header ] )
                        else:
                            header_set.add ( dep_header )

        return list ( header_set )


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -

    #
    # This function allows to get full pathnames of files that known by
    # this dependency manager.
    #
    def getFullPathname ( self, filename ):
        if filename in self.inputFilePathDict.keys():
            return self.inputFilePathDict[filename]
        else:
            None

    #
    # This function empty the code module set.
    # In order to reuse a dependency manager. It must be possible to
    # empty the code module set, and add a new one.
    #
    def emptyCodeModules ( self ):
        self.cmods = dict ()
        self.moduleDependencies = dict()

    def printDependencies( self, tableCharWidth = 80 ):

        printBuffer = str()
        maxLen      = 0

        for inputFile in self.dependencies.keys():
            inputFileName = os.path.basename(inputFile)
            if len(inputFileName) > maxLen:
                maxLen = len(inputFileName)

        printBuffer += "-" * tableCharWidth
        printBuffer += "\n"

        for inputFile in self.dependencies.keys():
            inputFileName = os.path.basename(inputFile)
            printBuffer += " " * (maxLen - len(inputFileName))

            printBuffer += "%s : "%(inputFileName)
            for incFile in self.dependencies[inputFile][0]:
                if incFile == None:
                    continue
                printBuffer += "%s\n"%os.path.basename(incFile)
                printBuffer += " " * maxLen
                printBuffer += "   "

            printBuffer += "CHECKSUM: %s\n\n"%self.dependencies[inputFile][1]


        printBuffer += "-" * tableCharWidth
        printBuffer += "\n"
        return printBuffer
