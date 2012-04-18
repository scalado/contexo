# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
#   ctx_svn_client.py                                                         #
#   Component of Contexo Core - (c) Scalado AB 2010                           #
#                                                                             #
#   Author: Thomas Eriksson                                                   #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   GIT interface for Contexo                                                 #                                                                             #                                                                             #
###############################################################################

from ctx_common import ctxAssert, userErrorExit, infoMessage, errorMessage
from ctx_repo_git import locate_git
import os

#------------------------------------------------------------------------------
class CTXGitClient():
    def __init__(self):
        self.git = locate_git()
        #old_git_error()
        self.msgSender = "CTXGitClient"

    #--------------------------------------------------------------------------
    # returns list() of revision in commit order, newest first, oldest last.
    # used by ctx view freeze
    def getRevisionFromWorkingCopy(self, repo_path):
        path = os.path.abspath('')
        if not os.path.isdir(repo_path):
            errorMessage("no such git repo: %s"%(repo_path))
            exit(42)
        os.chdir( repo_path )
        import subprocess
        args = [self.git, '--no-pager', 'log', '--pretty=oneline', '--no-color']
        p = subprocess.Popen(args, bufsize=8192, stdin=None, stdout=subprocess.PIPE, stderr=None)
        stdout = p.stdout.read()

        retcode = p.wait()
        if stdout.split() != []:
            rev = stdout.split()[0]

        if retcode != 0:
            print stderr
            errorMessage("could not run git log, git log failed with return code %d"%(retcode))
            exit(retcode)
        os.chdir(path)
        return rev



