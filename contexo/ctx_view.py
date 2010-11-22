###############################################################################
#                                                                             #
#   ctx_view.py                                                               #
#   Component of Contexo Shell - (c) Scalado AB 2008                          #
#                                                                             #
#   Author:                                                                   #
#   Manuel Astudillo ( manuel.astudillo@scalado.com)                          #
#   ------------                                                              #
#                                                                             #
#   View Class.                                                               #
#                                                                             #
###############################################################################

from ctx_rspec import RSpecFile
#, RSpecFileLocator
from ctx_repo_svn import *
from ctx_common import userErrorExit
from ctx_common import warningMessage, assureList
#from os import sep

SYSGLOBAL_PATH_SECTIONS = ['modules',
                           'cdef',
                           'bconf',
                           'comp',
                           'misc']

#------------------------------------------------------------------------------
class CTXView:
    def __init__(self, view_path=str(), updating=False, validate=True ):
        self.localPath = os.path.abspath(view_path)
        self.global_paths = dict() # {section: pathlist}, where 'section' is any of SYSGLOBAL_PATH_SECTIONS
        self.rspec = None
        self.updating = updating # True when the view is being updated instead of used for building
        self.msgSender = "CTXView"

        infoMessage("Using view: %s "%(self.getRoot()), 2)

        for sec in SYSGLOBAL_PATH_SECTIONS:
            self.global_paths[sec] = list()

        self.process_view_directory()
        self.set_global_config()
        os.chdir( self.getRoot() )

        if validate:
            self.validateRepositories()
        else:
            infoMessage("Skipping repository validation", 2);

    #--------------------------------------------------------------------------
    def set_global_config( self ):
        import ctx_cfg
        import ctx_common
        cfgFile = ctx_cfg.CFGFile( os.path.join( ctx_common.getUserCfgDir(), 'contexo.cfg' ))

        for p in ctx_common.assureList(cfgFile.getBConfPaths()):
            self.addGlobalPath( p, 'bconf' )

        for p in ctx_common.assureList(cfgFile.getCDefPaths()):
            self.addGlobalPath( p, 'cdef' )

        self.addGlobalPath( ctx_common.getUserCfgDir(), 'misc' )
        self.addGlobalPath( self.getRoot(), 'misc' )

    #--------------------------------------------------------------------------
    def process_view_directory( self ):

        # The view directory itself is always a candidate when locating any
        # type of item.
        for section in SYSGLOBAL_PATH_SECTIONS:
            self.addGlobalPath( self.getRoot(), section )

        # Process RSpecs and extract all additional paths introduced
        self.process_rspecs()
        #rspec = self.getRSpec()
        #if rspec != None:
        #    for repo in rspec.getRepositories():
        #        self.paths[section].extend( repo.getPaths(section) ) for section in VIEW_PATH_SECTIONS


        #

    #--------------------------------------------------------------------------
    def validateRepositories( self ):

        all_valid = True

        if not self.hasRSpec():
            return

        for repo in self.getRSpec().getRepositories():
            infoMessage("Validating repository '%s'"%(repo.getID()), 1)
            if not repo.checkValid( self.updating ):
                all_valid = False

        if all_valid == False:
            userErrorExit("Validation failed.")

    #--------------------------------------------------------------------------
    def process_rspecs( self ):
        #
        # Look for RSpecs at the root of the view. Multiple RSpecs are
        # prohibited unless one of them ends up importing all of the others
        # (directly or indirectly).
        #

        # Collect all rspecs
        rspec_path_list = list()
        root_files = os.listdir( self.localPath )
        for f in root_files:
            root, ext = os.path.splitext( f )
            if ext.lower() == '.rspec':
                rspec_path_list.append( os.path.join(self.getRoot(), f ) )

        if len(rspec_path_list) != 0:
            infoMessage("RSpecs detected in view: \n   %s"%("\n   ".join(rspec_path_list)), 2)

        # Determine the import relationship between the RSpecs
        if len(rspec_path_list):
            #
            candidate_rspecs = list()
            for rspec_path in rspec_path_list:

                rspec = RSpecFile( rspec_path, parent=None, view=self )
                remainder = False

                for potential_import in rspec_path_list:
                    if potential_import == rspec_path:
                        continue # skip checking if we import ourselves

                    if potential_import not in rspec.getImportPaths( recursive=True ):
                        remainder = True
                        break # we found an RSpec not imported so move on to the next one

                # remainder is False if all other RSpecs could be found in the
                # import tree of 'rspec', or if 'rspec' is the only one present
                # in the view.
                if remainder == False:
                    candidate_rspecs.append( rspec )

            # We should have exactly ONE candidate rspec. If we have zero candidates, it
            # means no single rspec imports all the others.
            # If we have multiple candidates, it means more than one rspec imports all
            # the others. Both these cases are terminal errors since we have no logic
            # way of selecting one of the candidates.
            if len(candidate_rspecs) != 1:
                userErrorExit("RSpec selection is ambiguous. Only one RSpec is allowed in a view. If multiple RSpecs exist, at least one of them must directly or indirectly import the others")
            else:
                infoMessage("Using RSpec: '%s'"%(candidate_rspecs[0].getFilename()), 2)
                self.setRSpec( candidate_rspecs[0] )

        else:
            infoMessage("No RSpec found in view", 2)

    #--------------------------------------------------------------------------
    def setRSpec( self, _rspec ):
        self.rspec = _rspec

    #--------------------------------------------------------------------------
    def getRSpec( self ):
        return self.rspec

    #--------------------------------------------------------------------------
    def hasRSpec( self ):
        return self.getRSpec() != None

    #--------------------------------------------------------------------------
    def addGlobalPath(self, path, path_section):
        ctxAssert( path_section in SYSGLOBAL_PATH_SECTIONS, "Unknown global path section '%s'"%(path_section) )
        infoMessage("System global path '%s' added to section '%s' in view"%(path, path_section), 2)
        self.global_paths[path_section].append( path )

    #--------------------------------------------------------------------------
    def getGlobalPaths(self, path_section):
        ctxAssert( path_section in SYSGLOBAL_PATH_SECTIONS, "Unknown global path section '%s'"%(path_section) )
        return self.global_paths[path_section]

    #--------------------------------------------------------------------------
    def getItemPaths(self, path_section ):
        if self.hasRSpec():
            item_paths = self.getRSpec().getRepoPaths( path_section )
        else:
            item_paths = self.getGlobalPaths(path_section)

        infoMessage("Item paths in section '%s' returned from view:\n  %s"\
                     %(path_section, "\n  ".join(item_paths)), 3)

        return item_paths

    #--------------------------------------------------------------------------
    #def getRSpecPaths(self, path_section ):
    #    ctxAssert( self.hasRSpec(), "Caller should check if view has RSpec prior to this call" )
    #
    #    full_paths = list()
    #    for path in self.getRSpec().getRepoPaths( path_section ):
    #        full_path = os.path.join(self.getRoot(), path)
    #        ctxAssert( os.path.exists(full_path) and os.path.isdir(full_path), "Non existing path detected by view handler: %s"%(full_path) )
    #        full_paths.append( full_path )
    #
    #    return full_paths

    #--------------------------------------------------------------------------
    # Used to query the location of a certain build item which belongs
    # to a certain path section (module, bconf, cdef, etc).
    # This method implements the rules for how paths are prioritized between
    # views, rspecs and global config.
    #--------------------------------------------------------------------------
    def locateItem(self, item, path_sections):

        candidate_locations = list()
        tried_locations = list()

        path_sections = assureList( path_sections )

        for path_section in path_sections:
            # Always prioritize locating items from the RSpec repositories
            if path_section in REPO_PATH_SECTIONS and self.getRSpec() != None:
                for repo in self.getRSpec().getRepositories():
                    repo_candidates, repo_tried = repo.locateItem( item, path_section )
                    candidate_locations.extend( repo_candidates )
                    tried_locations.extend( repo_tried )

            if len(candidate_locations) == 1:
                infoMessage("Located '%s' at '%s'"%(item, candidate_locations[0]), 2)
                return candidate_locations[0]
            elif len(candidate_locations) > 1:
                userErrorExit("Multiple occurances of '%s' was found. Unable to determine which one to use: \n   %s"\
                               %(item, "\n   ".join(candidate_locations)))
            infoMessage("Item '%s' was not found in RSpec repositories.\nTrying system global locations."%(item), 2) 

        for path_section in path_sections:
            # File was not found in RSpec repositories, look in view
            if path_section in SYSGLOBAL_PATH_SECTIONS:
                for path in self.getGlobalPaths(path_section):
                    tried_locations.append( path )
                    if os.path.isdir(path):
                        if item in os.listdir(path):
                            candidate_locations.append( os.path.join(path, item) )
                    else:
                        tried_locations[-1] = tried_locations[-1] + " (path not found)"
                        warningMessage("System global path '%s' doesn't exist"%(path))

            if len(candidate_locations) == 1:
                infoMessage("Located '%s' at '%s'"%(item, candidate_locations[0]), 2)
                return candidate_locations[0]
            elif len(candidate_locations) > 1:
                userErrorExit("Multiple occurances of '%s' was found. Unable to determine which one to use: \n   %s"\
                               %(item, "\n   ".join(candidate_locations)))


        userErrorExit("Unable to locate file '%s'. Attempted the following locations: \n   %s"\
                       %(item, "\n   ".join(tried_locations)))

    #--------------------------------------------------------------------------
    def getRoot( self ):
        return self.localPath

    #--------------------------------------------------------------------------
    # Updates all existing RSpec repositories within this view
    #--------------------------------------------------------------------------
    def updateRepositories(self):
        if self.hasRSpec():
            for repo in self.getRSpec().getRepositories():
                if repo.isLocal():
                    repo.update()

    #--------------------------------------------------------------------------
    # Checks out all missing RSpec repositories within this view
    #--------------------------------------------------------------------------
    def checkoutRepositories(self):
        if self.hasRSpec():
            for repo in self.getRSpec().getRepositories():
                if not repo.isLocal():
                    repo.checkout()

    #--------------------------------------------------------------------------
    # freezes this view with the current revision numbers for given
    # repository, or all repos if none specified.
    #--------------------------------------------------------------------------
    def freeze(self, repo_names = None,  output=sys.stdout):
        from contexo.ctx_rspec_freeze import RspecFreezer
        # work around the use of stdout since git needs access to it
        import tempfile
        (fd, fileName) = tempfile.mkstemp()
        f = os.fdopen(fd, "w+b")
        freezer = RspecFreezer(self.rspec.getRepositories(),  output = f)
        freezer.generateFrozen(repo_names)
        f.close()
        f = open(fileName, 'r+')
        output.write(f.read())
        f.close()
        os.remove(fileName)

    #--------------------------------------------------------------------------
    # unfreezes given repo, or all repos in the view
    #--------------------------------------------------------------------------
    #def unfreeze(self, repo_name = None):
    #    pass

    #--------------------------------------------------------------------------
    # prints this view in human readable way
    #--------------------------------------------------------------------------
    def printView(self):
        print "\nView", self.rspec.getFilename(), "at", self.rspec.getFilePath(), "\n"

        repositories = self.rspec.getRepositories()
        for repo in repositories:
            print "REPOSITORY:", repo.id_name, ", path:", repo.local_path, "url:", repo.href

            if len(repo.codeModulePaths) > 0:
                print "Code module paths:"
                for path in repo.codeModulePaths:
                    print path
            if len(repo.componentPaths) > 0:
                print "Component paths:"
                for path in repo.componentPaths:
                    print path
            print "----"
