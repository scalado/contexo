# -*- coding: utf-8 -*-

import os.path
import ntpath
from xmltools import XMLGenerator
#import pywintypes
import uuid

def relntpath(path, start):
    import ntpath #the windows version of os.path #available in python 2.6
#    return ntpath.relpath(path,  start)

    if start == None:
        start = os.getcwd()
    path = ntpath.normpath(path)
    start = ntpath.normpath(start)

    (drivep,  tailp) = ntpath.splitdrive(path)
    (drives,  tails) = ntpath.splitdrive(start)
    #if one of the paths has no drive letter, treat both of them so
    if (drivep == '' or drives == ''):
        path = tailp
        start = tails
    elif(drivep != drives):
        #ntpath.relpath returns error if drive letters differ, but we wont
        return path

    pathl  = path.replace("/", "\\").split('\\')
    startl = start.replace("/", "\\").split('\\')
    #print "path: %s, start:%s"%(path, start )
    while len(pathl) and len(startl) and pathl[0] == startl[0]:
            #print "removing "+pathl[0]
            del pathl[0]
            del startl[0]
    for i in range(len(startl)):
        pathl.insert(0, '..')

    return ntpath.join('.',  *pathl)





#codeModules = listof dictionaries: { MODNAME: string, SOURCES: list(paths), PRIVHDRS: list(paths), PUBHDRS: list(paths), PRIVHDRDIR: string, TESTSOURCES:list }
def make_libvcproj8( projectName, cflags, prepDefs, codeModules, outLib,
                    debug, do_tests,  incPaths, vcprojPath, platform = 'Win32',
                    fileTitle = None, configType = 'lib',
                     additionalDependencies = None,
                     additionalLibraryDirectories = None):


    import os.path
    vcprojFilePath = str()
    vcprojPath = os.path.abspath(vcprojPath)
    if fileTitle == None:
        fileTitle = projectName

    vcprojFilePath  = os.path.join( vcprojPath, fileTitle + ".vcproj" )
    vcprojFile      = open( vcprojFilePath, 'w')
    project         = XMLGenerator( vcprojFile )

    #GUID            = str(pywintypes.CreateGuid())
    GUID            = "".join(["{",str(uuid.uuid3(uuid.NAMESPACE_URL,"make_libvcproj8" + projectName)).upper(),"}"])

    #
    # Determine exe/lib
    #
    if configType == 'lib':
        configurationTypeNbr = '4'
    elif configType == 'exe':
        configurationTypeNbr = '1'
    else:
        print "Erroneous config type. Using 'lib'"
        configType = 'lib'
        configurationTypeNbr = '4'

    #
    # Determine debug/release
    #
    variant = str()
    if debug:
        variant = 'Debug'
    else:
        variant = 'Release'

    #
    # Determine DebugInformationFormat
    #
    debugInformationFormat = str()
    if platform == 'Win32':
        debugInformationFormat = '4'
    else:
        debugInformationFormat = '3'

    #
    # Prepare proprocessor definitions.
    #
    if type(prepDefs) == list:
        tmp = str()
        for d in prepDefs:
            tmp += d + ';'
        prepDefs = tmp


    project.startElement ('VisualStudioProject', {'ProjectType':'Visual C++',
                                                  'Version':'8,00',
                                                 'Name':projectName,
                                                 'RootNamespace':projectName,
                                                 'ProjectGUID':GUID,
                                                 'SccProjectName':'',
                                                  'SccLocalPath':''})

    project.startElement ('Platforms', {})

    project.element ('Platform', {'Name':platform})
    project.endElement ('Platforms')

    project.startElement ('Configurations', {})
    project.startElement ('Configuration', {'Name':variant+'|' + platform,
                                            'OutputDirectory':"".join(['.\\',variant,"\\",projectName]),
                                            'IntermediateDirectory':"".join(['.\\',variant,"\\",projectName]),
                                           'ConfigurationType':configurationTypeNbr,
                                           'UseOfMFC':'0',
                                            'CharacterSet':'1'})

    #
    # Compiler
    #

    if type(incPaths) != list:
        incPaths = split(";", incPaths)

    incPaths = [relntpath(path, vcprojPath) for path in incPaths]

    incPaths = ";".join(incPaths)

    compilerTool = {'Name':'VCCLCompilerTool',
                                  'PreprocessorDefinitions': prepDefs,
                                   'ObjectFile':"".join(['.\\',variant,"\\",projectName,'/']),
                                   'ProgramDataBaseFileName':"".join(['.\\',variant,"\\",projectName,'/']),
                                  'SuppressStartupBanner':'TRUE',
                                  'AdditionalIncludeDirectories':incPaths,
                                  'Optimization':'0',
                                   'DebugInformationFormat':debugInformationFormat}

    # Parse flags and add correct attributes in compiler tool.
    mycflags = cflags
    if type(mycflags) != list:
            mycflags = mycflags.split(' ')



    vcproj_opts_map = {
                    '/Zi':('DebugInformationFormat', '3'),
                    '/ZI':('DebugInformationFormat', '4'),
                    '/W4':('WarningLevel', '4'),
                    '/W3':('WarningLevel', '3'),
                    '/W2':('WarningLevel', '2'),
                    '/W1':('WarningLevel', '1'),
                    '/W0':('WarningLevel', '0'),
                    '/Od':('Optimization', '0'),
                    '/O1':('Optimization', '1'),
                    '/O2':('Optimization', '2')}

    # digest, analyse and remove options
    for opt in mycflags:
        try:
            (optionname,  numvalue) = vcproj_opts_map[opt]
            compilerTool[ optionname ] = numvalue
            mycflags.remove(opt)
            #print 'Digested %s'%opt
        except KeyError:
            #print 'Passing %s'%opt
            pass

    # Write the rest of the options as AdditionalOptions
    mycflags = " ".join(mycflags)
    compilerTool['AdditionalOptions'] = mycflags;

    # Write compilerTool to project
    project.element ('Tool',  compilerTool)

    #
    # Archiver
    #

    if configType == 'lib':
        project.element ('Tool', {'Name':'VCLibrarianTool',
                                   'OutputFile': '$(OutDir)/'+outLib})
    elif configType == 'exe':
        additionalDependencies = " ".join(map(ntpath.basename, additionalDependencies))
        additionalLibraryDirectories = " ".join(additionalLibraryDirectories)
        project.element ('Tool', {'Name':'VCLinkerTool',
                                  'GenerateDebugInformation':'TRUE',
                                  'TargetMachine':'1',
                                  'AdditionalDependencies':additionalDependencies,
                                  'AdditionalLibraryDirectories':additionalLibraryDirectories})
        project.element ('Tool', {'Name':'VCManifestTool'})
        project.element ('Tool', {'Name':'VCAppVerifierTool'})
        project.element ('Tool', {'Name':'VCWebDeploymentTool'})


    project.endElement ('Configuration')
    project.endElement ('Configurations')

    # Start module root folder.
    project.startElement ('Files')
    project.startElement ('Filter', {'Name':'Modules', 'Filter':''})


    #NOTE:
    #codeModules = listof dictionaries: { MODNAME: string, SOURCES: list(paths), PRIVHDRS: list(paths), PUBHDRS: list(paths), TESTSOURCES }
    for mod in codeModules:

        # Start module folder (public header goes here also)
        project.startElement ('Filter', {'Name': mod['MODNAME'],'Filter':''})


        # Start source file folder
        project.startElement ('Filter', {'Name': 'src','Filter':''})
        # Add all source files.
        for srcFile in mod['SOURCES']:
            project.startElement ('File', {'RelativePath': relntpath(srcFile, vcprojPath)})
            project.startElement('FileConfiguration',{'Name':"".join([variant,'|',platform])})
            project.element('Tool',{'Name':'VCCLCompilerTool','AdditionalIncludeDirectories':relntpath(mod['PRIVHDRDIR'], vcprojPath)})
            project.endElement ('FileConfiguration')
            project.endElement ('File')
            #project.startElement ('FileConfiguration', {'Name':variant+'|Win32'})
        # End source file folder
        project.endElement ('Filter')

        if do_tests:
            # Add test folder.
            project.startElement ('Filter', {'Name': 'tests','Filter':''})
            for src in mod['TESTSOURCES']:
                #project.characters('testsource:%s vcprojPath: %s'%(src, vcprojPath))
                project.startElement ('File', {'RelativePath':relntpath(src, vcprojPath)} )
                project.startElement('FileConfiguration',{'Name':"".join([variant,'|',platform])})
                project.element('Tool',{'Name':'VCCLCompilerTool','AdditionalIncludeDirectories':relntpath(mod['PRIVHDRDIR'], vcprojPath)})
                project.endElement ('FileConfiguration')
                project.endElement ('File')
            for hdr in mod['TESTHDRS']:
                project.element ('File', {'RelativePath':relntpath(hdr, vcprojPath)})

            project.endElement ('Filter')

        # Start private include folder
        project.startElement ('Filter', {'Name': 'inc','Filter':''})
        # Add all private headers.
        for hdr in mod['PRIVHDRS']:

            project.element ('File', {'RelativePath':relntpath(hdr, vcprojPath)})


        # End private include folder
        project.endElement ('Filter')


        # Add public headers to root.
        for hdr in mod['PUBHDRS']:
            #project.characters('header:%s vcprojPath: %s'%(hdr, vcprojPath))
            project.startElement ('File', {'RelativePath':relntpath(hdr, vcprojPath)} )
            project.endElement ('File')

        # End module folder
        project.endElement ('Filter')


    # End module root folder
    project.endElement ('Filter')

    project.endElement ('Files')

    project.endElement ('VisualStudioProject')

    vcprojFile.close ()

    return GUID


