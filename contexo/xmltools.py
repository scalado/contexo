
from xml.sax import saxutils


class XMLGenerator:
    def __init__(self, output):
        self.output = output

        output.write ('<?xml version="1.0" encoding = "Windows-1252"?>\n')

    def startElement (self, tag, attributes = None):
        self.output.write ('<'+tag)
        if attributes != None:
            self.output.write ('\n')
            for a in attributes:
                self.output.write (a[0] + '="' + a[1] + '"\n')
        self.output.write ('>\n')

    def endElement (self, tag):
        self.output.write('</'+tag+'>\n')

    def element (self, tag, attributes = None):
        self.output.write ('<'+tag)
        if attributes != None:
            self.output.write ('\n')
            for a in attributes:
                self.output.write (a[0] + '="' + a[1] + '"\n')
        self.output.write ('/>\n')

    def message (self, msg):
        self.output (encoded_msg = saxutils.escape(msg).encode('UTF-8'))
