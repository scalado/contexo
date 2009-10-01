
from xml.sax import saxutils
from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl

#pretty formating xml

class XMLGenerator:
    def __init__(self, output):
        self.output = output
        self.level = 0
        self.previous_was_end = False
        self.xmlgenerator = saxutils.XMLGenerator(output,'windows-1252');
        self.xmlgenerator.startDocument()
        self.xmlgenerator.characters('\n')
        #output.write ('<?xml version="1.0" encoding = "Windows-1252"?>\n')

    def startElement (self, tag, attributes = {}):
        if self.previous_was_end:
            pass
            #self.xmlgenerator.characters('\n')
        self.xmlgenerator.characters(multiplystring('\t', self.level))
        self.xmlgenerator.startElement(tag,  attributes)
        self.level += 1
        self.xmlgenerator.characters('\n')
        self.previous_was_end = False

    def endElement (self, tag):
        self.level -= 1
        self.xmlgenerator.characters(multiplystring('\t', self.level))
        self.xmlgenerator.endElement(tag)
        self.xmlgenerator.characters('\n')
        self.previous_was_end = True

    def element (self, tag, attributes = {}):
        self.xmlgenerator.characters(multiplystring('\t', self.level))
        self.xmlgenerator.startElement(tag,  attributes)
        self.xmlgenerator.endElement(tag)
        self.xmlgenerator.characters('\n')


    def characters(self, msg):
        self.xmlgenerator.characters(multiplystring('\t', self.level))
        self.xmlgenerator.characters(msg)
        self.xmlgenerator.characters('\n')
#        self.output (encoded_msg = saxutils.escape(msg).encode('UTF-8'))

def multiplystring( string,  times):
    ret = ''
    for i in range(0, times):
        ret += string
    return ret
