#!/usr/bin/python

from argparse import ArgumentParser
import os
import contexo.ctx_export as ctx_export
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_cmod

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list ):

    code_module_map = list()
    for mod in ctx_module_list:
        #srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()

        rawMod = mod #ctx_cmod.CTXRawCodeModule( mod )

        srcs = rawMod.getSourceAbsolutePaths()
        privHdrs= rawMod.getPrivHeaderAbsolutePaths()
        pubHdrs = rawMod.getPubHeaderAbsolutePaths()
        testSrcs = rawMod.getTestSourceAbsolutePaths()
        testHdrs = rawMod.getTestHeaderAbsolutePaths()
        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(),  'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs,  'TESTDIR':rawMod.getTestDir()}
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

depRoots = package.export_data['PATHS']['MODULES']
incPaths = list()
for depRoot in depRoots:
    incPathCandidates = os.listdir( depRoot )

    for cand in incPathCandidates:
        path = os.path.join(depRoot, cand)
        if contexo.ctx_cmod.isContexoCodeModule( path ):
            incPaths.append( path )
            
module_map = create_module_mapping_from_module_list( package.export_data['MODULES'].values() )
modules = package.export_data['MODULES']

# Start writing to the file - using default settings for now
makefile = open("Makefile", 'w')

# File header
makefile.write("#############################################\n")
makefile.write("### Makefile generated with contexo plugin.\n")

# Standard compiler settings
makefile.write("CC=gcc\n")
makefile.write("CFLAGS="+build_params.cflags+"\n")
makefile.write("LDFLAGS=\n")
makefile.write("OBJ_TEMP=output/temp\n")
makefile.write("\n")
makefile.write("AR=ar\n")
makefile.write("RANLIB=ranlib\n")
makefile.write("LIB_OUTPUT=output/lib\n")
makefile.write("\n")
makefile.write("EXPORT_CMD=cp\n")
makefile.write("HEADER_OUTPUT=output/inc\n")
makefile.write("\n")
makefile.write("EXECUTABLE=hello\n")
makefile.write("\n")

# Preprocessor defines
makefile.write("### Standard defines\n");
makefile.write("PREP_DEFS=")
for prepDefine in build_params.prepDefines:
	makefile.write("-D"+prepDefine+" ")
makefile.write("\n")

# Standard include path (all files)
makefile.write("\n")
makefile.write("### Standard include paths\n");
makefile.write("STD_INCLUDE=")
for incPath in incPaths:
	makefile.write("-I"+incPath+" ")
makefile.write("\n")

# Module specific include paths (one for each module)
makefile.write("\n")
makefile.write("### Module specific include paths\n")
for modName in modules:
	module = modules[modName]
	makefile.write(module.getName().upper()+"_PRIV="+module.getPrivHeaderDir()+"\n")

# "all" definition
makefile.write("\n")
makefile.write("### Build-all definition\n")
makefile.write("all: ")
for comp in package.export_data['COMPONENTS']:
	for lib in comp.libraries:
		libfilename=lib+".a"
		makefile.write(libfilename+" ")
makefile.write("\n")
makefile.write("\n")
makefile.write("clean:\n")
makefile.write("\trm -f $(OBJ_TEMP)/*.o\n")
makefile.write("\trm -f $(LIB_OUTPUT)/*.a\n")
makefile.write("\trm -f $(HEADER_OUTPUT)/*.h\n")
makefile.write("\n")

headerDict = dict()
for modName in modules:
	module = modules[modName]
	files = module.getPubHeaderAbsolutePaths()
	for f in files:
		headerDict[os.path.basename(f)] = f

# component definitions
makefile.write("\n")
makefile.write("### Component definitions\n")
for comp in package.export_data['COMPONENTS']:
	headerFiles=list()
	for headerFile in comp.publicHeaders:
		headerFiles.append(headerFile)

	for lib in comp.libraries:
		objectfiles=list()
		libfilename=lib+".a"

		for libs in comp.libraries[lib]:
			for srcFile in modules[libs].getSourceFilenames():
				objectfiles.append(srcFile[:-2]+".o ")
			for testFile in modules[libs].getTestSourceFilenames():
				objectfiles.append(testFile[:-2]+".o ")

		makefile.write(libfilename+": ")
		for objfile in objectfiles:
			makefile.write(objfile+" ")
		makefile.write("\n")

		makefile.write("\t$(AR) r $(LIB_OUTPUT)/"+libfilename+" ")
		for objfile in objectfiles:
			makefile.write("$(OBJ_TEMP)/"+objfile+" ")
		makefile.write("\n")

		makefile.write("\t$(RANLIB) $(LIB_OUTPUT)/"+libfilename)
		makefile.write("\n")

	for headerFile in headerFiles:
		makefile.write("\t$(EXPORT_CMD) "+headerDict[headerFile]+" $(HEADER_OUTPUT)/"+headerFile+"\n")
	makefile.write("\n")

makefile.write("\n")
makefile.write("### Object definitions\n")

for modName in modules:
	module = modules[modName]
	
	for srcFile in module.getSourceAbsolutePaths():
		objfile = os.path.basename(srcFile)[:-2]+".o"
		privInclude = module.getName().upper()+"_PRIV"
		
		makefile.write(objfile + ":\n")
		makefile.write("\t$(CC) $(CFLAGS) $(STD_INCLUDE) $(PREP_DEFS) -I$("+privInclude+") -c "+srcFile+" -o $(OBJ_TEMP)/"+objfile+"\n");

	for testFile in module.getTestSourceAbsolutePaths():
		objfile = os.path.basename(testFile)[:-2]+".o"
		privInclude = module.getName().upper()+"_PRIV"
		
		makefile.write(objfile + ":\n")
		makefile.write("\t$(CC) $(CFLAGS) $(STD_INCLUDE) $(PREP_DEFS) -I$("+privInclude+") -I"+module.getRootPath()+"/test/ -c "+testFile+" -o $(OBJ_TEMP)/"+objfile+"\n");
makefile.write("### End of Makefile\n")
makefile.write("\n")

makefile.close()
