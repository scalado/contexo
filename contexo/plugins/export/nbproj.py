#!/usr/bin/python
###############################################################################
#                                                                             #
#   nbproj.py                                                                 #
#   Component of Contexo Core - (c) Scalado AB 2010                           #
#                                                                             #
#   Author: Johannes Strömberg (johannes.stromberg@scalado.com)               #
#           Thomas Eriksson    (thomas.eriksson@scalado.com)                  #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Netbeans 6.9 export plugin                                                #
#                                                                             #
###############################################################################
# -*- coding: utf-8 -*-

from internal_argparse import ArgumentParser
import contexo.ctx_export as ctx_export
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import os
import contexo.ctx_bc
import contexo.ctx_cmod
import contexo.ctx_netbeans
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo

msgSender = 'Netbeans Export'

default_projname = "NETBEANS_EXPORT"

contexo_config_path = os.path.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
infoMessage("Using config file '%s'"%contexo_config_path,  1)
cfgFile = ctx_cfg.CFGFile( contexo_config_path)
ctx_common.setInfoMessageVerboseLevel( int(cfgFile.getVerboseLevel()) )

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list, depMgr):
    code_module_map = list()
    print 'mapping'
    for mod in ctx_module_list:
        #srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()
        depHdrDirs = set()

        rawMod = ctx_module_list[mod] #ctx_cmod.CTXRawCodeModule( mod )

        srcs = rawMod.getSourceAbsolutePaths()
        privHdrs= rawMod.getPrivHeaderAbsolutePaths()
        pubHdrs = rawMod.getPubHeaderAbsolutePaths()
        testSrcs = rawMod.getTestSourceAbsolutePaths()
        testHdrs = rawMod.getTestHeaderAbsolutePaths()
        modName = rawMod.getName()
        ## moduleDependencies[] only includes the top level includes, we must recurse through those to get all dependencies
        for hdr in  depMgr.moduleDependencies[modName]:
            hdr_location = depMgr.locate(hdr)
            if hdr_location != None:
                hdrpaths = depMgr.getDependencies(hdr_location)
                for hdrpath in hdrpaths:
                    depHdrDirs.add( os.path.dirname( hdrpath ))

        #modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(),  'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs,  'TESTDIR':rawMod.getTestDir()}
        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(), 'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs, 'DEPHDRDIRS':depHdrDirs,'TESTDIR':rawMod.getTestDir()}        
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
    bc_file =  package.export_data['SESSION'].getBCFile()
    build_params = bc_file.getBuildParams()

    tests = package.export_data['TESTS']

    #
    # Add module paths/repositories as include directories
    #

    modTags     = list()
    incPaths    = list()

    # TODO: the preprocessor define COMPILING_MOD_ is a legacy definition,
    # initially created to make sure private headers were not included in a
    # project.
    # DO NOT REMOVE until all previous releases compiles without it.
    # /thomase
    depRoots    = package.export_data['PATHS']['MODULES']
    for depRoot in depRoots:
        incPathCandidates = os.listdir( depRoot )
        for cand in incPathCandidates:
            path = os.path.join(depRoot, cand)
            if contexo.ctx_cmod.isContexoCodeModule( path ):
                rawMod = contexo.ctx_cmod.CTXRawCodeModule(path)
                modTags.append( 'COMPILING_MOD_' + string.upper( rawMod.getName() ) )

    #
    # Collect additional include paths and additional library paths
    #

    def getPathsFromOption(option):
        user_paths = list()
        if os.path.isdir( option ):
            user_paths.append(option)
        elif not os.path.isfile( option ):
            userErrorExit("Cannot find option file or directory'%s'"%option)
        else:
            file = open( option, "r" )
            for line in file.readlines():
                line = line.strip()
                user_paths += line.split(";")
            file.close()
            user_paths = filter(lambda x: x.strip(" ") != '',user_paths)
        dirname = os.path.abspath(os.path.dirname(filename))
        return map (lambda path: os.path.join(dirname,  path),  user_paths)

    if args.additional_includes != None:
        filename = args.additional_includes
        user_includepaths = getPathsFromOption(filename)
        #dirname = os.path.dirname(filename)
        for inc in user_includepaths:
            incPaths.append(inc)

    #
    # Determin if we're exporting components or modules, and do some related
    # sanity checks
    #

    comp_export = bool( package.export_data['COMPONENTS'] != None )

    if comp_export:
    #Exporting components
        pass
    else:
    # Exporting modules

        if package.export_data['MODULES'] == None:
            userErrorExit( "No components or modules specified for export.")

    #
    # If exporting components and the user specified --mirror-components we
    # create one vcproj per component library, otherwise we create one large
    # library of all code modules.
    #

    projList = list() # list of dict['PROJNAME':string, 'LIBNAME':string, 'MODULELIST':listof( see doc of make_libvcproj7 ) ]

    # Regardless if we export components or modules, all modules are located in export_data['MODULES']
    depMgr = package.export_data['DEPMGR']
    module_map = create_module_mapping_from_module_list( package.export_data['MODULES'], depMgr)


    if not args.mergename:
        for comp in package.export_data['COMPONENTS']:
            for library, modules in comp.libraries.iteritems():
                lib_modules = [ ("",mod) for mod in module_map if mod['MODNAME'] in modules  ]
                projList.append( { 'PROJNAME': library, 'LIBNAME': library, 'MODULELIST': lib_modules } )
    else:
        lib_modules = []
        for comp in package.export_data['COMPONENTS']:
            for library, modules in comp.libraries.iteritems():
                lib_modules.extend([ (library,mod) for mod in module_map if mod['MODNAME'] in modules  ])
        projList.append( { 'PROJNAME': args.mergename, 'LIBNAME': args.mergename, 'MODULELIST': lib_modules } )

    #
    # Generate the projects
    #

    if not os.path.exists( args.output ):
        os.makedirs( args.output )

    for proj in projList:
        #codeModules = listof dictionaries: { MODNAME: string, SOURCES: list(paths), PRIVHDRS: list(paths), PUBHDRS: list(paths), PRIVHDRDIR: string, TESTSOURCES:list }
        contexo.ctx_netbeans.make_libproj( proj['PROJNAME'],
                                            build_params.cflags,
                                            build_params.prepDefines + modTags,
                                            proj['MODULELIST'],
                                            proj['LIBNAME'] + '.lib',
                                            tests,
                                            incPaths,
                                            args.output)


    #
    # The End
    #
    infoMessage("Export done.", 1)


##### ENTRY POINT #############################################################

# Create Parser
parser = ArgumentParser( description="""Netbeans project export -
 plugin to Contexo Build System (c) 2006-2010 Scalado AB""",
 version="0.1")

parser.set_defaults(func=cmd_parse)

parser.add_argument('-ai', '--additional-includes', default=None,
 help="""Directory, or path to a file with include paths to append to the include directories
 of all projects generated. The paths in the file can be separated by line
 or by semicolon.""")

parser.add_argument('-o', '--output', default=os.getcwd(),
 help="The output directory for the export.")

parser.add_argument('-mn', '--mergename', default=None,
 help="The project name for merged projects. If provided it will merge all the libs in all the comp files into one project.")

#parser.add_argument('-ld','--libdir', default="", help=standard_description['--libdir'])
#parser.add_argument('-l', '--lib', help="if the build operation results in a single library, this option sets its name")

args = parser.parse_args()
args.func(args)
