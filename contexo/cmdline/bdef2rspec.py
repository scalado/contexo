#!/usr/bin/env python
#
# Author: Christoffer Green, Scalado AB
#
from xml.dom.minidom import parse, parseString
import sys
import os
import shutil
from xml.dom.minidom import Document
import pysvn

if(len(sys.argv) < 3):
	print ">convertBDEFtoRSPEC.py BDEF_file.bdef outfile.rspec"
	exit()

def getChildrenByTagName(node, tagName):
    for child in node.childNodes:
        if child.nodeType==child.ELEMENT_NODE and (tagName=='*' or child.tagName==tagName):
            yield child	
	
def ssl_server_trust_prompt( trust_dict ):
    return True, trust_dict['failures'], True

def get_login( realm, username, may_save ):
    name = raw_input("Please enter your SVN username: ")
    password = getpass.getpass()
    return True, name, password, True

client = pysvn.Client()
client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt
client.callback_get_login = get_login

repositories = []
xml = parse(sys.argv[1])
basedef = xml.getElementsByTagName('basedef')[0]
for repository in getChildrenByTagName(basedef, 'repository'):
	repositories.append(repository)

baselines = getChildrenByTagName(basedef, 'baseline')
for baseline in baselines:
	baselineRepository = baseline.getElementsByTagName('repository')[0]
	bdef = baseline.getElementsByTagName('bdef')[0]
	bdefURL = baselineRepository.attributes["href"].value + "/" + bdef.attributes["path"].value 
	bdefText = client.cat(bdefURL)
	nxml = parseString(bdefText)
	basedef = nxml.getElementsByTagName('basedef')[0]
	for repository in getChildrenByTagName(basedef, 'repository'):
		repositories.append(repository)
	
doc = Document()
rspecXML = doc.createElement("ctx-rspec")
for repository in repositories:
	ctxrepoXML = doc.createElement("ctx-repo")
	ctxrepoXML.setAttribute("id", repository.attributes["id"].value)
	ctxrepoXML.setAttribute("rcs", "svn")
	ctxrepoXML.setAttribute("href", repository.attributes["href"].value)
	ctxrepoXML.setAttribute("rev", repository.attributes["rev"].value)
	for ctx in getChildrenByTagName(repository, 'ctx'):
		type = ctx.attributes["type"].value
		if(type != "BC"):
			ctxXML = doc.createElement("ctx-path")
			if(type == "COMP"):
				ctxXML.setAttribute("type", "comp")
			if(type == "MODULE"):
				ctxXML.setAttribute("type", "modules")
			path = ctx.attributes["path"].value.replace("\\", "/")
			if(path == ""):
				path = "./"
			ctxXML.setAttribute("spec", path)
			ctxrepoXML.appendChild(ctxXML)		
	rspecXML.appendChild(ctxrepoXML)
doc.appendChild(rspecXML)	
file = open(sys.argv[2], "w")
file.write(doc.toprettyxml())
file.close()

	
