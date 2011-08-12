#!C:\Python26\python.exe
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

from internal_argparse import ArgumentParser
import os
import sys
import contexo.ctx_export as ctx_export
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_cmod
import shutil

exearg = False
buildTests = False
linkHeaders = False
exe = str()
relativeForwardSlashes = False

for arg in sys.argv:
    if arg == '-h':
        print >>sys.stderr, 'help:'
        print >>sys.stderr, '-l, symlink all headers to one directory and use that for include path'
        print >>sys.stderr, '-t, build tests'
        print >>sys.stderr, '-rfs, Relative build paths with Forward Slashes'
        sys.exit(1)
    if arg == '-t':
        buildTests = True
    if arg == '-l':
        linkHeaders = True
    if arg == '-rfs':
        relativeForwardSlashes = True


def dir_has_rspec(view_dir):
    view_filelist = os.listdir(view_dir)
    for entry in view_filelist:
        if entry.endswith('.rspec'):
            return True
    return False
orig_view_dir = os.path.abspath('')
view_dir = orig_view_dir
while not dir_has_rspec(view_dir):
    os.chdir('..')
    if view_dir == os.path.abspath(''):
        errorMessage('rspec not found, git ctx must be launched from a valid Contexo view')
        exit(2)
    view_dir = os.path.abspath('')
    os.chdir(view_dir)
os.chdir(orig_view_dir)


#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list, depMgr):
    code_module_map = list()
    print >>sys.stderr, 'mapping'
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
        subBCSrcs = rawMod.getSubBCSources()
        modName = rawMod.getName()
        ## moduleDependencies[] only includes the top level includes, we must recurse through those to get all dependencies
        for hdr in  depMgr.moduleDependencies[modName]:
            hdr_location = depMgr.locate(hdr)
            if hdr_location != None:
                hdrpaths = depMgr.getDependencies(hdr_location)
                for hdrpath in hdrpaths:
					depHdrs.add( hdrpath)

        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(), 'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs, 'DEPHDRS':depHdrs, 'TESTDIR':rawMod.getTestDir(), 'PREBUILTSOURCES': prebuiltSrcs, 'SUB_BC_SOURCES': subBCSrcs }
        code_module_map.append( modDict )


    return code_module_map
#------------------------------------------------------------------------------
#-- End of method declaration
#------------------------------------------------------------------------------


msgSender = 'Makefile Export'

if relativeForwardSlashes:
    sep = '/'
else:
    sep = os.sep


contexo_config_path = ctx_common.getUserCfgDir() + sep + ctx_sysinfo.CTX_CONFIG_FILENAME
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

lib_suffix = str()
lib_suffix = bc_file.getCompiler().cdef['LIBSUFFIX']

obj_suffix = str()
obj_suffix = bc_file.getCompiler().cdef['OBJSUFFIX']

inc_prefix = str()
inc_prefix = bc_file.getCompiler().cdef['INCPREFIX']
inc_suffix = str()
inc_suffix = bc_file.getCompiler().cdef['INCSUFFIX']


prep_prefix = str()
prep_prefix = bc_file.getCompiler().cdef['CPPDEFPREFIX']

modules = package.export_data['MODULES']


module_map = create_module_mapping_from_module_list( package.export_data['MODULES'], depMgr)

if linkHeaders:
    headers = set()
    for mod in module_map:
        headers |= set(mod['PUBHDRS'])
        headers |= set(mod['PRIVHDRS'])
        headers |= set(mod['DEPHDRS'])
        if buildTests:
            headers |= set(mod['TESTHDRS'])
    if os.path.isfile('output'):
        userErrorExit('output must not be a file if using symlinks')
    if not os.path.isdir('output'):
        os.mkdir('output')
    hdrlinkOutputDir = 'output' + sep + 'hdrlinks'
    shutil.rmtree(hdrlinkOutputDir,True)
    os.mkdir('output' + sep + 'hdrlinks')
    for header in headers:
        os.symlink(header, 'output' + sep + 'hdrlinks' + sep + os.path.basename(header))


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

ranlib = str()
if bc_file.getCompiler().cdef.has_key('RANLIB'):
    ranlib = bc_file.getCompiler().cdef['RANLIB']
else:
    ranlib = ""

ar = bc_file.getCompiler().cdef['AR']

