import os
#import sys
import hashlib
import cPickle

from stat import *

from ctx_common import *
#import ctx_cmod

import ctx_cparser

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
def findFileInPathList( src_file, pathList ):
    if src_file and pathList:
        for path in pathList:
            src_path = os.path.join( path, src_file)
            if os.path.exists(src_path):
                return src_path
        errorMessage("'%s' cannot be resolved in current path list."%( src_file) )
        infoMessage("%s"%"\n".join(pathList), msgVerboseLevel=8)
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
        absPath = findFileInPathList( includeFile, pathList )

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
    inputFilePath = findFileInPathList ( inputFile, pathList )
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
# Finds all possible source path locations  within the paths in searchPaths.
#
# For each directory found which evaluates to a valid contexo module, the
# private and public header directories are added to location list.
#
# Directories not evaluated as valid contexo modules will not be further
# processed. This implies that all paths in searchPaths are not traversed
# beyond the first level.
#
#------------------------------------------------------------------------------

def findAllCodeModulPaths( searchPaths ):
    from ctx_cmod import isContexoCodeModule, CTXRawCodeModule

    searchPaths = assureList ( searchPaths )

    pathList = list ()
    for path in searchPaths:
        codeModulePaths = []

        if len(codeModulePaths) == 0:
            try:
                pathCandidates = os.listdir( path )
            except OSError, (errno,  errmsg):
                userErrorExit("Could not list directory '%s': %s"%(path,  errmsg))
            for cand in pathCandidates:
                candPath = os.path.join( path, cand )
                if isContexoCodeModule( candPath ) == True:
                    mod = CTXRawCodeModule(candPath)
                    codeModulePaths.append( mod.getPubHeaderDir() )
                    codeModulePaths.append( mod.getPrivHeaderDir() )
                    codeModulePaths.append( mod.getSourceDir () )
                    codeModulePaths.append( mod.getTestDir () )
        pathList.extend( codeModulePaths )

    return pathLi

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
    def __init__(self, codeModulePaths = list(),  tolerateMissingHeaders = False,  additionalIncDirs = None):
        self.tolerateMissingHeaders = tolerateMissingHeaders
        self.msgSender                = 'CTXDepMgr'
        self.depRoots                 = list()
        self.supportedChecksumMethods = ['MTIME', 'MD5']
        self.checksumMethod           = self.supportedChecksumMethods[0]

        self.cmods                    = dict() # Dictionary mapping mod name to raw mod.
        self.additionalIncludeDirs = assureList(additionalIncDirs)
        self.depPaths                 = set() # Paths to be used for dep. search
        self.depPaths.update ( self.additionalIncludeDirs )
        self.xdepPaths                = list() # Paths to be used for xdep. search.

        self.inputFilePathDict        = dict() # { src_file : absfilepath }

        self.processed                = set () # Set containing processed files in this session.
        self.dependencies             = dict() # { src_file : (set( dep_headers ), md5)} (all files)
        self.moduleDependencies       = dict() # { module : set( dep_headers ) } (for a module)

        self.useDiskCaching           = True

        self.needUpdate               = True
        self.codeModulePaths          = codeModulePaths

        self.addDependSearchPaths( codeModulePaths )

    def _CTXDepMgr__updateDependencies ( self, inputFileList, pathList):

        inputFilePath       = str()
        incFileList         = list()
        checksum            = str()

        for inputFile in inputFileList:
            #
            # Resolve full path to the given input file. First try to locate it in
            # our path dictionary, otherwise we search it using the pathList.
            # The dependency list keys will be absolute paths
            #
            inputFilePath = self.locate(inputFile,  pathList)
            if inputFilePath == None:
                dependencies = self.findFilesDependingOn(inputFile)
                assert(dependencies)
                if ( self.tolerateMissingHeaders):
                    warningMessage("Dependency manager cannot locate input file: %s (from %s)"%(inputFile, ",".join(dependencies) ))
                else:
                    userErrorExit("Dependency manager cannot locate input file: %s (from %s)"%(inputFile, ",".join(dependencies) ))
                continue #return

            #
            # Create checksum used to determine if the input file has changed
            # from stored checksum in dependencies
            #

            assert(os.path.isabs(inputFile) or not inputFile.endswith('.c') )
            if inputFilePath not in self.processed:
                checksum = generateChecksum( inputFilePath, self.checksumMethod )

                if inputFilePath in self.dependencies and \
                    self.dependencies[inputFilePath][CHECKSUM] == checksum:
                    incFileList = self.dependencies[inputFilePath][INC_FILELIST]
                else:
                    inputFileContents = getFileContents( inputFilePath )
                    incFileList = ctx_cparser.parseIncludes(inputFileContents)[0]


                    self.dependencies[inputFilePath] = (incFileList, checksum)

                self.processed.add ( inputFilePath )

            inputFileContents = getFileContents( inputFilePath )

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
        #pathList  = assureList ( self.depPaths )
        #pathList += assureList ( cmod.getPubHeaderDir() )
        #pathList += assureList ( cmod.getPrivHeaderDir() )
        #pathList += assureList ( cmod.getSourceDir () )

        #self.depPaths.update ( assureList ( cmod.getPubHeaderDir() ) )
        #self.depPaths.update ( assureList ( cmod.getPrivHeaderDir() ) )
        #self.depPaths.update ( assureList ( cmod.getSourceDir () ) )

        if cmod.buildUnitTests:
            self.depPaths.update (assureList ( cmod.getTestDir () ) )

        paths = self.depPaths;

        if cmod.hasExternalDependencies():
            paths.update( assureList( CTXCodeModule(cmod.modRoot).resolveExternalDeps() ) )

        if len(paths) == 0:
            infoMessage("WARNING: List of dependency search paths is empty.", 2)

        # Add all sources for this module
        inputFileList = cmod.getSourceAbsolutePaths() #getSourceFilenames()
        inputFileList.extend ( cmod.getPubHeaderFilenames() )
        # Add sources for unit tests
        if cmod.buildUnitTests:
            inputFileList.extend ( cmod.getTestSourceAbsolutePaths() )#getTestSourceFilenames() )
            #pathList += assureList ( cmod.getTestDir () )

        self.__updateDependencies ( inputFileList, list(paths) )

        #copy dependencies for module's sourcefiles from the global dependency dictionary
        for inputFile in inputFileList:
            self.moduleDependencies[cmod.getName()].update ( self.dependencies[self.locate(inputFile)][0] )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def findFilesDependingOn(self,  header):
        ret = list()
        for file in self.dependencies.keys():
            if header in self.dependencies[file][0]:
                ret.append(file)
        return ret

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def locate(self,  file,  pathList=None):
        if file not in self.inputFilePathDict or not self.inputFilePathDict[file] or not os.path.exists(self.inputFilePathDict[file]) :
            filefromlist = findFileInPathList ( file, pathList )
            if filefromlist==None:
                return None
            self.inputFilePathDict[file] = filefromlist
        return self.inputFilePathDict[file]


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
        from ctx_cmod import CTXRawCodeModule

        codeModulePaths = assureList(codeModulePaths)

        #
        # Append CTXRawCodeModule objects for all given modules.
        #
        for mod in codeModulePaths:

            modPath = self.resolveCodeModulePath( mod )

            rawmod = CTXRawCodeModule(modPath, buildUnitTests = unitTests)
            self.cmods[rawmod.getName()] = rawmod

        self.needUpdate = True

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    #set up the list of paths which are interesting for the dep search. It is the view root and all the code module roots.
    def addDependSearchPaths( self, paths ):
        if len(paths) != 0:
            self.depRoots += assureList( paths )
            self.depPaths.update(findAllCodeModulPaths( self.depRoots ))

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def enableDiskCaching( self ):
        self.useDiskCache = True

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def disableDiskCaching( self ):
        self.useDiskCache = False

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def setChecksumMethod( self, method ):
        if method not in self.supportedChecksumMethods:
            userErrorExit("Unsupported checksum method: '%s'"%method)

        self.checksumMethod = method
        self.needUpdate = True

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #
    # Returns all include filenames that the input files depend on.
    #
