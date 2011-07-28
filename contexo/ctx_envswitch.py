###############################################################################
#
#   ctx_envswitch.py
#   Component of Contexo Shell - (c) Scalado AB 2006
#
#   Author: Robert Alm (robert.alm@scalado.com)
#
#   ------------
#
#   Handles environment switching.
#
###############################################################################

from config import Config
import os
import os.path
import sys
import string
import config
from ctx_common import *

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class EnvironmentLayout:
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __init__( self, config = None,  envFiles=None ):
        self.envFilePaths = envFiles
        self.env = dict()
        self.msgSender = 'EnvironmentLayout'

        if self.envFilePaths == None:
            for key, value in os.environ.iteritems():
                self.env[key] = value
        else:
            assert  (config != None)
            if type(self.envFilePaths) != list:
                self.envFilePaths = [self.envFilePaths,]

            #sysEnvPaths = config.getEnvPaths()
            sysEnvPaths = list()
            sysEnvPaths.extend(config.getEnvPaths())

            self.__resolveENVFileLocations(sysEnvPaths)

            for path in self.envFilePaths:
                cfg = Config( path )
                if not cfg.has_section( 'env' ):
                    userErrorExit("Missing mandatory section '%s'"%('env'))

                envDict = cfg.get_section( 'env'  )
                self.__mergeEnv( envDict )


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __mergeEnv( self, envDict, alwaysReplace = False ):
        delimiter = os.pathsep

        for key, value in envDict.iteritems():
            if type(value) == list:
                value = delimiter.join( value )
            elif type(value) != str:
                value = str(value)

            if self.env.has_key(key) and alwaysReplace == False:
                self.env[key] += delimiter + value
            else:
                self.env[key] = value


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def __resolveENVFileLocations( self,  sysEnvPaths ):
        for n in range( 0, len(self.envFilePaths) ):
            if not os.path.exists( self.envFilePaths[n] ):
                for sysEnvPath in sysEnvPaths:
                    path = os.path.join( sysEnvPath, self.envFilePaths[n] )
                    if not os.path.exists( path ):
                        self.envFilePaths[n] = None
                    else:
                        self.envFilePaths[n] = path
                if self.envFilePaths[n] == None:
                    userErrorExit("Cannot find ENV file '%s'"%path)
                else:
                    infoMessage("Including env file '%s'"%(self.envFilePaths[n]), 1)

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getEnv( self ):
        return self.env

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def getVar( self, var ):
        if not self.env.has_key( var ):
            userErrorExit("Cannot find variable '%s'"%var)
        return self.env[var]

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def merge( self, envLayout, alwaysReplace = False ):
        envLayoutDict = envLayout.getEnv()
        self.__mergeEnv( envLayoutDict, alwaysReplace )

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def removeDiff( self, envLayout ):
        for key in self.env.keys():
            if not envLayout.getEnv().has_key( key ):
                del self.env[key]

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def switchEnvironment( newEnvLayout, preserve = True ):

    # Create a backup of the existing environment.
    oldEnv = EnvironmentLayout()

    # Clone the existing environment and replace all
    # items defined by the given layout.

    curEnv = EnvironmentLayout()
    curEnv.merge( newEnvLayout, True )
    if preserve == False:
        # Remove items not included in the layout that was passed
        # to this function.
        curEnv.removeDiff( newEnvLayout )

    # Make the switch
    newEnvDict = curEnv.getEnv()
    for key, value in newEnvDict.iteritems():
        os.environ[key] = value
        # Don't mangle the PATH for git, but instead append it to the env-set PATH
        if key == 'PATH':
            os.environ[key] = value + os.pathsep + oldEnv.getVar(key)

    remKeys = list()
    for key, value in os.environ.iteritems():
        if key not in newEnvDict:
            remKeys.append( key )

    for key in remKeys:
        del os.environ[key]

    # Display resulting environment on high verbose level.
    if getVerboseLevel() >= 5:
        print >>sys.stderr, "---------------------------------------------------"
        print >>sys.stderr, "| (ctx_envswitch.py): Environment after switch:   |"
        print >>sys.stderr, "---------------------------------------------------"
        for var, val in os.environ.iteritems():
            val = val.split( os.pathsep )
            if type(val) == list:
                print >>sys.stderr, "%24s: %s;"%(var,val[0])
                for v in val[1:]:
                    print >>sys.stderr, "%24s  %s;"%("", v)
            else:
                print >>sys.stderr, "%24s:\t %s"%(var,val)
        print >>sys.stderr, "---------------------------------------------------\n\n"

    # Return old environment so the user can restore it later.
    return oldEnv

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
envRestore = None
def jitCleanup():
    global envRestore
    if envRestore != None:
        switchEnvironment( envRestore, False )