# config settings
if not os.path.isfile("Makefile.cfg"):
	cfgmakefile = open("Makefile.cfg", 'w')
	cfgmakefile.write("### Compiler settings\n")
	cfgmakefile.write("CC=" + bc_file.getCompiler().cdef['CC'] + "\n")
	cfgmakefile.write("CXX=g++\n")
	cfgmakefile.write("CFLAGS="+build_params.cflags+"\n")
	cfgmakefile.write("LDFLAGS=\n")
        for subBCName,subBCObject in bc_file.getSubBC().iteritems():
            cfgmakefile.write(subBCName.upper() + '_CC=' + subBCObject.getCompiler().cdef['CC'] + '\n')
            cfgmakefile.write(subBCName.upper() + '_CFLAGS =' + subBCObject.getBuildParams().cflags + '\n')
	cfgmakefile.write("\n# Additional compiler parameters, such as include paths\n")
	cfgmakefile.write("ADDFLAGS=\n")
	cfgmakefile.write("\n")
	cfgmakefile.write("AR="+ar+"\n")
        if len(ranlib) > 0:
        	cfgmakefile.write("RANLIB=" + ranlib + "\n")
	cfgmakefile.write("\n")
	cfgmakefile.write("OUTPUT=output\n")
	cfgmakefile.write("LIBDIR=" + "$(OUTPUT)" + sep + "lib" + "\n")
	cfgmakefile.write("OBJDIR=" + "$(OUTPUT)" + sep + "obj"+ "\n")
	cfgmakefile.write("HDRDIR=" + "$(OUTPUT)" + sep + "inc" + "\n")
	cfgmakefile.write("\n")
    
	if os.name == 'nt' and not relativeForwardSlashes:
		cfgmakefile.write("EXPORT_CMD=copy\n")
		cfgmakefile.write("RM=del /S /Q\n")
		cfgmakefile.write("MKDIR=mkdir\n")
		cfgmakefile.write("TOUCH=copy nul\n")
	else:
		cfgmakefile.write("EXPORT_CMD=cp\n")
		cfgmakefile.write("RM=rm -rf\n")
		cfgmakefile.write("MKDIR=mkdir -p\n")
		cfgmakefile.write("TOUCH=touch\n")
        
	cfgmakefile.write("\n")

makefile.write("\n")
makefile.write("### include user configured settings\n")
makefile.write("include Makefile.cfg\n")
makefile.write("\n")

if linkHeaders == True:
	makefile.write("### symlinked headers output dir\n")
	makefile.write("INCLUDES="+inc_prefix+"$(OUTPUT)" + sep + "hdrlinks")+inc_suffix
	makefile.write("\n")

# Preprocessor defines
makefile.write("### Standard defines\n")
makefile.write("PREP_DEFS=")
for prepDefine in build_params.prepDefines:
	makefile.write(prep_prefix+prepDefine+" ")
makefile.write("\n")

libs = set()
for comp in package.export_data['COMPONENTS']:
	libs = set.union( libs, comp.libraries)

# LIBS definition
makefile.write("### Build-all definition\n")
makefile.write("LIBS =")
for lib in libs:
	makefile.write(" " + "$(LIBDIR)" + sep + lib + lib_suffix)
makefile.write("\n")

# "all" definition
makefile.write("\n")
makefile.write("### Build-all definition\n")
makefile.write("all: $(OBJDIR) $(HDRDIR) $(LIBDIR) $(LIBS)")
# add user configurable target in Makefile.inc
makefile.write(" inc_all")
makefile.write("\n")
makefile.write("clean: inc_clean\n")
makefile.write("\t$(RM) " + "$(OBJDIR)" + sep + "*"+obj_suffix + "\n")
makefile.write("\t$(RM) " + "$(LIBDIR)" + sep + "*"+lib_suffix + "\n")
makefile.write("\t$(RM) " + "$(HDRDIR)" + sep + "*.h" + "\n")
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
makefile.write("\t$(MKDIR) $@\n")
makefile.write("$(LIBDIR):\n")
makefile.write("\t$(MKDIR) $@\n")
makefile.write("$(HDRDIR):\n")
makefile.write("\t$(MKDIR) $@\n")
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
		libfilename=lib+lib_suffix

		for libs in comp.libraries[lib]:
			for srcFile in modules[libs].getSourceFilenames():
				objectfiles.append("$(OBJDIR)" + sep + os.path.basename(srcFile[:-2])+obj_suffix +" ")
                        if buildTests == True:
            			for testFile in modules[libs].getTestSourceFilenames():
	        			objectfiles.append("$(OBJDIR)" + sep + os.path.basename(testFile[:-2])+obj_suffix+" ")

                objfilestring = ""
		for objfile in objectfiles:
			objfilestring += objfile+" "

		makefile.write("$(LIBDIR)" + sep + libfilename+": ")
		makefile.write("$(HDRDIR) $(OBJDIR) $(LIBDIR) "+objfilestring+"\n")
                arcom = bc_file.getCompiler().cdef['ARCOM']
                if len(arcom) > 0:
                    cmdline = "\t" + arcom.lstrip() + "\n"
                    cmdline = cmdline.replace("%AR","$(AR)")
                    cmdline = cmdline.replace("%SOURCES",objfilestring)
                    cmdline = cmdline.replace("%TARGET","$@")
                else:
                    cmdline = "\t$(AR) r $@ " + objfilestring +"\n"
                if len(ranlib) > 0:
		    makefile.write("\t$(RANLIB) $@\n")

	
	for headerFile in headerFiles:
                if headerDict.has_key(headerFile):
                    if relativeForwardSlashes:
                        relHdr = headerDict[headerFile][len(view_dir)+1:].replace(os.sep, sep)
                    else:
                        relHdr = headerDict[headerFile]
                    makefile.write("\t$(EXPORT_CMD) "+ relHdr + " $(HDRDIR)" + sep + headerFile + "\n")
                else:
                    warningMessage('Headerfile '+headerFile+' could not be located')
	makefile.write("\n")

