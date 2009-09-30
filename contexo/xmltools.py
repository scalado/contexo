
from xml.sax import saxutils
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl

#TODO:remove this file

class XMLGenerator:
    def __init__(self, output):
        self.output = output
        self.xmlgenerator = saxutils.XMLGenerator(output,'windows-1252');
        self.xmlgenerator.startDocument()
        #output.write ('<?xml version="1.0" encoding = "Windows-1252"?>\n')

    def startElement (self, tag, attributes = {}):
        self.xmlgenerator.startElement(tag,  attributes)
#        self.output.write ('<'+tag)
#        if attributes != None:
#            self.output.write ('\n')
#            for a in attributes:
#                self.output.write (a[0] + '="' + a[1] + '"\n')
#        self.output.write ('>\n')

    def endElement (self, tag):
        self.xmlgenerator.endElement(tag)
#        self.output.write('</'+tag+'>\n')

    def element (self, tag, attributes = {}):
        self.startElement(tag, attributes)
        self.endElement(tag)
#        self.output.write ('<'+tag)
#        if attributes != None:
#            self.output.write ('\n')
#            for a in attributes:
#                self.output.write (a[0] + '="' + a[1] + '"\n')
#        self.output.write ('/>\n')

    def message (self, msg):
        self.xmlgenerator.characters(msg)
#        self.output (encoded_msg = saxutils.escape(msg).encode('UTF-8'))
