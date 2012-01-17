import os.path
###############################################################################
#                                                                             #
#   ctx_repo_git.py                                                           #
#   Component of Contexo - (c) Scalado AB 2010                                #
#                                                                             #
#   Authors: Robert Alm, Thomas Eriksson                                      #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Implementation of CTXRepository for GIT                                   #
#                                                                             #
###############################################################################

from ctx_repo import *
from ctx_common import userErrorExit, warningMessage
import os

#, infoMessage, ctxAssert
def locate_git():
    warn_hardcoded_git_path = False
    for git_cand in ['git', 'git.cmd', 'git.exe', 'git.bat']:
        for path in os.environ["PATH"].split(os.pathsep):
            if os.path.exists(os.path.join( path, git_cand)) and os.access( os.path.join( path, git_cand), os.X_OK):
                return git_cand
    for git_cand in ['git', 'git.cmd', 'git.exe', 'git.bat']:
        for path in ['C:\\Program Files\\Git\cmd', 'C:\\Program Files (x86)\\Git\\cmd', '/usr/bin', '/usr/local/bin']:
            if os.path.exists(os.path.join( path, git_cand)) and os.access( os.path.join( path, git_cand), os.X_OK):
                #warningMessage("Falling back to hardcoded git path")
                return os.path.join(path, git_cand)
 
    userErrorExit("Git cannot be found in your PATH. Please re-install Git and make sure the git.cmd, git.exe or git binary can be found in your PATH")

#------------------------------------------------------------------------------
class CTXRepositoryGIT(CTXRepository):
    def __init__(self, id_name, local_path, href, rev):
        self.path = os.path.abspath('')
        self.destpath = os.path.join(local_path, id_name)
        self.id_name = id_name
        self.git = locate_git()
        self.rev = rev


        if href == None:
            userErrorExit("No HREF specified for repository '%s'. Failed to aquire HREF from local copy '%s'"\
                           %(id_name, self.getAbsLocalPath()))

        CTXRepository.__init__( self, id_name, local_path, href, rev, version_control=True )
	
	# these are hardcoded dummy paths for ctxview
	self.local_path = local_path
	self.codeModulePaths = ['dummy1']
	self.componentPaths = ['dummy2']
	# END hardcoded dummy paths

	self.msgSender = "CTXRepositoryGIT"

    #--------------------------------------------------------------------------
    def isLocal(self):

        import subprocess
        import os
        os.chdir(self.path)
        if not os.path.isdir(self.destpath):
            return False
        os.chdir(self.path)

        return True



    #--------------------------------------------------------------------------
    # returns name of branch if exists
    # the string '(no branch)' if not on a branch but valid repo
    # empty string if not exists
    def getBranch(self):
        os.chdir(self.path)
        if not os.path.isdir(self.destpath):
            return ''
        os.chdir(self.destpath)
        import subprocess
        args = [self.git, 'branch', '--no-color' ]
        p = subprocess.Popen(args, bufsize=4096)
        retcode = p.wait()

        if retcode != 0:
            print >>sys.stderr, stderr
            errorMessage("GIT execution failed with error code %d"%(retcode))
            exit(retcode)

        retcode = p.wait()
        os.chdir(self.path)
        return ''

    #--------------------------------------------------------------------------
    # TODO: test disconnected operation
    # resolves git remotes such as 'origin' or href urls to a href url
    # if remote repo is not available, an empty string is returned
    def getRemote(self, fetch_url):
        import subprocess
        import tempfile
        if fetch_url == '.' or fetch_url == '':
            errorMessage("getRemote called with invalid parameters (%s), make sure the .rspec points to valid repositories."%(fetch_url))
            exit(42)

        tmpdir = ''
        os.chdir(self.destpath)
        remote = ''

        args = [self.git, 'remote', 'show', fetch_url]
        p = subprocess.Popen(args, bufsize=4096)
        retcode = p.wait()

        if retcode != 0:
            remote = ''
        os.chdir(self.path)

        return remote
    #--------------------------------------------------------------------------
    def getRcs(self):
       return 'git'

    #--------------------------------------------------------------------------
    def update(self):
        import ctx_view
        import subprocess

        origin_href = self.getRemote('origin')
 
        if origin_href != self.href:
            warningMessage("rspec href is set to %s, but the git repository origin is set to %s. Using git repository origin"%(self.href, origin_href))

        os.chdir(self.destpath)

        infoMessage("Fetching new tags in '%s': 'git fetch'"%(self.id_name))
        p = subprocess.Popen([self.git, 'fetch'], bufsize=4096)
        retcode = p.wait()
        if retcode != 0:
            warningMessage("could not fetch from %s"%(self.href))
            sys.exit(1)
        
        workingBranchName = self.getBranch()
        # getBranch changes dir, go back to git dir
        restoreWorkBranch = False

        infoMessage("Checking out %s in %s 'git checkout %s'"%(self.rev, self.id_name, self.rev),1)
        os.chdir(self.destpath)
        p = subprocess.Popen([self.git, 'checkout', self.rev], bufsize=4096)
        retcode = p.wait()
        if retcode != 0:
            sys.exit(1)
        updateBranchName = self.getBranch()
        # getBranch changes dir, go back to git dir
        os.chdir(self.destpath)
        if updateBranchName != '' and updateBranchName != '(no branch)':
            infoMessage("Updating branch '%s' in '%s': 'git pull %s %s''"%(self.rev, self.id_name, 'origin', self.rev))
            p = subprocess.Popen([self.git, 'pull', 'origin', self.rev], bufsize=4096)
            retcode = p.wait()
            print >>sys.stderr, ''
            if retcode != 0:
                #print >>sys.stderr, p.stderr.read()
                errorMessage("could not pull from %s"%(self.href))
                exit(retcode)

        os.chdir(self.path)

    #--------------------------------------------------------------------------
    def clone(self):
        import subprocess
        infoMessage("Cloning RSpec defined GIT repo '%s' (%s)"%(self.id_name, self.href), 1)
        infoMessage("Running 'git clone %s %s'"%(self.href, self.id_name), 1)
        p = subprocess.Popen([self.git, 'clone', self.href, self.id_name],bufsize=0 ,stdin=None)

        retnum = p.wait()
	# newline after output
	print >>sys.stderr, ''
        if retnum != 0:
            errorMessage("Could not clone %s"%(self.href))
            exit(retnum)
        if not os.path.isdir(self.id_name):
            errorMessage("Destination nonexistant after clone: %s"%(self.id_name))
            exit(42)

        os.chdir(self.id_name)
        infoMessage("Running 'git checkout %s' in '%s'"%(self.rev, self.id_name), 1)
        args = [self.git, 'checkout', self.rev]
        p = subprocess.Popen( args,bufsize=0 ,stdin=None, stdout=None)

        retnum = p.wait()
        if retnum != 0:
            print >>sys.stderr, stdout
            print >>sys.stderr, stderr
            errorMessage("Could not checkout '%s' in '%s'"%(self.rev, self.id_name))
            exit(retnum)
        os.chdir(self.path)

        infoMessage("Successfully cloned GIT repo '%s'"%(self.id_name), 1)



    #--------------------------------------------------------------------------
    # this method is unused
    def checkValidRevision(self):
        return True

    #--------------------------------------------------------------------------
    def checkValid(self, updating ):
        return True

    #--------------------------------------------------------------------------
    # call clone() instead to avoid confusion over function naming
    def checkout(self):
        return self.clone()