makefile.write("\n")
makefile.write("### Object definitions\n")

def write_build_command(srcFile = str(), test = False):
    objfile = os.path.basename(srcFile)[:-2]+obj_suffix
    if relativeForwardSlashes:
        relSrcFile = srcFile[len(view_dir)+1:].replace(os.sep,sep)
    else:
        relSrcFile = srcFile
    makefile.write("$(OBJDIR)" +sep+ objfile + ": " + relSrcFile)
    for hdr in mod['DEPHDRS']:
        if relativeForwardSlashes:
            relHdr = hdr[len(view_dir)+1:].replace(os.sep,sep)
        else:
            relHdr = hdr
        makefile.write(" " + relHdr)
    makefile.write("\n")
    cxx = "$(CXX)"
    cmdline = str()
    if srcFile[-4:] == '.cpp':
            cmdline = "\t" + bc_file.getCompiler().cdef['CXXCOM'].lstrip() + "\n"
    else:
            cmdline = "\t" + bc_file.getCompiler().cdef['CCCOM'].lstrip() + "\n"
            if srcFile in mod['SUB_BC_SOURCES'].values():
                    subBCName = os.path.basename(os.path.dirname(srcFile))
                    cc = "$(" + subBCName.upper() + "_CC)"
                    cflags = "$(" + subBCName.upper() + "_CFLAGS)"
            else:
                    cc = "$(CC)"
                    cflags = "$(CFLAGS)"
    cflags = cflags + " $(ADDFLAGS)"
    cppdefines = "$(PREP_DEFS)"
    incpaths = str()
    if relativeForwardSlashes:
        srcFile = srcFile[len(view_dir)+1:].replace(os.sep,sep)
    if linkHeaders == True:
            incpaths = " $(incpaths)"
    else:
            for hdrdir in mod['DEPHDRS']:
                relhdrdir = hdrdir
                if relativeForwardSlashes:
                    relhdrdir = os.path.dirname( hdrdir)[len(view_dir)+1:].replace(os.sep,sep)
                else:
                    relhdrdir = os.path.dirname( hdrdir)
                incpaths += " "+inc_prefix+ relhdrdir +inc_suffix
    if test:
        incpaths +=" " + inc_prefix+ module.getRootPath()+sep+"test"+inc_suffix

    cmdline.replace("%CC", "$(CC)")
    # Expand all commandline mask variables to the corresponding items we prepared.
    cmdline = cmdline.replace( '%CC'          ,   cc)
    cmdline = cmdline.replace( '%CXX'         ,   cxx)
    # not supported yet
    #cmdline = cmdline.replace( '%ASMFLAGS'   ,   asmflags_cmdline    )
    # not supported yet
    #cmdline = cmdline.replace( '%ASM'        ,   cdef['ASM']    )
    cmdline = cmdline.replace( '%CFLAGS'      ,   cflags)
    cmdline = cmdline.replace( '%CPPDEFINES'  ,   cppdefines )
    cmdline = cmdline.replace( '%INCPATHS'    ,   incpaths )
    cmdline = cmdline.replace( '%SOURCES'     ,   srcFile )
    # is this directive used?
    cmdline = cmdline.replace( '%TARGETDIR'   ,   "."           )
    # make specific
    cmdline = cmdline.replace( '%TARGETFILE'  ,   "$@" )
    cmdline = cmdline.replace( '%TARGET'      ,   "$@")

    makefile.write(cmdline)

for mod in module_map:
	for srcFile in mod['SOURCES']:
            write_build_command(srcFile = srcFile, test = False)
	for prebuiltObjFile in mod['PREBUILTSOURCES']:
                objfile = os.path.basename(prebuiltObjFile)
		makefile.write("$(OBJDIR)"+sep+objfile + ": ")
		makefile.write("\n")
		makefile.write("\t$(EXPORT_CMD) " + prebuiltObjFile + " $@\n")
        if buildTests == True:
        	for testFile in mod['TESTSOURCES']:
                    write_build_command(srcFile = testFile, test = True)
makefile.write("### End of Makefile\n")
makefile.write("\n")

makefile.close()
