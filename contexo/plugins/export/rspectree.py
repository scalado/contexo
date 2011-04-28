#! /usr/bin/env python

import sys
from internal_argparse import ArgumentParser
from contexo.ctx_export import *
from contexo.ctx_common import *
import contexo.ctx_bc
import contexo.ctx_cmod
import contexo.ctx_msvc

msgSender = 'rspectree'

header = """
digraph test123 {
node[shape=box];
node[fontname=verdana];
node[fontsize=9];
edge[dir=back];

"""

footer = """
}
"""
        
#------------------------------------------------------------------------------
def cmd_parse( args ):

    if sys.platform != 'win32':
        userErrorExit("The RSpec Tree plugin is currently only supported on Windows")

    infoMessage("Receiving export data from Contexo...", 1)
    package = CTXExportData()
    package.receive() # Reads pickled export data from stdin
    
    infoMessage("Received export data:", 4)
    for item in package.export_data.keys():
        infoMessage("%s: %s"%(item, str(package.export_data[item])), 4) 

    if len(package.export_data['RSPEC'].keys()) == 0:
        userErrorExit("No RSpec received for export. Make sure a valid RSpec file is located in the view when exporting.")
        
    root_rspec = package.export_data['RSPEC'].keys()[0]
    filename = os.path.join( args.output, root_rspec + '.dot' )
    dotfile = open( filename, "w" )
    
    dotfile.write( header )
    
    def recurse_rspecs( rspec, imports_dict, dotfile ):
        
        line = str()
        if len(imports_dict.keys()) != 0:
            line = "%s -> {%s};\r\n"%( rspec, " ".join(imports_dict.keys()) )
        
        line = line.replace('.rspec', '')
        dotfile.write( line )                    
        
        for k in imports_dict.keys():
            recurse_rspecs( k, imports_dict[k], dotfile )

    current_rspec   = package.export_data['RSPEC'].keys()[0]
    current_imports = package.export_data['RSPEC'][current_rspec]
    
    recurse_rspecs( current_rspec, current_imports, dotfile )
    
    dotfile.write( footer )
    dotfile.close()
    
    os.system( "dot.exe -Tjpeg %s -ofile -O"%(filename) )

    if not args.no_display:
        os.system( "%s"%( filename + '.jpeg') )
    
    print "Done"
    
##### ENTRY POINT #############################################################

# Create Parser
parser = ArgumentParser( description="RSpec tree image generator - plugin to Contexo Build System (c) 2006-2009 Scalado AB",
 epilog="Requires Graphviz dot to be installed on the system.\nObtain installer for Windows here: http://www.graphviz.org/pub/graphviz/stable/windows/graphviz-2.24.msi",
 version="0.1")

parser.set_defaults(func=cmd_parse)

parser.add_argument('-o', '--output', default=os.getcwd(), 
 help="The output directory for the export. Default is current directory.")

parser.add_argument('-nd', '--no-display', action='store_true', 
 help="""If specified, the rendered JPEG image will not be automatically displayed""")

args = parser.parse_args()
args.func(args)