#    def _CTXDepMgr__getDependentIncludes ( self, includeFiles, pathList, processedFiles= set()):
#
#        for incFile in includeFiles:
#
#            if incFile not in self.dependencies:
#                self.__updateDependencies ( [incFile], pathList  )
#                ctxAssert ( incFile in self.dependencies, "incFile= " + incFile )
#
#            if incFile not in processedFiles:
#                depIncludes = set ( self.dependencies[incFile][0] )
#                processedFiles.add ( incFile )
#                self.__getDependentIncludes ( depIncludes, pathList, processedFiles )
#
#        return processedFiles


    def _CTXDepMgr__getDependentIncludes ( self, includeFiles, pathList):
        processedFiles = set()
        def enclosedRecursion(includeFiles):
            for incFile in includeFiles:
                if incFile not in self.dependencies:
                    self.__updateDependencies ( [incFile], pathList  )
                    ctxAssert ( incFile in self.dependencies, "incFile= " + incFile )
                if incFile not in processedFiles:
                    depIncludes = set ( self.dependencies[incFile][0] )
                    fullpathIncludes = [ s for s in map( self.locate,  depIncludes) if s != None ]
                    processedFiles.add ( incFile )
                    enclosedRecursion ( fullpathIncludes )

        enclosedRecursion(includeFiles)
        return processedFiles

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def hasModule( self, moduleName ):
        return self.cmods.has_key(moduleName)

    #
    # returns all paths required to find the dependent includes of filenames.
    #
    def getIncludePaths ( self, filenames, extraPaths = None ):

        pathList = list(self.depPaths)

        if extraPaths != None:
            pathList.extend ( extraPaths )

        #get the includes that 'filenames' depend on i.e. ( the includes files in the filenames list include )
        depIncludes = self.__getDependentIncludes ( filenames, pathList )