# name:string, path:string, projects:list( dict{ PROJNAME:string PROJGUID:string, DEBUG:True/False } ), exeproject: dict{ PROJNAME:string PROJGUID:string, DEBUG:True/False }
def make_solution8( name, path, projects, exeproject = None, platform = 'Win32' ):

    if not os.path.exists( path ):
        os.makedirs( path )

    if name[-4:].lower() != '.sln':
        name += '.sln'

    GUID = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"


    filePath = os.path.join( path, name )
    slnFile = open( filePath, "w" )

    slnFile.write( "Microsoft Visual Studio Solution File, Format Version 9.00\n# Visual Studio 2005" )

    prjTemplate = """
Project(\"%s\") = \"%s\", \"%s.vcproj\", \"%s\"
    ProjectSection(ProjectDependencies) = postProject
    EndProjectSection
EndProject"""
    #%( solution GUID, project name, project name, project GUID )


    for proj in projects:
        slnFile.write( prjTemplate%(GUID, proj['PROJNAME'], proj['PROJNAME'], proj['PROJGUID']) )

    exeprjTemplate = """
Project(\"%s\") = \"%s\", \"%s\", \"%s\"
    ProjectSection(ProjectDependencies) = postProject%s
    EndProjectSection
EndProject"""
    #%( solution GUID, project name, file name, project GUID, dependencies string )

    if exeproject:
        dependencies = "\n" + "\n".join(map(lambda p: p['PROJGUID'] + " = " + p['PROJGUID'],projects))
        slnFile.write( exeprjTemplate%(GUID, exeproject['PROJNAME'], exeproject['FILENAME'], exeproject['PROJGUID'], dependencies ))



    globalBegin = """
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
         Debug|%(platform)s = Debug|%(platform)s
         Release|%(platform)s = Release|%(platform)s
     EndGlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution"""

    slnFile.write( globalBegin%{'platform':platform} )




    globalPrjTemplate = """
        %s.%s.ActiveCfg = %s|%s
        %s.%s.Build.0 = %s|%s
    """
    #%( proj GUID, Debug/Release, Debug/Release, platform, proj GUID, Debug/Release, Debug/Release, platform )



    for proj in projects:
        confString = ""
        if proj['DEBUG']:
            confString = "Debug"
        else:
            confString = "Release"

        slnFile.write( globalPrjTemplate%(proj['PROJGUID'], confString, confString, platform,proj['PROJGUID'], confString, confString, platform) )


    if exeproject:
        confString = ""
        if exeproject['DEBUG']:
            confString = "Debug"
        else:
            confString = "Release"
        slnFile.write( globalPrjTemplate%(exeproject['PROJGUID'], confString, confString, platform,exeproject['PROJGUID'], confString, confString, platform) )



    globalEnd = """
    EndGlobalSection
    GlobalSection(ExtensibilityGlobals) = postSolution
    EndGlobalSection
    GlobalSection(ExtensibilityAddIns) = postSolution
    EndGlobalSection
EndGlobal"""

    slnFile.write( globalEnd )





    slnFile.close()

























