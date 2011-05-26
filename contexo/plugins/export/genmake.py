#!/usr/bin/python
###############################################################################
#                                                                             
#   genmake.py
#   Component of Contexo commandline tools - (c) Scalado AB 2010
#                                                                             
#   Author: Ulf Holmstedt (ulf.holmstedt@scalado.com)
#           Thomas Eriksson (thomas.eriksson@scalado.com)
#                                                                             
#   ------------
#                                                                             
#   Generate GNU Makefile from contexo sources
#                                                                             
###############################################################################
#
# Paul's Rules of Makefiles (from: http://mad-scientist.net/make/rules.html)
#
# 1. Use GNU make.
#    Don't hassle with writing portable makefiles, use a portable make instead!
#
# 2. Every non-.PHONY rule must update a file with the exact name of its target.
#    Make sure every command script touches the file "$@"-- not "../$@", or "$(notdir $@)", but exactly $@. That way you and GNU make always agree.
#
# 3. Life is simplest if the targets are built in the current working directory.
#    Use VPATH to locate the sources from the objects directory, not to locate the objects from the sources directory.
#
# 4. Follow the Principle of Least Repetition.
# Try to never write a filename more than once. Do this through a combination of make variables, pattern rules, automatic variables, and GNU make functions.
# 
# 5. Every non-continued line that starts with a TAB is part of a command script--and vice versa.
# If a non-continued line does not begin with a TAB character, it is never part of a command script: it is always interpreted as makefile syntax. If a non-continued line does begin with a TAB character, it is always part of a command script: it is never interpreted as makefile syntax.
# 
# Continued lines are always of the same type as their predecessor, regardless of what characters they start with.

from argparse import ArgumentParser
import os
import sys
import contexo.ctx_export as ctx_export
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_cmod

# use the same include directories for ALL source files when building
# however, only export public headers
# defaults to OFF
# may cause command line overflow
# may build incorrectly due to wrong header being selected
# but may be needed for netbeans
exearg = False
buildTests = False
linkHeaders = False
exe = str()

for arg in sys.argv:
    if arg == '-h':
        print 'help:'
        print '-l, symlink all headers to one directory and use that for include path'
        print '-t, build tests'
    if arg == '-t':
        buildTests = True
    if arg == '-l':
        linkHeaders = True

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list, depMgr):
    code_module_map = list()
    print 'mapping'
    for mod in ctx_module_list:
        #srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()
        depHdrDirs = set()
        depHdrs = set()

        rawMod = ctx_module_list[mod] #ctx_cmod.CTXRawCodeModule( mod )

        srcs = rawMod.getSourceAbsolutePaths()
        privHdrs= rawMod.getPrivHeaderAbsolutePaths()
        pubHdrs = rawMod.getPubHeaderAbsolutePaths()
	prebuiltSrcs = rawMod.getPreBuiltObjectAbsolutePaths()
        testSrcs = rawMod.getTestSourceAbsolutePaths()
        testHdrs = rawMod.getTestHeaderAbsolutePaths()
        modName = rawMod.getName()
        ## moduleDependencies[] only includes the top level includes, we must recurse through those to get all dependencies
        for hdr in  depMgr.moduleDependencies[modName]:
            hdr_location = depMgr.locate(hdr)
            if hdr_location != None:
                hdrpaths = depMgr.getDependencies(hdr_location)
                for hdrpath in hdrpaths:
					depHdrs.add( hdrpath)

        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(), 'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs, 'DEPHDRS':depHdrs, 'TESTDIR':rawMod.getTestDir(), 'PREBUILTSOURCES': prebuiltSrcs }
        code_module_map.append( modDict )


    return code_module_map
#------------------------------------------------------------------------------
#-- End of method declaration
#------------------------------------------------------------------------------


msgSender = 'Makefile Export'

contexo_config_path = os.path.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
infoMessage("Using config file '%s'"%contexo_config_path,  1)
cfgFile = ctx_cfg.CFGFile(contexo_config_path)
ctx_common.setInfoMessageVerboseLevel( int(cfgFile.getVerboseLevel()) )

infoMessage("Receiving export data from Contexo...", 1)
package = ctx_export.CTXExportData()
package.receive() # Reads pickled export data from stdin

for item in package.export_data.keys():
    infoMessage("%s: %s"%(item, str(package.export_data[item])))

# Retrieve build config from session
bc_file = package.export_data['SESSION'].getBCFile()
build_params = bc_file.getBuildParams()

depMgr = package.export_data['DEPMGR']

includeExtensions = ['.h','.inl','.hpp']
includes = set()

modules = package.export_data['MODULES']

