###############################################################################
#                                                                             #
#   ctx_log.py                                                                #
#   Component of Contexo Core - (c) Scalado AB 2006                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Log generator classes.                                                    #
#                                                                             #
###############################################################################

import os
import sys
import string
import shutil
import ctx_config
from ctx_common import *
from time import localtime, strftime


# --------- Predefined templates for log output xml tags ----------------------
xml_intro               = "<?xml version=\"1.0\" ?>\n\n"

xml_log_begin           = "<contexo_buildlog>\n"
xml_log_end             = "</contexo_buildlog>\n"

xml_datetime            = "<datetime>%s</datetime>\n\n"

xml_bc_begin            = "<bc bcfile=\"%s\">\n"
xml_compiler            = "  <compiler>%s</compiler>\n"
xml_cflags              = "  <cflags>%s</cflags>\n"
xml_prep                = "  <prep>%s</prep>\n"
xml_cmdline             = "  <cmdline>%s</cmdline>\n"
xml_bc_end              = "</bc>\n\n"

xml_components_begin    = "<components>\n"
xml_component           = "<comp name=\"%s\">\n%s\n%s\n</comp>\n"
xml_components_end      = "</components>\n\n"

xml_libraries_begin     = "<libraries>\n"
xml_lib                 = "  <lib name=\"%s\">\n%s      </lib>\n"
xml_libraries_end       = "</libraries>\n"

xml_codemods_begin      = "    <codemodules>\n"
xml_codemod             = "      <cm name=\"%s\">\n%s          </cm>\n"
xml_codemods_end        = "    </codemodules>\n"

xml_objfiles_begin      = "        <objfiles>\n"
xml_objfile             = "          <obj name=\"%s\" src=\"%s\"/>\n"
xml_objfiles_end        = "        </objfiles>\n"

xml_exports_begin       = "<exports>\n"
xml_exports_end         = "</exports>\n"

xml_headers_begin       = "  <headers>\n"
xml_header              = "    <hdr name=\"%s\"/>\n"
xml_headers_end         = "  </headers>\n"

xml_files_begin         = "  <files>\n"
xml_file                = "    <file name=\"%s\" type=\"%s\"/>\n"
xml_files_end           = "  </files>\n"

xml_errors_begin        = "<errors>\n"
xml_error               = "<err>%s</err>\n"
xml_errors_end          = "</errors>\n\n"

