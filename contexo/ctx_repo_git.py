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
#, infoMessage, ctxAssert

#------------------------------------------------------------------------------
class CTXRepositoryGIT(CTXRepository):
    def __init__(self, id_name, local_path, href, rev , branch):
        self.path = os.path.abspath('')
        self.destpath = os.path.join(local_path, id_name)
        self.id_name = id_name
        self.git = 'git'
        if rev == None:
            warningMessage("rev is None")
            self.rev = 'HEAD'
        else:
            self.rev = rev

        if href == None:
            userErrorExit("No HREF specified for repository '%s'. Failed to aquire HREF from local copy '%s'"\
                           %(id_name, self.getAbsLocalPath()))

        CTXRepository.__init__( self, id_name, local_path, href, None, version_control=True )
        self.msgSender = "CTXRepositoryGIT"
    #--------------------------------------------------------------------------
    def getSHA1(self):
        raise NotImplementedError



    #--------------------------------------------------------------------------
    def isLocal(self):

        import subprocess
        import os
        if not os.path.isdir(self.destpath):
            return False


        os.chdir(self.destpath)
        p = subprocess.Popen([self.git, 'status'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.readline()
        retcode = p.wait()

        if stderr == 'fatal: Not a git repository (or any of the parent directories): .git':
            print stderr
            warningMessage("Not a valid GIT repo")
            return False
        # TODO: temporary workaround, rev is modified elsewhere!
        if self.rev == None:
            self.rev = 'master'
            errorMessage("overriding undefined self.rev revision with \'master\'")
        infoMessage("Running 'git checkout %s'"%(self.rev),1)
        args = [self.git, 'checkout', self.rev]

        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.readline()
        retcode = p.wait()
        if retcode != 0:
            print stderr
        #if stderr != 'Already on \'master\'':
        #    print stderr

        return True



    #--------------------------------------------------------------------------
    def getBranch(self):
        import subprocess
        os.chdir(self.destpath)
        args = [self.git, 'branch', '--no-color' ]
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()

        if retcode != 0:
            print stderr
            errorMessage("GIT execution failed with error code %d"%(retcode))
            exit(retcode)

        p.wait()
        for line in stdout.split('\n'):
            if line.find('*') == 0:
                branch = line.split(' ')[1]
                return branch

        errorMessage("git branch parsing failed")
        raise

    #--------------------------------------------------------------------------
    def getLocalRev(self):
        import subprocess
        os.chdir(self.destpath)
        args = [self.git, '--no-pager', 'log', '-a', '--no-color' ]
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()

        if retcode != 0:
            print stderr
            errorMessage("GIT execution failed with error code %d"%(retcode))
            exit(retcode)

        p.wait()
        for line in stdout.split('\n'):
            if line.find('commit') == 0:
                rev = (line.split(' ')[1])
                return rev
        print stdout
        print stderr
        errorMessage("could not find SHA1 information")
        raise

    #--------------------------------------------------------------------------
    def getLocalBranches(self):
        import subprocess
        os.chdir(self.destpath)
        args = [self.git, 'branch', '-a', '--no-color' ]
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retcode = p.wait()

        if retcode != 0:
            print stderr
            errorMessage("GIT execution failed with error code %d"%(retcode))
            exit(retcode)

        p.wait()
        localBranches = list()
        for line in stdout.split('\n'):
            if line.find('*') == 0:
                localBranches.append(line.split(' ')[1])
            else:
                localBranches.append(line.trim())
        return localBranches

    #--------------------------------------------------------------------------
    def getRcs(self):
       return 'git'

    #--------------------------------------------------------------------------
    def update(self):
        import ctx_view
        import subprocess

        infoMessage("Running 'git fetch'")
        p = subprocess.Popen([self.git, 'fetch'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = p.wait()
        if retcode != 0:
            print p.stderr.read()
            errorMessage("could not pull from %s"%(self.href))
            exit(retcode)

        infoMessage("Running 'git checkout %s'"%(self.rev),1)
        p = subprocess.Popen([self.git, 'checkout', self.rev], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.readline()
        retcode = p.wait()
        if retcode != 0:
            print stderr


        infoMessage("Running 'git pull'")
        p = subprocess.Popen([self.git, 'pull'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = p.wait()
        if retcode != 0:
            print p.stderr.read()
            errorMessage("could not pull from %s"%(self.href))
            exit(retcode)

        stderr = p.stderr.readline()

        if stderr == 'fatal: Not a git repository (or any of the parent directories): .git':
            return False


    #--------------------------------------------------------------------------
    def clone(self):
        import subprocess
        infoMessage("Cloning RSpec defined GIT repo '%s' (%s)"%(self.id_name, self.href), 1)
        p = subprocess.Popen([self.git, 'clone', self.href, self.id_name],bufsize=0 ,stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.stderr.readline()
        while output != '':
            output = p.stderr.readline()
            print output
        retnum = p.wait()
        if retnum != 0:
            print p.stdout.read()
            errorMessage("Could not clone %s"%(self.href))
            exit(retnum)
        else:
            infoMessage("Successfully cloned GIT repo", 1)

    #--------------------------------------------------------------------------
    # is there such a sha in the remote repo?
    def checkValidRevision(self):
        raise NotImplementedError
        # Not applicable to non revisioned repositories
        return True

    #--------------------------------------------------------------------------
    def checkValid(self, updating ):
        self.getBranch()
        return self.isLocal()


    #--------------------------------------------------------------------------
    def checkout(self):
        return self.clone()