if linkHeaders:
    for modulePath in modules:
        directories = [modulePath]
        while len(directories)>0:
            directory = directories.pop()
            for name in os.listdir(directory):
                item = os.path.join(directory,name)
                if name == 'src' and os.path.isdir(item) == True:
                    depMgr.addCodeModules( os.path.basename(directory), unitTests=True )
                if name.endswith('.h') and os.path.basename(directory) != 'inc':
                    depMgr.addCodeModules( os.path.basename(directory), unitTests=True )
                if os.path.isfile(item):
                    if item[item.rfind('.'):] in includeExtensions:
                        includes.add(item)
                elif os.path.isdir(item):
                    directories.append(item)
    depMgr.updateDependencyHash()
    if os.path.isfile('output'):
        userErrorExit('output must not be a file if using symlinks')
    if not os.path.isdir('output'):
        os.mkdir('output')
    hdrlinkOutputDir = 'output' + os.sep + 'hdrlinks'
    if not os.path.isdir(hdrlinkOutputDir):
        try:
            shutil.rmtree(hdrlinkOutputDir)
        except:
            pass
        os.mkdir('output' + os.sep + 'hdrlinks')
    for includeFile in includes:
        os.symlink(includeFile, 'output' + os.sep + 'hdrlinks' + os.sep + os.path.basename(includeFile))


module_map = create_module_mapping_from_module_list( package.export_data['MODULES'], depMgr)

if not os.path.isfile("Makefile.inc"):
	incmakefile = open("Makefile.inc", 'w')
	incmakefile.write("### inc_all is built after all other projects is built\n")
	incmakefile.write("### add dependencies for inc_all to add further build steps\n")
	incmakefile.write("inc_all: $(LIBS)\n")
	incmakefile.write("\ttouch $@\n\n")
	incmakefile.write("### add dependencies for inc_clean to add further clean steps\n")
	incmakefile.write("inc_clean:\n")
	incmakefile.write("\ttouch $@\n")

# Start writing to the file - using default settings for now
makefile = open("Makefile", 'w')

# File header
makefile.write("#############################################\n")
makefile.write("### Makefile generated with contexo plugin.\n")

# config settings
if not os.path.isfile("Makefile.cfg"):
	cfgmakefile = open("Makefile.cfg", 'w')
	cfgmakefile.write("### Compiler settings\n")
	cfgmakefile.write("CC=gcc\n")
	cfgmakefile.write("CXX=g++\n")
	cfgmakefile.write("CFLAGS="+build_params.cflags+"\n")
	cfgmakefile.write("LDFLAGS=\n")
	cfgmakefile.write("\n# Additional compiler parameters, such as include paths\n")
	cfgmakefile.write("ADDFLAGS=\n")
	cfgmakefile.write("\n")
	cfgmakefile.write("AR=ar\n")
	cfgmakefile.write("RANLIB=ranlib\n")
	cfgmakefile.write("\n")
	cfgmakefile.write("LIBDIR=output/lib\n")
	cfgmakefile.write("OBJDIR=output/obj\n")
	cfgmakefile.write("HDRDIR=output/inc\n")
	cfgmakefile.write("\n")
	cfgmakefile.write("EXPORT_CMD=cp\n")
	cfgmakefile.write("\n")

makefile.write("\n")
makefile.write("### include user configured settings\n")
makefile.write("include Makefile.cfg\n")
makefile.write("\n")

if linkHeaders == True:
	makefile.write("### symlinked headers output dirn")
	makefile.write("INCLUDES=-I$(OUTPUT)/hdrlinks/")
	makefile.write("\n")

# Preprocessor defines
makefile.write("### Standard defines\n")
makefile.write("PREP_DEFS=")
for prepDefine in build_params.prepDefines:
	makefile.write("-D"+prepDefine+" ")
makefile.write("\n")

libs = set()
for comp in package.export_data['COMPONENTS']:
	libs = set.union( libs, comp.libraries)

# LIBS definition
makefile.write("### Build-all definition\n")
makefile.write("LIBS =")
for lib in libs:
	makefile.write(" "+"$(LIBDIR)/"+lib+".a")
makefile.write("\n")

# "all" definition
makefile.write("\n")
makefile.write("### Build-all definition\n")
makefile.write("all: $(OBJDIR) $(HDRDIR) $(LIBDIR) $(LIBS)")
# add user configurable target in Makefile.inc
makefile.write(" inc_all")
makefile.write("\n")
makefile.write("clean: inc_clean\n")
makefile.write("\trm -f $(OBJDIR)/*.o\n")
makefile.write("\trm -f $(LIBDIR)/*.a\n")
makefile.write("\trm -f $(HDRDIR)/*.h\n")
makefile.write("\n")

makefile.write("\n")
makefile.write("### include user configured targets\n")
makefile.write("include Makefile.inc\n")
makefile.write("\n")


modules = package.export_data['MODULES']