#        includePaths = set ()
#        for f in depIncludes:
#            if f not in self.inputFilePathDict:
#                incPath = updatePath ( f, self.inputFilePathDict, pathList )
#            elif not os.path.exists (self.inputFilePathDict[f]):
#                incPath = updatePath ( f, self.inputFilePathDict, pathList )
#            else:
#                incPath = self.inputFilePathDict[f]


            #includePaths.add ( os.path.dirname (incPath) )

        ret = set ( map(os.path.dirname,  depIncludes) )
        #infoMessage("pathList: %s"%", ".join(pathList), 6 )
        #infoMessage("getIncludePaths: %s"%", ".join(ret), 6 )
        #import pdb
        #pdb.set_trace()
        return ret

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getModuleIncludePaths( self, moduleName ):
        from ctx_cmod import CTXCodeModule
        #import pdb
        #pdb.set_trace()
        if self.needUpdate:
            self.updateDependencyHash()

        if moduleName not in self.moduleDependencies:
            cmod = CTXCodeModule ( moduleName, self.codeModulePaths, False )
            self.cmods[moduleName] = cmod
            self.updateModuleDependencies ( cmod )

        cmod = self.cmods[moduleName]
        filenames = set( cmod.getSourceAbsolutePaths() )
        filenames.update ( cmod.getPrivHeaderAbsolutePaths() )
        filenames.update ( cmod.getPubHeaderAbsolutePaths() )

     #   pathList = assureList ( cmod.getPrivHeaderDir() )
     #   pathList += assureList ( cmod.getSourceDir () )

       # return self.getIncludePaths ( filenames, pathList )
        ret = self.getIncludePaths ( filenames, None )
