# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   ctx_svn_client.py                                                         #
#   Component of Contexo Core - (c) Scalado AB 2009                           #
#                                                                             #
#   Author: Robert Alm
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   PySVN/Subversion interface for Contexo                                          #                                                                             #                                                                             #
###############################################################################

from ctx_common import ctxAssert, userErrorExit, infoMessage, errorMessage
import os
import sys
import pysvn
from getpass import getpass
import urllib

# Mapping of state notification enums to display text.
# Empty strings for states we don't need to report
state_text = {
pysvn.wc_notify_state.inapplicable: '',
pysvn.wc_notify_state.unknown:      '',
pysvn.wc_notify_state.unchanged:    '',
pysvn.wc_notify_state.missing:      '(MISSING)',
pysvn.wc_notify_state.obstructed:   '(***OBSTRUCTED***)',
pysvn.wc_notify_state.changed:      '',
pysvn.wc_notify_state.merged:       '(MERGED)',
pysvn.wc_notify_state.conflicted:   '(***CONFLICTED***)'
}

# Mapping of action notification enums to display text
action_text = {
pysvn.wc_notify_action.delete:          'delete',
pysvn.wc_notify_action.failed_revert:   'failed_revert',
pysvn.wc_notify_action.resolved:        'resolved',
pysvn.wc_notify_action.restore:         'restore',
pysvn.wc_notify_action.revert:          'revert',
pysvn.wc_notify_action.skip:            '*SKIP*',
pysvn.wc_notify_action.status_completed: None,
pysvn.wc_notify_action.update_add:      'add',
pysvn.wc_notify_action.update_completed: None,
pysvn.wc_notify_action.update_delete:   'delete',
pysvn.wc_notify_action.update_update:   'update',
}

#
# PYSVN exception error codes
#

ERR_NOT_A_WORKING_COPY = 155007
ERR_HOST_UNRESOLVED    = 175002
ERR_INVALID_ARGUMENT   = 22

#
# pysvn callbacks
#

#------------------------------------------------------------------------------
def get_login( realm, username, may_save ):
    print "Subversion login"
    username = raw_input("user: ")
    password = getpass("pass: ")
    return True, username, password, True

#------------------------------------------------------------------------------
def ssl_server_trust_prompt( trust_dict ):
    return True, 0, False

