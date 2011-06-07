#! /usr/bin/env python
import sys
from internal_argparse import ArgumentParser
import contexo.ctx_export as ctx_export
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import os
import contexo.ctx_bc
import contexo.ctx_cmod
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo

msgSender = 'MSVC Export'

default_projname = "MSVC_EXPORT"

contexo_config_path = os.path.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
infoMessage("Using config file '%s'"%contexo_config_path,  1)
cfgFile = ctx_cfg.CFGFile( contexo_config_path)
ctx_common.setInfoMessageVerboseLevel( int(cfgFile.getVerboseLevel()) )

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list ):

    code_module_map = list()

    for mod in ctx_module_list:
        srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()

        rawMod = mod #ctx_cmod.CTXRawCodeModule( mod )

        srcs = rawMod.getSourceAbsolutePaths()
        privHdrs= rawMod.getPrivHeaderAbsolutePaths()
        pubHdrs = rawMod.getPubHeaderAbsolutePaths()
        testSrcs = rawMod.getTestSourceAbsolutePaths()

        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(),  'TESTSOURCES':testSrcs ,  'TESTDIR':rawMod.getTestDir()}
        code_module_map.append( modDict )

    return code_module_map

#------------------------------------------------------------------------------
def allComponentModules( component_list ):

    modules = list()
    for comp in component_list:
        for lib, libmods in comp.libraries.iteritems():
            modules.extend( libmods )

    return modules

#------------------------------------------------------------------------------
def cmd_parse( args ):
    import string
    infoMessage("Receiving export data from Contexo...", 1)
    package = ctx_export.CTXExportData()
    package.receive() # Reads pickled export data from stdin

    infoMessage("Received export data:", 4)
    for item in package.export_data.keys():
        infoMessage("%s: %s"%(item, str(package.export_data[item])), 4)

    # Retrieve build config from session
    #bc_file =  package.export_data['SESSION'].getBCFile()

    #build_params = bc_file.getBuildParams()

    #tests = package.export_data['TESTS']

    module_dicts = create_module_mapping_from_module_list( package.export_data['MODULES'].values() )

    def getFileContents(inputFilePath):
        f = open( inputFilePath, 'rb' )
        contents = f.read()
        f.close()
        return contents
    input_names = list ( args.input_names )

    #init the dict with input_names and empty lists
    allNames = dict( zip(input_names, [[] for i in range(len(input_names))] ) )

    for module in module_dicts:

        sources = module['SOURCES'] + module['TESTSOURCES']
        print 'Analysing %s in %s'%( map(os.path.basename,  sources),  module['MODNAME'] )
        def readNames(name):
            from contexo.ctx_cparser import parseTengilTests
            #Get a list of lists of testnames. One list of names for each source file.
            lista = map( lambda sourcefile: parseTengilTests( getFileContents(sourcefile),  name),   sources )
            #squash the list of lists into a simple list
            allNames[name] += reduce( lambda l1,l2: l1 + l2,  lista, [])
        map(readNames,  input_names)


    output_names = input_names if len(args.output_names) == 0 else list(args.output_names)
    if len(output_names) != len(input_names):
        userErrorExit("output names should map 1:1 to input names")
    nameMap = dict(zip(input_names,  output_names))

    outputfile = open( args.output ,'wb' )

    def writeName( (inname,  outname) ):
        def writeCall( arg ):
            outputfile.write( '%s(%s)\n'%( outname,  arg ) )
            print ( '   %s(%s)'%( outname,  arg ) )
        map(writeCall,  allNames[inname])
    map(writeName,  nameMap.items() )

    outputfile.close()


    #
    # The End
    #
    infoMessage("Export done.", 1)


##### ENTRY POINT #############################################################

# Create Parser
parser = ArgumentParser( description="""tengil testcase parser""",
 version="0.1")

parser.set_defaults(func=cmd_parse)

parser.add_argument('-in', '--input-names', nargs = '+',
 help="""names of the calls or macros to find""")

parser.add_argument('-on', '--output-names', default='',  nargs = '*',
 help="""names of the calls to generate""")

parser.add_argument('-o', '--output', default=os.getcwd(),
 help="The path to the output file.")



#parser.add_argument('-ld','--libdir', default="", help=standard_description['--libdir'])
#parser.add_argument('-l', '--lib', help="if the build operation results in a single library, this option sets its name")

args = parser.parse_args()
args.func(args)
