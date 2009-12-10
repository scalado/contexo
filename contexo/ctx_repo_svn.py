###############################################################################
#                                                                             #
#   ctx_repo_svn.py                                                           #
#   Component of Contexo Core - (c) Scalado AB 2007                           #
#                                                                             #
#   Author: manuel.astudillo@scalado.com                                      #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Implementation of CTXRepository for svn                                   #                                                                             #                                                                             #
###############################################################################

from ctx_repo import *
from ctx_common import ctxAssert, userErrorExit, infoMessage
import ctx_common
import ctx_svn_client
from getpass import getpass

#------------------------------------------------------------------------------
class CTXRepositorySVN(CTXRepository):
    def __init__(self, id_name, local_path, href, rev):
        self.client = ctx_svn_client.CTXSubversionClient()
        self.path = os.path.join(local_path, id_name)

        if href == None:
            # Try to get href from local copy
            href = self.client.getURLFromWorkingCopy( self.path )

        if href == None:
            userErrorExit("No HREF specified for repository '%s'. Failed to aquire HREF from local copy '%s'"\
                           %(id_name, self.path))

        CTXRepository.__init__( self, id_name, local_path, href, rev, version_control=True )
        self.msgSender = "CTXRepositorySVN"

    #--------------------------------------------------------------------------
    def isLocal(self):

        if os.path.isdir(self.getAbsLocalPath()):

            isWC = self.client.isWorkingCopy( self.getAbsLocalPath() )

            if isWC == False:
                warningMessage("Directory '%s' is the local representation of repository '%s', but is not a valid subversion repository."\
                                %(self.getAbsLocalPath(), self.getID() ))
                return False
            else:
                return True

        return False

    #--------------------------------------------------------------------------
    def update(self):
        ctxAssert( self.isLocal(),
                   "This method should not be called without first checking for an existing working copy." )

        infoMessage("Updating RSpec repository '%s' (%s)"%(self.getID(), self.getHref()), 1)

        self.client.updateWorkingCopy( self.getAbsLocalPath(), self.getRSpecRevision() )

    #--------------------------------------------------------------------------
    def checkout(self):
        ctxAssert( self.isLocal() == False,
                   "This method should not be called without first checking for an existing working copy." )

        infoMessage("Checking out RSpec repository '%s' (%s)"%(self.getID(), self.getHref()), 1)

        if not os.path.isdir(self.getAbsLocalPath()):
            os.makedirs( self.getAbsLocalPath() )

        self.client.checkout( self.getHref(), self.getAbsLocalPath(), self.getRSpecRevision() )

    def getRcs(self):
       return 'svn'

    #--------------------------------------------------------------------------
    # Always returns an exact revision as a number
    # (e.g. translates HEAD into to current revision)
    #--------------------------------------------------------------------------
    def getRevisionExact(self):
        base_rev = self.getRSpecRevision()
        if str(base_rev) == 'HEAD':
            base_rev = self.client.getRevisionFromURL( self.getHref() )

        return int(base_rev)

    #--------------------------------------------------------------------------
    def checkValidRevision(self):

        # Check if working copy exists at all
        if not self.isLocal():
            errorMessage("Local representation of repository '%s' (%s) doesn't exist. The view needs to be updated."\
                           %(self.getID(), self.getAbsLocalPath()))
            return False

        local_rev = self.client.getRevisionFromWorkingCopy( self.getAbsLocalPath() )
        base_rev = self.getRSpecRevision()
        if str(base_rev) == 'HEAD':
            base_rev = self.client.getRevisionFromURL( self.getHref() )

        if int(local_rev) != int(base_rev):
            errorMessage("Working copy of repository '%s' (revision %d) is not up-to-date with base revision %d."\
                          %(self.getID(), int(local_rev), int(base_rev)))
            return False

        return True

    #--------------------------------------------------------------------------
    def checkValid(self, updating ):

        #
        # Make sure the local represenation exists and has the correct URL (terminal error),
        # and check if working copy has same revision as rspec specifies (warning).
        #

        # Check if working copy exists at all
        if not self.isLocal() and not updating:
            errorMessage("Local representation of repository '%s' (%s) doesn't exist. The view needs to be updated."\
                           %(self.getID(), self.getAbsLocalPath()))
            return False

        # Check if repository URLs match
        if self.isLocal():
            url = self.client.getURLFromWorkingCopy( self.getAbsLocalPath() )
            if not ctx_common.areURLsEqual(url,  self.getHref() ):
                errorMessage("Inconsistent repository.\nWorking copy of repository '%s' originates from '%s', but the RSpec specifies '%s'"\
                              %(self.getID(), url, self.getHref()))
                return False

        # Check revision
        if not updating:
            return self.checkValidRevision()


        return True
