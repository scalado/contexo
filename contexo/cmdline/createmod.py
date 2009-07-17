#! /usr/bin/env python

info = """
###############################################################################
#                                                                             #
#   createmod.py                                                              #
#   Accessory of Contexo - (c) Scalado AB 2006                                #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Generates an empty code module structure with custom dependencies and an  #
#   initial template  implementation of a public header.                      #
#                                                                             #
#   Usage:                                                                    #
#                                                                             #
#   createmod.py --name <i>module_name</i> [--depends <i>module-names</i>]    #
#                [--path <i>module-path</i>] [--nofiles]                      #
#                [--optfile <i>filename</i>]                                  #
#                                                                             #
#                                                                             #
#    --name      Name of the code module (and root directory).                #
#                                                                             #    
#    --depends   [optional] List of code modules which the new module will    #
#                depend on.                                                   #
#                                                                             #
#    --path      [optional] The path to where the new code module will be     #
#                created.                                                     #
#                                                                             #
#    --nofiles   [optional] If specified, no files are created for the new    #
#                code module, only the directory structure is generated.      #
#                                                                             #
#    --optfile   [optional] Option file with commandline options.             #
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
from ctx_common import *

current_year = "2007"

#------------------------------------------------------------------------------
def create_module_structure( path, modname, overwrite ):
    
    if not os.path.exists( path ):
        print "Can't find path: '" + path + "'"
        sys.exit( 1 )
 
    modroot = os.path.join( path, modname )
     
    if os.path.exists( modroot ):
    
        if overwrite == True:
            shutil.rmtree( modroot )
        else:        
            print "Module already exists: '" + modroot + "'"
            sys.exit( 1 )
    
    os.makedirs( os.path.join( modroot, 'doc'    ))
    os.makedirs( os.path.join( modroot, 'inc'    ))
    os.makedirs( os.path.join( modroot, 'output' ))
    os.makedirs( os.path.join( modroot, 'contexo'))
    os.makedirs( os.path.join( modroot, 'src'    ))
    os.makedirs( os.path.join( modroot, 'test'   ))
    
    return modroot


#------------------------------------------------------------------------------
def create_module_depends_file( modroot, depends_list ):
    
    depfile = file( os.path.join( modroot, "contexo/depends" ), "w" )
    
    depfile.write( """
###############################################################################
#                                                                             #
#   Contexo code module dependency.                                           #                                      
#                                                                             #
###############################################################################
\n""") 
    
    for dep in depends_list:
        depfile.write( dep + '\n' )
    depfile.close()
    
     

#------------------------------------------------------------------------------
def create_public_header_file( modroot, modname ):

    pubheader_contents = """\
/*****************************************************************************
 * 2000-%s Scalado AB. All rights reserved.                                *
 *                                                                           *
 * Technologies used in this source code are patented or patent pending      *
 * by Scalado AB Swedish Org. Number, 556594-6885.                           *
 *                                                                           *
 * All Intellectual Property Rights related to this source code,             *
 * belongs to Scalado AB.                                                    *
 *                                                                           *
 * This source code is furnished under license agreement and may be used     *
 * or copied only in accordance with terms of such license agreement.        *
 *                                                                           *
 * Except as permitted by such license agreement, no part of this source     *
 * code may be reproduced, stored in a retrieval system, or transmitted,     *
 * in any form or by any means, electronic, mechanical, recording, or        *
 * otherwise, without the prior written permission of Scalado.               *
 *                                                                           *
 * Scalado assumes no responsibility or liability for any errors or          *
 * inaccuracies in this source code or any consequential, incidental or      *
 * indirect damage arising out of the use of this source code.               *
 *                                                                           *
 * Scalado and the Scalado logo are either registered trademarks or          *
 * trademarks of Scalado AB in Sweden and/or other countries.                *
 *                                                                           *
 *****************************************************************************/
#ifndef %s_H
#define %s_H

///////////////////////////////////////////////////////////////////////////////
//-----------------------------------------------------------------------------
/** 
    @file %s.h

    $PublicHeaderFileDescription$
*/
//-----------------------------------------------------------------------------
///////////////////////////////////////////////////////////////////////////////
#ifdef __cplusplus
extern "C" {
#endif



#ifdef __cplusplus
} // extern "C"
#endif
#endif // !defined( %s_H )
    """%( current_year, modname.upper(), modname.upper(), modname, modname.upper())
   
    pubheader = file( os.path.join( modroot, modname + ".h" ), "w" )
    pubheader.write( pubheader_contents )
    pubheader.close()






#------------------------------------------------------------------------------
############# Entry point #####################################################
#------------------------------------------------------------------------------


if len(sys.argv) == 1:
    print info
    sys.exit(0)

#
# Process commandline
#

knownOptions = ['--name', '--depends', '--path', '--nofiles', '--optfile']
options = digestCommandline( sys.argv[1:], True, knownOptions )

#
# Check mandatory options
#

for opt in ['--name']:
    if opt not in options.keys():
        userErrorExit( "Missing mandatory option: '%s'"%opt, msgSender )

#
# Assign default values to omitted options
#

if not options.has_key( '--path' ):
    options['--path'] = [os.getcwd(),]
    
if not options.has_key( '--depends' ):
    options['--depends'] = ["",]

#
# Check for required option arguments
#

for opt in ['--name','--depends','--path']:
    if len(options[opt]) == 0:
        userErrorExit( "Missing arguments to option '%s'"%opt )

arg_modulename = options['--name'][0]
arg_depends    = options['--depends']
arg_path       = options['--path'][0]
arg_nofiles    = bool( options.has_key('--nofiles') )
arg_overwrite  = False


module_root = create_module_structure( arg_path, arg_modulename, arg_overwrite )

create_module_depends_file( module_root, arg_depends )

create_public_header_file( module_root, arg_modulename )


