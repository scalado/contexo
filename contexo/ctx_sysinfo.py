###############################################################################
#                                                                             #
#   ctx_sysinfo.py                                                            #
#   Component of Contexo - (c) Scalado AB 2009                                #
#                                                                             #
#   Author:                                                                   #
#   Robert Alm                                                                #
#   ------------                                                              #
#                                                                             #
#   System information constants and persistent settings                      #
#                                                                             #
###############################################################################

#
#### System information 
#

CTX_VER_MAJOR           = 0
CTX_VER_MINOR           = 4
CTX_VER_STATE           = 'beta'
CTX_DISPLAYVERSION      = '%d.%d %s'%(CTX_VER_MAJOR, CTX_VER_MINOR, CTX_VER_STATE)

CTX_BANNER              = """
Contexo Build System v%s 
"""%(CTX_DISPLAYVERSION)



#
#### Configuration
#


CTX_CONFIG_FILENAME     = 'contexo.cfg'
