###############################################################################
#                                                                             #
#   ctx_repo.py                                                               #
#   Component of Contexo Core - (c) Scalado AB 2008                           #
#                                                                             #
#   Author: manuel.astudillo@scalado.com                                      #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Interface class for handling revisioned repositories.                     #
###############################################################################

import os.path
from ctx_common import *

REPO_PATH_SECTIONS = ['modules','cdef','bconf','comp', 'misc']

#------------------------------------------------------------------------------
class CTXRepository:
    def __init__( self, id_name, offset_path, href, rev, version_control  ):
        self.id_name = id_name
        self.href = href
        self.rev = rev
        self.offset_path = offset_path
        #self.rel_local_path = os.path.join(self.offset_path, id_name)
        self.abs_local_path = None
        self.relative_paths = dict() # This is path types provided via <ctx-path> items.
        self.version_control = version_control
        self.access_policy = None
        self.view_root = ""
        self.msgSender = "CTXRepository"

        if self.__class__ is CTXRepository:
            raise NotImplementedError

        for sec in REPO_PATH_SECTIONS:
            self.relative_paths[sec] = list()

        infoMessage("\n", 2)
        infoMessage("Repository added:\n   %s\n"\
                     %("\n   ".join(   ["                ID: " + str(self.getID()), \
                                        "              HREF: " + str(self.getHref()), \
                                        "        Local path: " + str(self.getRelLocalPath()), \
                                        "    RSpec revision: " + str(self.rev), \
                                        "Version controlled: %s"%( "Yes" if self.version_control else "No" ) ] )), 2)


    #--------------------------------------------------------------------------
    ######## Interface ############

    def isLocal(self):
        raise NotImplementedError

    # Updates the local copy
    def update(self):
        raise NotImplementedError

    # Checks out the local copy
    def checkout(self):
        raise NotImplementedError


    # Checks if the current revision is in sync
    def checkValidRevision(self):
        raise NotImplementedError

    # Checks if this repository is valid. If 'updating' is True, certain checks are
    # skipped. This is usually the case when validating during view update.
    def checkValid(self, updating ):
        raise NotImplementedError

    ##############################
    #--------------------------------------------------------------------------

    def getRcs(self):
        raise NotImplementedError

    #--------------------------------------------------------------------------
    def getID(self):
        return self.id_name

    #--------------------------------------------------------------------------
    def getPath(self):
        return self.offset_path
    #--------------------------------------------------------------------------
    def getHref(self):
        return self.href

    #--------------------------------------------------------------------------
    def getAbsLocalPath(self):
        ctxAssert( self.view_root != None and len(self.view_root) > 0, "Absolute local path has not been set yet" )
        return os.path.join( self.view_root, self.offset_path, self.id_name ) #self.abs_local_path

    #--------------------------------------------------------------------------
    # Returns the relative local path of the repository within the view
    #--------------------------------------------------------------------------
    def getRelLocalPath( self ):
        return os.path.join(self.offset_path, self.id_name)

    #--------------------------------------------------------------------------
    def getRSpecRevision( self ):
        return self.rev

    #--------------------------------------------------------------------------
