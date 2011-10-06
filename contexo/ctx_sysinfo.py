###############################################################################
#                                                                             #
#   ctx_sysinfo.py                                                            #
#   Component of Contexo - (c) Scalado AB 2009                                #
#                                                                             #
#   Author:                                                                   #
#   Robert Alm                                                                #
#   License GPL v2. See LICENSE.txt.                                          #
#   ------------                                                              #
#                                                                             #
#   System information constants and persistent settings                      #
#                                                                             #
###############################################################################

#
#### System information
#

CTX_VER_MAJOR           = 0
CTX_VER_MINOR_1         = 16
CTX_VER_MINOR_2         = 3
CTX_VER_STATE           = ''
CTX_DISPLAYVERSION      = '%d.%d.%d %s'%(CTX_VER_MAJOR, CTX_VER_MINOR_1, CTX_VER_MINOR_2, CTX_VER_STATE)
CTX_LICENSE             = 'licesed under GPLv2 ( http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt )'

CTX_BANNER              = """
Contexo Build System v%s,\n %s
"""%(CTX_DISPLAYVERSION, CTX_LICENSE)

#
#### Configuration
#

CTX_CONFIG_FILENAME     = 'contexo.cfg'
