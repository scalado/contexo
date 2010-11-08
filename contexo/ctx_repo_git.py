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
from ctx_common import userErrorExit
import os

#, infoMessage, ctxAssert
def locate_git():
    for git_cand in ['git', 'git.cmd', 'git.exe', 'git.bat']:
        for path in os.environ["PATH"].split(os.pathsep):
            if os.path.exists(os.path.join( path, git_cand)) and os.access( os.path.join( path, git_cand), os.X_OK):
                return git_cand
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


        os.chdir(self.destpath)
        p = subprocess.Popen([self.git, 'status'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        retcode = p.wait()

	# git 1.6 returns 1
	# git 1.7 returns 0
        if retcode != 0 and retcode != 1:
            print stderr
            warningMessage("Not a valid GIT repo")
            os.chdir(self.path)
            return False
        infoMessage("Running 'git checkout %s' in '%s'"%(self.rev, self.id_name),1)
        args = [self.git, 'checkout', self.rev]

        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()
        if retcode != 0:
            print stdout
            print stderr
            errorMessage("could not checkout %s"%(self.rev))
            exit(retcode)
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
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()

        if retcode != 0:
            print stderr
            errorMessage("GIT execution failed with error code %d"%(retcode))
            exit(retcode)

        retcode = p.wait()
        os.chdir(self.path)
        for line in stdout.split('\n'):
            split_line = line.split()
            if len(split_line) == 3:
                if split_line[0] == '*' and split_line[1] == '(no' and split_line[2] == 'branch)':
                    return '(no branch)'
            if line.find('*') == 0:
                branch = split_line[1]
                return branch

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
        if self.getBranch() == '':
            # git can validate remote repos, but only if it is executed from a
            # git repository, this creates a temporary git repo to check the remote repo
            tmpdir = tempfile.mkdtemp(suffix='ctx_git')
            os.chdir(tmpdir)
            args = [self.git, 'init']
            p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            retcode = p.wait()
            if retcode != 0:
                # this should not happen!
                errorMessage("failed during creation of temporary git dir")
                raise
        else:
            os.chdir(self.destpath)
        remote = ''

        args = [self.git, 'remote', 'show', fetch_url]
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()

        retcode = p.wait()
        if retcode != 0:
            remote = ''
		# this section is a bit version dependent
        for line in stdout.split('\n'):
            split_line = line.split()
			# git 1.6
            if len(split_line) == 2:
				if split_line[0] == 'URL:':
					remote = split_line[1]
            # git v1.7
            if len(split_line) == 3:
                if split_line[0] == 'Fetch' and split_line[1] == 'URL:':
                    remote = split_line[2]
        os.chdir(self.path)
        # clean up
        if tmpdir != '':
            import shutil
            import time
            failcount = 0
            max_failures = 20
            while failcount < max_failures:
                try:
                    shutil.rmtree(tmpdir)
                    print 'success: removed after'
                    print failcount
                    print 'tries'
                    failcount = max_failures
                except:
                    print 'could not remove temporary dir ' + tmpdir + ': retrying...'
                    failcount = failcount + 1
                    time.sleep(0.1)
                    pass
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
        infoMessage("Running 'git fetch' in '%s'"%(self.id_name))
        p = subprocess.Popen([self.git, 'fetch'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = p.wait()
        if retcode != 0:
            print p.stderr.read()
            errorMessage("could not fetch from %s"%(self.href))
            exit(retcode)

        infoMessage("Running 'git checkout %s' in '%s'"%(self.rev, self.id_name),1)
        p = subprocess.Popen([self.git, 'checkout', self.rev], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        retcode = p.wait()
        if retcode != 0:
            print stderr
        localBranch = self.getBranch()
        # getBranch changes dir, go back to git dir
        os.chdir(self.destpath)
        if localBranch != '' and localBranch != '(no branch)':
            infoMessage("Running 'git pull %s %s' in '%s''"%('origin', self.rev, self.id_name))
            p = subprocess.Popen([self.git, 'pull', 'origin', self.rev], bufsize=4096, stdin=None)
            retcode = p.wait()
            print ''
            if retcode != 0:
                #print p.stderr.read()
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
	print ''
        if retnum != 0:
            errorMessage("Could not clone %s"%(self.href))
            exit(retnum)
        if not os.path.isdir(self.id_name):
            errorMessage("Destination nonexistant after clone: %s"%(self.id_name))
            exit(42)

        os.chdir(self.id_name)
        infoMessage("Running 'git checkout %s' in '%s'"%(self.rev, self.id_name), 1)
        args = [self.git, 'checkout', self.rev]
        p = subprocess.Popen( args,bufsize=0 ,stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retnum = p.wait()
        if retnum != 0:
            print stdout
            print stderr
            errorMessage("Could not checkout '%s' in '%s'"%(self.rev, self.id_name))
            exit(retnum)
        os.chdir(self.path)

        infoMessage("Successfully cloned GIT repo '%s'"%(self.id_name), 1)



    #--------------------------------------------------------------------------
    # this method is unused
    def checkValidRevision(self):
        if self.getBranch() != '':
            # repo is cloned
            return True
        else:
            return False

    #--------------------------------------------------------------------------
    def checkValid(self, updating ):
        if self.getBranch() != '':
            # repo is cloned
            return True
        else:
            # repo is remote
            # cannot validate remote repo if git is not initialized
            if self.getRemote(self.href) == '':
                errorMessage("Remote git repo %s is not valid"%(self.href))
                return False
            return True

    #--------------------------------------------------------------------------
    # call clone() instead to avoid confusion over function naming
    def checkout(self):
        return self.clone()