#------------------------------------------------------------------------------
class CTXSubversionClient():
    def __init__(self):
        self.client = None
        self.msg_list = list()
        self.msgSender = "CTXSubversionClient"

        self.resetClient()

    #--------------------------------------------------------------------------
    def resetClient(self):
        self.client = pysvn.Client()
        self.client.callback_get_login = get_login
        self.client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
        self.client.callback_notify = self.svn_notify_callback
        self.client.exception_style = 1
        self.msg_list = list()

    #--------------------------------------------------------------------------
    # Returns true if the given local path is a local copy of a subversion
    # repository.
    #--------------------------------------------------------------------------
    def isWorkingCopy( self, local_path ):
        try:
            entry = self.client.info( local_path )
        except pysvn.ClientError, e:
            for message, code in e.args[1]:
                if code in [ERR_NOT_A_WORKING_COPY, ERR_INVALID_ARGUMENT]:
                    return False
                else:
                    ctxAssert( False, "Unhandled pysvn exception: (%d) %s. This code need to be updated." )

        return True

    #--------------------------------------------------------------------------
    # Returns true if the given (remote) URL is a known subversion repository.
    #--------------------------------------------------------------------------
    def isRepoURL( self, url ):
        return self.client.is_url( url )

    #--------------------------------------------------------------------------
    # Returns the subversion URL associated with the given working copy.
    #--------------------------------------------------------------------------
    def getURLFromWorkingCopy( self, lc_path ):
        if not os.path.exists(lc_path):
            userErrorExit( "Given path to local copy '%s' is invalid"%(lc_path), self.msgSender )

        entry = self.client.info( lc_path )
        #strip the %20-quotations from the url
        return urllib.unquote( entry['url'] ) if entry != None else None

    #--------------------------------------------------------------------------
    # Returns the revision of the given working copy
    #--------------------------------------------------------------------------
    def getRevisionFromWorkingCopy( self, lc_path ):
        if not os.path.exists(lc_path):
            userErrorExit( "Given path to local copy '%s' is invalid"%(lc_path), self.msgSender )

        entry = self.client.info( lc_path )

        if entry.revision.kind == pysvn.opt_revision_kind.head:
            return 'HEAD'
        elif entry.revision.kind == pysvn.opt_revision_kind.number:
            return entry.revision.number
        else:
            ctxAssert( False, "Unhandled pysvn revision kind" )

    #--------------------------------------------------------------------------
    # Returns the revision of the given working copy
    #--------------------------------------------------------------------------
    def getRevisionFromURL( self, url ):
        url = urllib.quote(url,  safe=',~=!@#$%^&*()+|}{:?><;[]\\/')
        entry = self.client.info2( url )
        ctxAssert( entry[0][1]['rev'].kind == pysvn.opt_revision_kind.number, "Revision of URL is not a number" )
        return entry[0][1]['rev'].number

    #--------------------------------------------------------------------------
    #
    #--------------------------------------------------------------------------
    def updateWorkingCopy( self, lc_path, rev ):
        self.resetClient()

        if not self.isWorkingCopy( lc_path ):
            userErrorExit( "Unable to update '%s'. Not a valid working copy."\
                           %(lc_path), self.msgSender )

        if rev.upper() == 'HEAD':
            rev = pysvn.Revision(pysvn.opt_revision_kind.head )
        else:
            rev = pysvn.Revision(pysvn.opt_revision_kind.number, rev )

        try:
            self.client.update( path=lc_path, recurse=True, revision=rev )

        except pysvn.ClientError, e:
            for message, code in e.args[1]:
                if code in [ERR_HOST_UNRESOLVED,]:
                    errorMessage("Unable to resolve host '%s'. Proceeding.. "\
                                  %(self.getURLFromWorkingCopy(lc_path)))
                else:
                    userErrorExit( "Unknown failure when updating '%s'\nPYSVN Exception:\n%s (%d)"%(lc_path, message, code), self.msgSender )


    #--------------------------------------------------------------------------
    # Checks out the given revision of the remote file or folder specified by
    # 'url' to the given local directory.
    #--------------------------------------------------------------------------
    def checkout( self, url, local_directory, revision ):
        self.resetClient()

        if self.isWorkingCopy( local_directory ):
            userErrorExit( "Unable to checkout '%s', given target directory '%s' is an existing working copy."\
                           %(url, local_directory), self.msgSender )

        if not self.isRepoURL(url):
            userErrorExit( "Invalid SVN repository: '%s'"%(url), self.msgSender )

        if revision.upper() == 'HEAD':
            rev = pysvn.Revision(pysvn.opt_revision_kind.head )
        else:
            rev = pysvn.Revision(pysvn.opt_revision_kind.number, revision )

        if not os.path.isdir(local_directory):
            userErrorExit( "Checkout destination '%s' is not a directory"%(local_directory), self.msgSender )

        try:
            #pysvn checkout seems to have a problem when spaces are not escaped but also when other characters are escaped
            url = urllib.quote(url,  safe=',~=!@#$%^&*()+|}{:?><;[]\\/')
            self.client.checkout(url=url, path=local_directory, recurse=True, revision=rev)
        except pysvn.ClientError, e:
            for message, code in e.args[1]:
                if code in [ERR_HOST_UNRESOLVED,]:
                    errorMessage("Unable to resolve host '%s'. Proceeding.. "%(url))
                else:
                    userErrorExit( "Unknown failure when checking out '%s'\nPYSVN Exception:\n%s (%d)"%(url, message, code), self.msgSender )


    #--------------------------------------------------------------------------
    # Checks out the given revision of the remote file or folder specified by
    # 'url' to the given local directory.
    #--------------------------------------------------------------------------
    def export( self, url, local_directory, revision ):
        self.resetClient()

        if not self.isRepoURL(url):
            userErrorExit( "Invalid SVN repository: '%s'"%(url), self.msgSender )

        if revision.upper() == 'HEAD':
            rev = pysvn.Revision(pysvn.opt_revision_kind.head )
        else:
            rev = pysvn.Revision(pysvn.opt_revision_kind.number, revision )

        if not os.path.isdir( local_directory ):
            os.makedirs( local_directory )
        elif self.isWorkingCopy( local_directory ):
            userErrorExit( "Export destination '%s' is an existing working copy"%(local_directory), self.msgSender )


        export_dest = os.path.join( local_directory, os.path.basename(url) )

        try:
            self.client.export(src_url_or_path=url, dest_path=export_dest, force=False, revision=rev)
        except :
            userErrorExit( "Exception caught from pysvn: \n%s"%(sys.exc_value), self.msgSender )

    #--------------------------------------------------------------------------
    #--------------------------------------------------------------------------
    def svn_notify_callback( self, event ):

        msg = None

        if event['action'] == pysvn.wc_notify_action.update_completed:
            msg = "[SVN]: Operation complete at revision %s."\
                  %( str(event['revision'].number) \
                    if event['revision'].kind == pysvn.opt_revision_kind.number \
                    else '(unknown)' )


        elif event['path'] != '' and action_text[ event['action'] ] is not None:
            msg = '[SVN]: %s %s %s'%( action_text[ event['action'] ], state_text[ event['content_state'] ], event['path'])

        if msg is not None:
            self.msg_list.append( msg )
            print msg