xml_messages_begin      = "<messages>\n"
xml_message             = "<msg>%s</msg>\n"
xml_messages_end        = "</messages>\n\n"
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
# \class {CTXLog}
#------------------------------------------------------------------------------
class CTXLog:
    def __init__(self):
        self.log = dict({\
              'datetime': strftime("%a, %d %b %Y %H:%M:%S", localtime()),\
                    'bc': dict({'compiler': str(), 'cflags': str(), 'prep': list(), 'commandline': str() }),\
            'components': list(),\
                'errors': list(),\
              'messages': list() })

        self.curComp    = 0
        self.curLib     = 0
        self.curCodemod = 0
        self.curObj     = 0

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def inComp( self ):
        return bool( self.curComp < len(self.log['components']) )

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newComp( self, name ):
        return dict({ 'name': name, 'libraries': list(), 'exports': dict({ 'headers':list(), 'files':list() }) })
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newLib( self, name ):
        return dict({ 'name': name, 'codemods': list() })
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newCodemod( self, name ):
        return dict({ 'name': name, 'objfiles': list() })
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newObjFile( self, name, src ):
        return dict({ 'name': name, 'src': src })
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newHeader( self, name ):
        return name
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newFile( self, name, type ):
        return name, type
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newError( self, errorMsg ):
        return errorMsg
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __newMessage( self, msg ):
        return msg


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def setBuildConfig( self, bcfile, compiler, cflags, prep, commandline = None ):
        self.log['bc']['bcfile']        = bcfile
        self.log['bc']['compiler']      = compiler
        self.log['bc']['cflags']        = cflags
        self.log['bc']['prep']          = prep
        self.log['bc']['commandline']   = commandline

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def beginComponent( self, name ):
        self.log['components'].append( self.__newComp(name) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def endComponent( self ):
        self.curComp    += 1
        self.curLib     = 0


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def beginLibrary( self, name ):
        if not self.inComp():
            self.beginComponent( '$none$' )

        self.log['components'][self.curComp]['libraries'].append( self.__newLib(name) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def endLibrary( self  ):
        self.curLib += 1
        self.curCodemod = 0


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def beginCodeModule( self, name ):
        self.log['components'][self.curComp]['libraries'][self.curLib]['codemods'].append( self.__newCodemod(name) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def endCodeModule( self  ):
        self.curCodemod += 1
        self.curObj     = 0

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def beginObjectFile( self, name, src ):
        self.log['components'][self.curComp]['libraries'][self.curLib]['codemods'][self.curCodemod]['objfiles'].append( self.__newObjFile(name, src) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def endObjectFile( self  ):
        self.curObj += 1
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addObjectFile( self, name, src):
        self.beginObjectFile( name, src )
        self.endObjectFile()

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addExportHeader( self, name ):
        self.log['components'][self.curComp]['exports']['headers'].append( self.__newHeader(name) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addExportFile( self, name, type = "unknown" ):
        self.log['components'][self.curComp]['exports']['files'].append( self.__newFile(name, type) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addError( self, errorMsg ):
        self.log['errors'].append( self.__newError(errorMsg) )
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def addMessage( self, msg ):
        self.log['messages'].append( self.__newMessage(msg) )


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getMessagesAsXML( self, msgList ):
        xmlbuf = str()
        for msg in msgList:
            xmlbuf += xml_message       %(msg)
        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getErrorsAsXML( self, errList ):
        xmlbuf = str()
        for err in errList:
            xmlbuf += xml_error        %(err)
        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getExportsAsXML( self, exports ):
        xmlbuf = str()

        xmlbuf += xml_exports_begin

        xmlbuf += xml_headers_begin
        for header in exports['headers']:
            xmlbuf += xml_header        %(header)
        xmlbuf += xml_headers_end

        xmlbuf += xml_files_begin
        for f, t in exports['files']:
            xmlbuf += xml_file          %(f, t)
        xmlbuf += xml_files_end

        xmlbuf += xml_exports_end

        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getObjFilesAsXML( self, objList ):
        xmlbuf = str()
        xmlbuf += xml_objfiles_begin
        for obj in objList:
            xmlbuf += xml_objfile       %(obj['name'], obj['src'])
        xmlbuf += xml_objfiles_end
        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getCodemodsAsXML( self, codemodList ):
        xmlbuf = str()
        xmlbuf += xml_codemods_begin
        for cm in codemodList:
            xmlbuf += xml_codemod       %(cm['name'], self.__getObjFilesAsXML(cm['objfiles']) )
        xmlbuf += xml_codemods_end
        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getLibsAsXML( self, libList ):
        xmlbuf = str()
        xmlbuf += xml_libraries_begin
        for lib in libList:
            xmlbuf += xml_lib           %(lib['name'], self.__getCodemodsAsXML(lib['codemods']) )
        xmlbuf += xml_libraries_end
        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getComponentsAsXML( self, compList ):
        xmlbuf = str()

        # If not actually building component(s) we still use a virtual component
        # in here to avoid the special case.
        virtualComponent = bool( len(compList) > 0 and compList[0]['name'] == '$none$' )


        if virtualComponent:
            for comp in compList:
                xmlbuf += self.__getLibsAsXML(comp['libraries'])
                xmlbuf += self.__getExportsAsXML(comp['exports'])

        else:
            xmlbuf += xml_components_begin
            
            for comp in compList:
                xmlbuf += xml_component     %( comp['name'], 
                                               self.__getLibsAsXML(comp['libraries']), 
                                               self.__getExportsAsXML(comp['exports']) )
            xmlbuf += xml_components_end

        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __getLogAsXML( self, log ):

        xmlbuf = str()

        xmlbuf += xml_intro
        xmlbuf += xml_log_begin

        xmlbuf += xml_datetime%( log['datetime'] )

        xmlbuf += xml_bc_begin  %( log['bc']['bcfile'] )
        xmlbuf += xml_compiler  %( log['bc']['compiler'] )
        xmlbuf += xml_cflags    %( log['bc']['cflags'] )
        xmlbuf += xml_prep      %( string.join( log['bc']['prep'], ';' ) )
        xmlbuf += xml_cmdline   %( log['bc']['commandline'] )
        xmlbuf += xml_bc_end

        xmlbuf += xml_errors_begin
        xmlbuf += self.__getErrorsAsXML( log['errors'] )
        xmlbuf += xml_errors_end

        xmlbuf += xml_messages_begin
        xmlbuf += self.__getMessagesAsXML( log['messages'] )
        xmlbuf += xml_messages_end

        xmlbuf += self.__getComponentsAsXML( log['components'] )

        xmlbuf += xml_log_end

        return xmlbuf

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def generateXMLBuffer( self ):

        if self.inComp():
            if self.log['components'][self.curComp]['name'] == '$none$':
                self.endComponent()
            else:
                ctxAssert( False, "CTXLog component not ended when log generator is invoked" )


        return self.__getLogAsXML( self.log )


    #--------------------------------------------------------------------------
    def writeToFile( self, filepath, appendToExisting = True ):

        mode = 'w'
        if os.path.exists(filepath) and appendToExisting:
            mode = 'a'

        f = file( filepath, mode )
        f.write( self.generateXMLBuffer() )
        f.close()

    #--------------------------------------------------------------------------
    def writeToConsole( self ):
        print self.generateXMLBuffer()

ctxlog = None
logEnabled = False
#------------------------------------------------------------------------------
# Global wrapper functions
#------------------------------------------------------------------------------
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogStart():
    global logEnabled
    global ctxlog
    logEnabled = True
    if ctxlog == None:
        ctxlog = CTXLog()
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogStop():
    global logEnabled
    logEnabled = False
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogSetBuildConfig( bcfile, compiler, cflags, prep, commandline = None ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.setBuildConfig( bcfile, compiler, cflags, prep, commandline )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogBeginComponent( name ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.beginComponent( name )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogEndComponent():
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.endComponent()
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogBeginLibrary( name ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.beginLibrary( name )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogEndLibrary():
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.endLibrary()
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogBeginCodeModule( name ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.beginCodeModule( name )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogEndCodeModule():
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.endCodeModule()
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogAddObjectFile( name, src):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.addObjectFile( name, src )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogAddExportHeader( name ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.addExportHeader( name )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogAddExportFile( name, type = "unknown" ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.addExportFile(name, type)
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogAddError( errorMsg ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.addError(errorMsg)
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogAddMessage( msg ):
    global logEnabled
    global ctxlog
    if logEnabled:
        ctxlog.addMessage( msg )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogWriteToFile( filepath, appendToExisting = True ):
    global ctxlog
    if ctxlog != None:
        ctxlog.writeToFile( filepath, appendToExisting )
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def ctxlogWriteToConsole():
    global ctxlog
    if ctxlog != None:
        ctxlog.writeToConsole()
