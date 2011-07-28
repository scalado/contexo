#! /usr/bin/env python

info = """
###############################################################################
#                                                                             #
#   switchcfg.py                                                              #
#   Accessory of Contexo - (c) Scalado AB 2007                                #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Switches the current system config.                                       #
#                                                                             #
#   Usage:                                                                    #
#                                                                             #
#   switchcfg.py config-name                                                  #
#                                                                             #
#   config-name should be the name of a config file located in folder         #
#   "CONTEXO_ROOT/ctxcfg". Extension may be omitted, in which case '.cfg' is  #
#   appended by the script.                                                   #
#                                                                             #
#   Examples:                                                                 #
#                                                                             #
#   >> This commandline will change current config to                         #
#   >> CONTEXO_ROOT/ctxcfg/default.cfg                                        #
#   c:\> switchcfg.py default                                                 #
#                                                                             #
#   >> This commandline will change current config to                         #
#   >> CONTEXO_ROOT/ctxcfg/japanbranches33.cfg                                #
#   c:\> switchcfg.py japanbranches33.cfg                                     #
#                                                                             #
###############################################################################
"""

import os
import sys
from ctx_common import *
msgSender = 'switchcfg.py'

#------------------------------------------------------------------------------
def replaceMatchingLineInFile( file_path, existing, replacement ):
    tmp_file = file_path + ".tmp"
    if os.path.exists( file_path ):
        inputFile	= file(file_path)
        outputFile	= file(tmp_file, "w")
    
        for l in inputFile.readlines():
            if l.find( existing ) != -1:
                l = replacement
            outputFile.write(l)
    
        inputFile.close()
        outputFile.close()
        os.remove( file_path )
        os.rename( tmp_file, file_path )    

##### ENTRY POINT #############################################################

if len(sys.argv) == 1:
    print >>sys.stderr, info
    ctxExit(0)

sysCfgName = sys.argv[1]
dummy, ext = os.path.splitext(sysCfgName)
if len(ext) == 0:
    sysCfgName += '.cfg'
    
sysCfgPath = os.path.join( getUserCfgDir(), sysCfgName )

if not os.path.exists( sysCfgPath ):
    userErrorExit( "Unable to find given cofiguration file '%s'"%(sysCfgPath), msgSender )
     
configSelector = os.path.join( getUserDir(), 'ctx.cfg' )    
replaceMatchingLineInFile( configSelector, "CURRENT_SYSCFG", "CURRENT_SYSCFG = %s"%sysCfgName ) 

print >>sys.stderr, "System config switched to '%s'"%sysCfgName


