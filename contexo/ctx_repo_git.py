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
        self.rev = rev

        if href == None:
            userErrorExit("No HREF specified for repository '%s'. Failed to aquire HREF from local copy '%s'"\
                           %(id_name, self.getAbsLocalPath()))

        CTXRepository.__init__( self, id_name, local_path, href, rev, version_control=True )
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

        if retcode != 0:
            print stderr
            warningMessage("Not a valid GIT repo")
            os.chdir(self.path)
            return False
        infoMessage("Running 'git checkout %s'"%(self.rev),1)
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
        for line in stdout.split('\n'):
            split_line = line.split()
            if len(split_line) == 3:
                if split_line[0] == 'Fetch' and split_line[1] == 'URL:':
                    remote = split_line[2]
        os.chdir(self.path)
        # clean up
        if tmpdir != '':
            import shutil
            shutil.rmtree(tmpdir)
        return remote

    #--------------------------------------------------------------------------
    # returns list() of revision in commit order, newest first, oldest last.
    # used by ctx view freeze
    def getRevisions(self):
        import subprocess
        localRevisions = list()
        args = [self.git, '--no-pager', 'log', '--pretty=oneline', '--no-color']
        p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()

        retcode = p.wait()
        for log_entry in stdout.split('\n'):
            localRevisions.append(log_entry[0])

        if retcode != 0:
            print stderr
            errorMessage("could not run git log, git log failed with return code %d"%(retcode))
            exit(retcode)
        os.chdir(self.path)
        return localRevisisons

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
        infoMessage("Running 'git fetch'")
        p = subprocess.Popen([self.git, 'fetch'], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        retcode = p.wait()
        if retcode != 0:
            print p.stderr.read()
            errorMessage("could not fetch from %s"%(self.href))
            exit(retcode)

        infoMessage("Running 'git checkout %s'"%(self.rev),1)
        p = subprocess.Popen([self.git, 'checkout', self.rev], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        retcode = p.wait()
        if retcode != 0:
            print stderr
        localBranch = self.getBranch()
        # getBranch changes dir, go back to git dir
        os.chdir(self.destpath)
        if localBranch != '' and localBranch != '(no branch)':
            infoMessage("Running 'git pull %s %s'"%('origin', self.rev))
            p = subprocess.Popen([self.git, 'pull', 'origin', self.rev], bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            retcode = p.wait()
            if retcode != 0:
                print p.stderr.read()
                errorMessage("could not pull from %s"%(self.href))
                exit(retcode)

            stderr = p.stderr.read()
        os.chdir(self.path)

    #--------------------------------------------------------------------------
    def clone(self):
        import subprocess
        infoMessage("Cloning RSpec defined GIT repo '%s' (%s)"%(self.id_name, self.href), 1)
        infoMessage("Running 'git clone %s %s'"%(self.href, self.id_name), 1)
        p = subprocess.Popen([self.git, 'clone', self.href, self.id_name],bufsize=0 ,stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()

        retnum = p.wait()
        if retnum != 0:
            print stdout
            print stderr
            errorMessage("Could not clone %s"%(self.href))
            exit(retnum)
        if not os.path.isdir(self.id_name):
            errorMessage("Destination nonexistant after clone: %s"%(self.id_name))
            exit(42)

        os.chdir(self.id_name)
        infoMessage("Running 'git checkout %s'"%(self.rev), 1)
        args = [self.git, 'checkout', self.rev]
        p = subprocess.Popen( args,bufsize=0 ,stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = p.stderr.read()
        stdout = p.stdout.read()
        retnum = p.wait()
        if retnum != 0:
            print stdout
            print stderr
            errorMessage("Could not checkout %s"%(self.rev))
            exit(retnum)
        os.chdir(self.path)

        infoMessage("Successfully cloned GIT repo", 1)



    #--------------------------------------------------------------------------
    # is there such a sha in the remote repo?
    def checkValidRevision(self):
        raise NotImplementedError
        # Not applicable to non revisioned repositories
        return True

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
    # call clone() instead to avoid confusion
    def checkout(self):
        return self.clone()

