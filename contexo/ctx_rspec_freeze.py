###############################################################################
#                                                                             #
#   ctx_rspec.py                                                              #
#   Component of Contexo Shell - (c) Scalado AB 2007                          #
#                                                                             #
#   Author:                                                                   #
#   Michal Pomorski                         #
#   ------------                                                              #
#                                                                             #
#   RSpec Classes.                                                            #
#                                                                             #
#   Support:                                                                  #
#                                                                             #
#   20080519 - RSpec format version 0.1                                       #
#                                                                             #
###############################################################################

from xml.sax            import  make_parser
from xml.sax.handler    import  ContentHandler
from xml.sax.saxutils import XMLGenerator

from ctx_common         import userErrorExit, warningMessage, infoMessage
from ctx_common         import getVerboseLevel, ctxAssert, getUserTempDir
from contexo                import ctx_svn_client
import os.path
import sys


class RspecFreezer():
    #repositories is a dict of names and CTXRepo objects
    def __init__ (self,  repositories,  output = sys.stdout):
        self.default_version = "1"
        self.repos = repositories
        self.msgSender = "rspecRecursiveFreezer"
        self.xmlgenerator = XMLGenerator(output,'utf-8');
        self.svnclient = ctx_svn_client.CTXSubversionClient()

    #--------------------------------------------------------------------------
    def generateFrozen(self,  repo_names_to_freeze = None):
        self.xmlgenerator.startDocument()
        self.xmlgenerator.characters("\n")
        self.xmlgenerator.startElement('ctx-rspec',  attrs = {})
        self.xmlgenerator.characters("\n")
        for repo in self.repos:
            if repo_names_to_freeze == None:
                self.freezeRepo(repo)
            else:
                if repo.getID() in repo_names_to_freeze:
                    self.freezeRepo(repo)
        self.xmlgenerator.endElement('ctx-rspec')
        self.xmlgenerator.characters("\n")
        self.xmlgenerator.endDocument()
        #self.rspec.

    def freezeRepo(self,  repo):
        id = repo.getID()
        href = repo.getHref()
        rcs = repo.getRcs()
        path = repo.getPath()
        rev = repo.getRSpecRevision()
        repo_path = repo.getAbsLocalPath()
        #TODO: make it possible to base the freeze on an existing rspec (only freeze repos included in there)
        if (rcs == 'svn'):
            if rev == 'HEAD' or rev == None:
                curr_rev = self.svnclient.getRevisionFromWorkingCopy(repo_path)
            else:
                curr_rev = self.svnclient.getRevisionFromWorkingCopy(repo_path)
                if str(curr_rev) != rev:
                    warningMessage('%s: Overwriting strict revision nr %d with %d'%(id, int(rev),  curr_rev))
            self.xmlgenerator.characters("\t")
            self.xmlgenerator.startElement('ctx-repo',  attrs = {'id':id,'rcs':rcs, 'href': href,  'rev': str(curr_rev),  'path':path })
            self.xmlgenerator.characters("\n")
        else:
            warningMessage("Currently only supporting freeze for svn-repos, skipping '%s'"%repo_path)
            return
        paths = repo.getAllRelativePaths()
        for path_type in paths:
            for  path_spec in paths[path_type]:
                self.xmlgenerator.characters("\t\t")
                self.xmlgenerator.startElement('ctx-path',  attrs = {'type':path_type,  'spec':path_spec})
                self.xmlgenerator.endElement('ctx-path')
                self.xmlgenerator.characters("\n")
        self.xmlgenerator.characters("\t")
        self.xmlgenerator.endElement('ctx-repo')
        self.xmlgenerator.characters("\n\n")