def env2MSVS ( env, projname, srcs, variant ):
    # Create .proj file
    proj_file = open (projname + '.vcproj', 'w')

    project = XMLGenerator (proj_file)

    GUID = '{28540DAA-6718-4DE8-8D55-468836F0BE71}'


    project.startElement ('VisualStudioProject', {'ProjectType':'Visual C++',
                                                 'Version':'7.10',
                                                 'Name':projname,
                                                 'ProjectGUID':GUID,
                                                 'SccProjectName':'',
                                                  'SccLocalPath':''})

    project.startElement ('Platforms', None)
    project.element ('Platform', {'Name':'Win32'})

    project.endElement ('Platforms')


    project.startElement ('Configurations', {})

    project.startElement ('Configuration', {'Name':variant+'|Win32',
                                           'OutputDirectory':'.\\'+variant,
                                           'IntermediateDirectory':'.\\'+variant,
                                           'ConfigurationType':'1',
                                           'UseOfMFC':'0',
                                            'CharacterSet':'2'})


    #
    # Compiler
    #

    ppdefs = ''
    for p in env['CPPDEFINES']:
        ppdefs = ppdefs + p + ';'

    # TODO: parse flags and add correct attributes in compiler tool.
    ccflags = env['CCFLAGS']

    project.element ('Tool', {'Name':'VCCLCompilerTool',
                                  'PreprocessorDefinitions':ppdefs,
                                  'ObjectFile':'.\\' + variant + '/',
                                  'ProgramDataBaseFileName':'.\\' + variant + '/',
                                  'SuppressStartupBanner':'TRUE',
                                   'AdditionalOptions':str(ccflags),
                                  'Optimization':'0',
                                   'DebugInformationFormat':'4'})


    #
    # Linker
    #
    libs = ""
    for lib in env['LIBS']:
        libs += str ( env['LIBPREFIX'] + lib + env['LIBSUFFIX'] ) + " "

    libsdir = ''
    for d in env['LIBPATH']:
        libsdir = libsdir + d + ';'


    project.element ('Tool', {'Name':'VCLinkerTool',
                             'AdditionalDependencies':libs,
                             'SuppressStartupBanner':'TRUE',
                             'OutputFile':'.\\' + variant + '/' + projname + '.exe',
                             'AdditionalLibraryDirectories':libsdir,
                              'GenerateDebugInformation':'TRUE'})

    project.endElement ('Configuration')
    project.endElement ('Configurations')

    project.startElement ('Files')

    project.startElement ('Filter', {'Name':'Source Files',
                                     'Filter':'cpp;c;cxx;rc;def;r;odl;idl;hpj;bat'})

    srcs.sort ()
    for m in srcs:
        module = m[0]
        src_list = m[1]

        project.startElement ('Filter', {'Name': module,'Filter':''})
        for s in src_list:
            incpaths = ''
            for path in s.incpaths:
                incpaths = incpaths + path + ';'

            ppdefs = ''
            for ppdef in s.ppdefs:
                ppdefs = ppdefs + ppdef + ';'

            project.startElement ('File', {'RelativePath':s.filepath})
            project.startElement ('FileConfiguration', {'Name':variant+'|Win32'})
            project.element ('Tool', {'Name':'VCCLCompilerTool',
                                 'PreprocessorDefinitions':ppdefs,
                                  'AdditionalIncludeDirectories':incpaths})
            project.endElement ('FileConfiguration')
            project.endElement ('File')

        project.endElement ('Filter')

    project.endElement ('Filter')

    project.endElement ('Files')

    project.endElement ('VisualStudioProject')

    proj_file.close ()

