#! /usr/bin/env python

info = """
###############################################################################
#                                                                             #
#   stat_mod.py                                                               #
#   Accessory of SBuild - (c) Scalado AB 2006                                 #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Verifies a given code module for SBuild compliance.                       #
#                                                                             #
#   All errors reported by this tool need to be solved before building the    #
#   code module - the build system uses the same verification routine.        #
#                                                                             #
#   Warnings are less serious notes to be considered about the module's       #
#   format, for example violation of less strict naming conventions or case   #
#   issues.                                                                   #
#                                                                             #
#                                                                             #
#   Usage:                                                                    #
#                                                                             #
#   verify_codemodule.py -name module_name -path module_path                  #
#                                                                             #
#                                                                             #
#   -name      - The name of the module.                                      #
#                                                                             #
#   -path      - The path to the code module root directory                   #
#                                                                             #
#                                                                             #
#   Example:                                                                  #
#                                                                             #
#   verify_codemodule.py -name scbutil -path c:\mods\scbutil                  #
#                                                                             #
###############################################################################
"""

import os
import os.path
import sys
import errno
import shutil
import re
import string


error_template   = "*** Error: %s"
warning_template = "*** Warning: %s"
error_list       = list()
warning_list     = list()

def add_warning( warning_message ):
    warning_list.append( warning_template%(warning_message) )
        
def add_error( error_message ):
    error_list.append( error_template%(error_message) )

#------------------------------------------------------------------------------
def verify_dir_structure( path, modname ):
    
    if not os.path.exists( path ):
        print >>sys.stderr, "*** Error, can't find path: '" + path + "'"
        sys.exit( 1 )
 
    mod_dir = os.path.basename( path )

    #
    # Warn if module name or directory contains upper case characters.
    #    
    
    if not mod_dir.islower():
        add_warning( "Module root directory contains upper case characters." )
        
    if not modname.islower():
        add_warning( "Module name contains upper case characters." )
        
    mod_dir = mod_dir.lower()
    modname = modname.lower()
    
    #
    # Verify that module name and module directory match.
    #
    
    if mod_dir != modname:
        add_error( "Module directory does not equal module name." )
        
    #
    # Verify module subdirectories.
    #
    
    mandatory_subdirs = ['doc', 'inc', 'output', 'sbuild', 'src', 'test']
    
    subdirs = os.listdir( path )
    
    for subdir in subdirs:

        if not subdir.islower():
            add_warning( "Sudirectory '%s' contains upper case characters."%subdir )
        
        if subdir.lower() in mandatory_subdirs:
            mandatory_subdirs.remove( subdir.lower() )
        
    for missing_subdir in mandatory_subdirs:
        add_error( "Mandatory subdirectory '%s' is missing."%missing_subdir )


#------------------------------------------------------------------------------
############# Entry point #####################################################
#------------------------------------------------------------------------------


### print >>sys.stderr, info and usage if no arguments given ###
if len(sys.argv) <= 1 or sys.argv[1] == '-?' or sys.argv[1] == '/?':
    print >>sys.stderr, info
    sys.exit(1)

arg_modulename = ""
arg_path       = ""


### Process commandline ###
curcmd = ""
for arg in sys.argv:

    if arg[-20:] == "verify_codemodule.py":
        continue

#    if arg == "-overwrite":
#        arg_overwrite = True
#        continue

    ### Below this point are options which have parameters.
    if arg[0] == '-':
        curcmd = arg
        continue

    ## Option '-name'
    if curcmd == "-name":
        arg_modulename = arg
        
     ## Option '-path'
    elif curcmd == "-path":
        arg_path = arg
 
       
    ## Handle unknown commandline item.
    else:
        print >>sys.stderr, "Unknown option or commandline item: '" + arg + "'"
        sys.exit(1)



if len(arg_modulename) == 0:
    print >>sys.stderr, "Name of module is mandatory input!"
    sys.exit(1)
     
if len(arg_path) == 0:
    print >>sys.stderr, "Module path is mandatory input!"
    sys.exit(1)

arg_modulename = arg_modulename.rstrip("\\/")


#
# Start verification
#

verify_dir_structure( arg_path, arg_modulename )



#
# Output summary
#

print >>sys.stderr, "\n- Summary for module: %s -\n"%arg_modulename

print >>sys.stderr, "----------- Errors ------------------------------------------"
if len(error_list) == 0: print >>sys.stderr, "No errors."
for error in error_list:
    print >>sys.stderr, error
print >>sys.stderr, "----------- Warnings ----------------------------------------"
if len(warning_list) == 0: print >>sys.stderr, "No warnings."
for warning in warning_list:
    print >>sys.stderr, warning
print >>sys.stderr, "-------------------------------------------------------------"