#   print "getModuleIncludePaths: "
#   print ret
        return ret


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -

    #
    # Returns a list of files depending on sourceFile ( with abs. paths )
    #
    def getDependencies( self, sourceFile ):

        if self.needUpdate:
            self.updateDependencyHash()

        includeFiles = self.__getDependentIncludes ( [sourceFile], list(self.depPaths))

        #deps = list()
        #for f in includeFiles:
        #    if not self.inputFilePathDict.has_key(f):
        #        deps.append( updatePath( f, self.inputFilePathDict, self.depPaths ) )
        #    deps.append(self.inputFilePathDict[f])

        return includeFiles

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getDependenciesChecksum( self, inputFile ):

        if self.needUpdate:
            self.updateDependencyHash()

        filename = inputFile #os.path.basename ( inputFile )

        if filename in  self.dependencies:
            return self.dependencies[filename][1]
        else:
            userErrorExit("Given input file %s is not a valid hash key"%filename)

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Returns a closed set with all the modules that self.cmods depends on
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def getCodeModulesWithDependencies( self ):
        import ctx_cmod

        if self.needUpdate:
            self.updateDependencyHash()

        processed_set = set ()
        moduleRoots = set ( map(lambda mod: mod.modRoot,  self.cmods.values() ))

        while moduleRoots != processed_set:
            for moduleRoot in moduleRoots - processed_set:
                incPathSet = self.getModuleIncludePaths(moduleRoot)

                for path in incPathSet:
                    if ctx_cmod.isContexoCodeModule ( path ): #WARNING: assuming public headers lie in the root of a module
                        moduleRoots.add (  path  )

                processed_set.add ( moduleRoot )

        return list (moduleRoots)

#
#    def getCodeModulesDependencies( self, input_modules ):
#
#        input_modules = assureList( input_modules )
#        codeModules = self.getCodeModulesWithDependencies()
#
#        return list (codeModules- set(input_modules))

    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    # Returns a list of CTXCodeModule from the named list of modules.
    #
    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -
    def createCodeModules( self, input_modules, buildTests=False, force=False ):
        from ctx_cmod import CTXCodeModule

        codeModules = list ()

        for mod in set(input_modules):
            modPath = self.resolveCodeModulePath( mod )
            codeModules.append( CTXCodeModule(modPath,
                                              pathlist=None,
                                              buildUnitTests = buildTests,
                                              forceRebuild=force) )

        return codeModules


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
                pubHeaders = self.cmods[ module_name ].getPubHeaderAbsolutePaths()

                for header in pubHeaders:
                    if full_path and not os.path.isabs(header):
                        header_set.add(self.inputFilePathDict [ header ])
                        assert(False)
                    else:
                        header_set.add ( header )

                    for dep_header in self.dependencies[header][0]:
                        if (full_path):
                            header_set.add ( self.inputFilePathDict [ dep_header ] )
                        else:
                            header_set.add ( dep_header )

        return list ( header_set )

    def resolveCodeModulePath( self, mod ):
        import ctx_cmod

        modPath = mod

        #if not os.path.exists( modPath ):
        for path in self.depRoots:
            modPath = os.path.join( path, mod )
            if os.path.exists( modPath ):
                if ctx_cmod.isContexoCodeModule(modPath):
                    break
                else:
                    infoMessage( "Directory %s is not a valid contexo module, ignoring"%modPath,  3  )
            else:
                modPath = str()

        if len(modPath) == 0:
            userErrorExit("Unable to locate code module: '%s'"%mod)

        ctx_cmod.assertValidContexoCodeModule( modPath, self.msgSender )

        return modPath


    # - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - -

    #
    # This function allows to get full pathnames of files that known by
    # this dependency manager.
    #
    def getFullPathname ( self, filename ):
        if self.inputFilePathDict.has_key(filename):
            return self.inputFilePathDict[filename]
        else:
            return None

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