def env2MSVS8 ( env, projname, path, srcs, variant ):
    # Create .proj file
    proj_file = open (os.path.join (path,projname + '.vcproj'), 'w')

    project = XMLGenerator (proj_file)

    GUID = '{28540DAA-6718-4DE8-8D55-468836F0BE71}'
    project.startElement ('VisualStudioProject', {'ProjectType':'Visual C++',
                                                  'Version':'8,00',
                                                 'Name':projname,
                                                 'ProjectGUID':GUID,
                                                 'SccProjectName':'',
                                                  'SccLocalPath':''})

    project.startElement ('Platforms', None)
    project.element ('Platform', {'Name':'Win32'})

    project.endElement ('Platforms')


    project.startElement ('Configurations', {})

    project.startElement ('Configuration', {'Name':variant+'|Win32',
                                           'OutputDirectory':'.\\'+variant,
                                           'IntermediateDirectory':'.\\'+variant,
                                           'ConfigurationType':'1',
                                           'UseOfMFC':'0',
                                            'CharacterSet':'2'})


    #
    # Compiler
    #

    ppdefs = ''
    for p in env['CPPDEFINES']:
        ppdefs = ppdefs + p + ';'

    # TODO: parse flags and add correct attributes in compiler tool.
    ccflags = env['CCFLAGS']

    project.element ('Tool', {'Name':'VCCLCompilerTool',
                                  'PreprocessorDefinitions':ppdefs,
                                  'ObjectFile':'.\\' + variant + '/',
                                  'ProgramDataBaseFileName':'.\\' + variant + '/',
                                  'SuppressStartupBanner':'TRUE',
                                   'AdditionalOptions':str(ccflags),
                                  'Optimization':'0',
                                   'DebugInformationFormat':'4'})


    #
    # Linker
    #
    libs = ""
    for lib in env['LIBS']:
        libs += str ( env['LIBPREFIX'] + lib + env['LIBSUFFIX'] ) + " "

    libsdir = ''
    for d in env['LIBPATH']:
        libsdir = libsdir + d + ';'

    project.element ('Tool', {'Name':'VCLinkerTool',
                             'AdditionalDependencies':libs,
                             'SuppressStartupBanner':'TRUE',
                             'OutputFile':'.\\' + variant + '/' + projname + '.exe',
                             'AdditionalLibraryDirectories':libsdir,
                              'GenerateDebugInformation':'TRUE'})

    project.endElement ('Configuration')
    project.endElement ('Configurations')

    project.startElement ('Files')

    project.startElement ('Filter', {'Name':'Source Files',
                                     'Filter':'cpp;c;cxx;rc;def;r;odl;idl;hpj;bat'})

    srcs.sort ()
    for m in srcs:
        module = m[0]
        src_list = m[1]

        project.startElement ('Filter', {'Name': module,'Filter':''})
        for s in src_list:
            incpaths = ''
            for path in s.incpaths:
                incpaths = incpaths + path + ';'

            ppdefs = ''
            for ppdef in s.ppdefs:
                ppdefs = ppdefs + ppdef + ';'

            project.startElement ('File', {'RelativePath':s.filepath})
            project.startElement ('FileConfiguration', {'Name':variant+'|Win32'})
            project.element ('Tool', {'Name':'VCCLCompilerTool',
                                 'PreprocessorDefinitions':ppdefs,
                                  'AdditionalIncludeDirectories':incpaths})
            project.endElement ('FileConfiguration')
            project.endElement ('File')

        project.endElement ('Filter')

    project.endElement ('Filter')

    project.endElement ('Files')

    project.endElement ('VisualStudioProject')

    proj_file.close ()

