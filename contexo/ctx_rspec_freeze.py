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


class rspecRevisionFreezer(ContentHandler):
    def __init__ (self,  output = sys.stdout):
        self.default_version = "1"
        self.msgSender = "rspecXmlFreezer"
        self.xmlgenerator = XMLGenerator(output,'utf-8');
        self.svnclient = ctx_svn_client.CTXSubversionClient()
        self.xmlgenerator.startDocument()

    #--------------------------------------------------------------------------
    def startElement(self, name, attrs):

        # .....................................................................
        if name == 'ctx-rspec':
         #   if self.parent_element.peek() != None:
         #       userErrorExit( "'<ctx-rspec>' can only be used as root element", self.msgSender )
            self.xmlgenerator.startElement(name,  attrs)
        # .....................................................................
        elif name == 'ctx-import':
            # Make sure this element is used in correct context
            #if self.parent_element.peek() != 'ctx-rspec':
             #   userErrorExit( "'%s' elements can only be used within '%s' elements"%(name, 'ctx-rspec'), self.msgSender )

            #
            # Digest import and check for errors/inconsistencies
            #

            href = attrs.get('href', None)
            if href == None:
                userErrorExit( "<ctx-import>: Missing mandatory attribute '%s' in RSpec '%s'"%('href', self.rspecFile.getFilename()), self.msgSender )

            rcs = attrs.get('rcs', None)
            if rcs == None and attrs.has_key('rev'):
                userErrorExit( "<ctx-import>: Revision ('rev') specified without specifying 'rcs' in RSpec '%s'"%(self.rspecFile.getFilename()), self.msgSender )

            rev = attrs.get('rev', None )
            if rcs != None and rev == None:
                warningMessage( "<ctx-import>: No revision specified for import in RSpec '%s'. Assuming 'HEAD'"%(self.rspecFile.getFilename()), self.msgSender )
                rev = 'HEAD'

            if (rcs == 'svn'):
                if rev == 'HEAD':
                    curr_rev = self.svnclient.getRevisionFromURL(href)
                else:
                    curr_rev = rev
                self.xmlgenerator.startElement(name, attrs = { 'rcs':rcs, 'href': href,  'rev': str(curr_rev) })
            # Prepare locator object and add import to current RSpec
            #rspecFileLocator = RSpecFileLocator( rcs, href, rev )
            #self.rspecFile.addImport( rspecFileLocator ) # POINT OF RECURSION

        # .....................................................................
        elif name == 'ctx-repo':

            # Make sure this element is used in correct context
           # if self.parent_element.peek() != 'ctx-rspec':
            #    userErrorExit( "'%s' elements can only be used within '%s' elements"%(name, 'ctx-rspec'), self.msgSender )

            # Make sure 'id' attribute is unique within RSpec
            #if attrs.has_key('id'):
              #  if in self.id_list:
               #     userErrorExit( "Multiple occurances of id '%s' in '%s'"%(attrs.get('id'), self.rspecFile.getFilename()), self.msgSender )
               # else:
               #     self.id_list.append(attrs.get('id'))
            rcs = attrs.get('rcs', None)
            href = attrs.get('href', "")
            path = attrs.get('path',  "")
            rev = attrs.get('rev', None )
            id = attrs.get('id',  None)
            repo_path = os.path.join(path, id)
            if (rcs == 'svn'):
                if rev == 'HEAD' or rev == None:
                    curr_rev = self.svnclient.getRevisionFromWorkingCopy(repo_path)
                else:
                    curr_rev = self.svnclient.getRevisionFromWorkingCopy(repo_path)
                    warningMessage( '%s: Overwriting strict revision nr %d with %d'%(id, int(rev),  curr_rev),   self.msgSender )


                self.xmlgenerator.startElement(name, attrs = {'id':id,'rcs':rcs, 'href': href,  'rev': str(curr_rev),  'path':path })

            else:
                userErrorExit("Currently only supporting freeze for svn",  self.msgSender)



        # .....................................................................
        elif name == 'ctx-path':

           # Make sure this element is used in correct context
            #if self.parent_element.peek() not in ['ctx-repo',]:
             #   userErrorExit( "'<%s>' elements cannot be used within '<%s>' elements"%(name, self.parent_element.peek()), self.msgSender )

            #
            # Assure presence of mandatory attributes
            #

            attribute = 'type'
            if not attrs.has_key(attribute):
                userErrorExit( "Missing mandatory attribute '%s' in element '<%s>'"%(attribute, name), self.msgSender )

            attribute = 'spec'
            if not attrs.has_key(attribute):
                userErrorExit( "Missing mandatory attribute '%s' in element '<%s>'"%(attribute, name), self.msgSender )

            self.xmlgenerator.startElement(name, attrs)


        # .....................................................................
        else:
            warningMessage( "Ignoring unknown element '<%s>' in RSpec.\nThis might be a normal compatibility issue."%(name), self.msgSender )



    #--------------------------------------------------------------------------
    def endElement(self, name):
        self.xmlgenerator.endElement(name)

    #depending on what is the current state,
    #put the character in the correct bin
    def characters (self, ch):
        self.xmlgenerator.characters(ch)
        #warningMessage( "Adding superflous character data '%s'"%(ch), self.msgSender )

    def endDocument(self):
        self.xmlgenerator.endDocument()