#    def addAbsolutePath(self, path_section, path):
#        ctxAssert( path_section in REPO_PATH_SECTIONS, "Unknown path section '%s'"%(path_section) )
#        self.relative_paths[path_section].append( path )
#        infoMessage( "Path '%s' added to section '%s' in repository '%s'"%(path, path_section, self.getID()), 2, self.msgSender )

    #--------------------------------------------------------------------------
    def addPath(self, path_section, path):
        ctxAssert( path_section in REPO_PATH_SECTIONS, "Unknown path section '%s'"%(path_section) )
        if os.path.isabs(path):
            warningMessage("The absolute path %s will be treated as relative to the repository copy"%(path))
        path = path.lstrip('\\/ ')

        self.relative_paths[path_section].append( path )
        infoMessage("Path '%s' added to section '%s' in repository '%s'"%(path, path_section, self.getID()), 2)

    #--------------------------------------------------------------------------
    def getFullPaths( self, path_section ):
        from ctx_view import AP_PREFER_REMOTE_ACCESS, AP_NO_REMOTE_ACCESS

        ctxAssert( path_section in REPO_PATH_SECTIONS, "Unknown path section '%s'"%(path_section) )
        ctxAssert( self.access_policy != None, "No access policy was set for repository '%s'"%self.getID() )
        ctxAssert( self.view_root != None, "No view root path was set for repository '%s'"%self.getID() )

        full_paths = set()

        if self.access_policy == AP_PREFER_REMOTE_ACCESS and self.isVersionControlled() == False:
            for path in self.relative_paths[path_section]:
                full_paths.add( os.path.join(self.getHref(), path)  )

        elif self.access_policy == AP_NO_REMOTE_ACCESS or self.isVersionControlled() == True:
            for path in self.relative_paths[path_section]:
                full_paths.add( os.path.join(self.getAbsLocalPath(), path)   )
        else:
            ctxAssert( False, "Unhandled access policy" )

        return list(full_paths)

    #--------------------------------------------------------------------------
    def getRelativePaths( self, path_section ):
        ctxAssert( path_section in REPO_PATH_SECTIONS, "Unknown path section '%s'"%(path_section) )
        return self.relative_paths[path_section]

    def getAllRelativePaths( self):
        return self.relative_paths

    #--------------------------------------------------------------------------
    #def getAllPaths(self):
    #    all_paths = list()
    #    for plist in self.full_paths.values():
    #        all_paths.extend( plist )
    #
    #    return all_paths

    #--------------------------------------------------------------------------
    def isVersionControlled( self ):
        return self.version_control

    #--------------------------------------------------------------------------
    def setAccessPolicy( self, access_policy ):
        from ctx_view import AP_PREFER_REMOTE_ACCESS, AP_NO_REMOTE_ACCESS, AP_FLAGS

        self.access_policy = access_policy

        if not self.isVersionControlled() and self.access_policy == AP_PREFER_REMOTE_ACCESS:
            infoMessage("Repository '%s' will be used (built and/or accessed) from its remote source location '%s'.\n(Use option '%s' to force the system to access this repository from the local view)"\
                         %(self.getID(), self.getHref(), AP_FLAGS[AP_NO_REMOTE_ACCESS] ), 2)

    #--------------------------------------------------------------------------
    def getAccessPolicy(self):
        return self.access_policy

    #--------------------------------------------------------------------------
    def setViewRoot( self, view_root ):
        self.view_root = view_root

        if len(self.getHref()) == 0:
            self.href = self.getAbsLocalPath()
        self.relative_paths['modules'].append('.' )


    #--------------------------------------------------------------------------
    # Used to query the location of a certain build item which belongs
    # to a certain path section (module, bconf, cdef, etc).
    # This method implements the rules for how files are located within a
    # repository.
    # Returns a tuple with two elements, where the first element is a list
    # of paths (including item names) where the queried item exists, and the
    # second element is a list of paths (excluding item names) where this
    # method searched for the queried item.
    #--------------------------------------------------------------------------
    def locateItem( self, item, path_section ):

        local_paths = self.getFullPaths( path_section )
        remote_paths = list()
        tried_locations = list()
        candidate_locations = list()

        for path in local_paths:
            tried_locations.append( path )
            if not os.path.isdir(path):
                tried_locations[-1] += " (path not found)"
            else:
                if item in os.listdir(path):
                    candidate_locations.append( os.path.join(path, item) )

        # As a secondary measure, if this is a non version controlled
        # repository with regular file access, we try to locate the item
        # directly from the remote source of the repository.
        if len(candidate_locations) == 0 and not self.isVersionControlled():

            for relpath in self.getRelativePaths(path_section):
                remote_paths.append( os.path.join(self.getHref(), relpath) )

            for path in remote_paths:
                if os.path.isdir( path ):
                    tried_locations.append( path )
                    if item in os.listdir(path):
                        candidate_locations.append( os.path.join(path, item) )
                else:
                    warningMessage("Repository path '%s' doesn't exist"%(path))


        return (candidate_locations, tried_locations)