#parameters:list( dict{ DEBUG:True/False, TOOL:string, KEY:string, VALUE:string } )
def update_vcproj8(filename,parameters):
    try:
        from xml.etree import cElementTree as ET
    except:
        userErrorExit("You need Python 2.5 to call update_vcproj8")

    tree = ET.parse(filename)
    root = tree.getroot()

    for p in parameters:
        if p['DEBUG']:
            config = 'Debug'
        else:
            config = 'Release'
        configurations = filter(lambda c: c.get("Name").startswith(config),root.findall("Configurations/Configuration"))

        for c in configurations:
            tools = filter(lambda t: t.get("Name") == p['TOOL'],c.findall("Tool"))
            for t in tools:
                t.set(p['KEY'],p['VALUE'])

    f = open( filename, 'w')
    f.write(ET.tostring(root))
    f.close()

#return:dict{ FILENAME:string, PROJNAME:string, GUID:string }
def get_info_vcproj8(filename):
    try:
        from xml.etree import cElementTree as ET
    except:
        userErrorExit("You need Python 2.5 to call get_info_vcproj8")
    tree = ET.parse(filename)
    root = tree.getroot()

    result = dict()

    result['PROJNAME'] = root.get("Name")
    result['PROJGUID'] = root.get("ProjectGUID")
    result['FILENAME'] = filename

    return result