headerDict = dict()
for modName in modules:
	module = modules[modName]
	files = module.getPubHeaderAbsolutePaths()
	for f in files:
		headerDict[os.path.basename(f)] = f

# create directories
makefile.write("\n")
makefile.write("### create directories\n")
makefile.write("$(OBJDIR):\n")
makefile.write("\tmkdir -p $@\n")
makefile.write("$(LIBDIR):\n")
makefile.write("\tmkdir -p $@\n")
makefile.write("$(HDRDIR):\n")
makefile.write("\tmkdir -p $@\n")
makefile.write("\n")

# TODO: this matches duplicate libraries (when libraries in components overlap)
# component definitions
makefile.write("\n")
makefile.write("### Component definitions\n")
for comp in package.export_data['COMPONENTS']:
	headerFiles=set()
	for headerFile in comp.publicHeaders:
		headerFiles.add(headerFile)

	for lib in comp.libraries:
		objectfiles=list()
		libfilename=lib+".a"

		for libs in comp.libraries[lib]:
			for srcFile in modules[libs].getSourceFilenames():
				objectfiles.append("$(OBJDIR)/" + os.path.basename(srcFile[:-2])+".o ")
                        if buildTests == True:
            			for testFile in modules[libs].getTestSourceFilenames():
	        			objectfiles.append("$(OBJDIR)/" + os.path.basename(testFile[:-2])+".o ")

		makefile.write("$(LIBDIR)/"+libfilename+": ")
		for objfile in objectfiles:
			makefile.write(objfile+" ")
		makefile.write("\n")

		makefile.write("\t$(AR) r $@")
		for objfile in objectfiles:
			makefile.write(" " + objfile)
		makefile.write("\n")

		makefile.write("\t$(RANLIB) $@\n")

	makefile.write("\tmkdir -p $(HDRDIR) $(OBJDIR) $(LIBDIR)\n")
	for headerFile in headerFiles:
                if headerDict.has_key(headerFile):
                    makefile.write("\t$(EXPORT_CMD) "+headerDict[headerFile]+" $(HDRDIR)/"+headerFile+"\n")
                else:
                    warningMessage('Headerfile '+headerFile+' could not be located')
	makefile.write("\n")

makefile.write("\n")
makefile.write("### Object definitions\n")

for mod in module_map:
	for srcFile in mod['SOURCES']:
		objfile = os.path.basename(srcFile)[:-2]+".o"
		
		makefile.write("$(OBJDIR)/" + objfile + ": " + srcFile)
		for hdr in mod['DEPHDRS']:
			makefile.write(" " + hdr)
		makefile.write("\n")
                if srcFile[-4:] == '.cpp':
        		makefile.write("\t$(CXX) $(CFLAGS) $(ADDFLAGS)")
                else:
        		makefile.write("\t$(CC) $(CFLAGS) $(ADDFLAGS)")
		if linkHeaders == True:
			makefile.write(" $(INCLUDES)")
		else:
			for hdrdir in mod['DEPHDRS']:
				makefile.write(" -I"+os.path.dirname( hdrdir))
		makefile.write(" $(PREP_DEFS) -c "+srcFile+" -o $@\n");
	for prebuiltObjFile in mod['PREBUILTSOURCES']:
		objfile = os.path.basename(prebuiltObjFile)
		makefile.write("$(OBJDIR)/" + objfile + ": ")
		makefile.write("\n")
		makefile.write("\t$(EXPORT_CMD) " + prebuiltObjFile + " $@\n")
        if buildTests == True:
        	for testFile in mod['TESTSOURCES']:
	        	objfile = os.path.basename(testFile)[:-2]+".o"
		        privInclude = module.getName().upper()+"_PRIV"
		
		        makefile.write("$(OBJDIR)/" + objfile + ": " + testFile + " ")
		        for hdr in mod['DEPHDRS']:
			        makefile.write( " " + hdr)
        		makefile.write("\n")
                        if testFile[-4:] == '.cpp':
        	        	makefile.write("\t$(CXX) $(CFLAGS) $(ADDFLAGS)")
                        else:
                                makefile.write("\t$(CC) $(CFLAGS) $(ADDFLAGS)")
		        if linkHeaders == True:
			        makefile.write(" $(INCLUDES)")
        		else:
	        		for hdrdir in mod['DEPHDRS']:
		        		makefile.write(" -I"+os.path.dirname( hdrdir))
        		makefile.write(" $(PREP_DEFS)")
	        	for hdrdir in mod['DEPHDRS']:
		        	makefile.write(" -I"+os.path.dirname( hdrdir))
        		makefile.write(" -I"+module.getRootPath()+"/test/ -c "+testFile+" -o $@\n")
makefile.write("### End of Makefile\n")
makefile.write("\n")

makefile.close()
