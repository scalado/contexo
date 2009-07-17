###############################################################################
#                                                                             #
#   ctx_platform.py                                                           #
#   Component of Contexo Core - (c) Scalado AB 2006                           #
#                                                                             #
#   Author: Robert Alm (robert.alm@scalado.com)                               #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Provides a replaceable interface to system specific functions used by the #
#   build system.                                                             #
#                                                                             #
###############################################################################

import os
from contexo.ctx_common import infoMessage

def executeCommandline( commandline ):
    if os.name == 'nt':
        infoMessage( "Executing: %s"%commandline, 5, 'ctx_platform' )
    else:
        infoMessage( "Executing: %s"%commandline, 5, 'ctx_platform' )
    return os.system( commandline )

def shortenPathIfPossible( longPath ):
    shortPath = longPath
#    if os.name == 'nt':
#        import win32api
#        shortPath = win32api.GetShortPathName(longPath)
    return shortPath
