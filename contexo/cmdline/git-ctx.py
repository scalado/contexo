#!/usr/bin/python
###############################################################################
#                                                                             #
#   git-ctx.py                                                                #
#   Contexo rspec multi repository tool support for the Git toolsuite         #
#                                                       (c) Scalado AB 2010   #
#                                                                             #
#   Author: Thomas Eriksson (thomas.eriksson@scalado.com)                     #
#   License GPL v2. See LICENSE.txt.                                          #
#   ------------                                                              #
#                                                                             #
#                                                                             #
###############################################################################
# coding=UTF-8

import os
import os.path
import sys
from contexo import ctx_repo
from contexo import ctx_rspec
from contexo import ctx_view
def dir_has_rspec(view_dir):
    view_filelist = os.listdir(view_dir)
    for entry in view_filelist:
        if entry.endswith('.rspec'):
            return True
    return False



class GITCtx:
    def __init__( self ):
        self.git = 'git'
        self.git_repos = list()
        self.ignored_repos = list()
        # instead of manually specifying rspec (as is the de facto uage convention
        # with contexo)
        # search backwards in path until an rspec file is found (the de-facto
        # git usage convention)
        self.view_dir = os.path.abspath('')
        while not dir_has_rspec(self.view_dir):
            os.chdir('..')
            self.view_dir = os.path.abspath('')
        ctxview = ctx_view.CTXView(self.view_dir)

        for repo in ctxview.getRSpec().getRepositories():
            if repo.getRcs() == 'git':
                self.git_repos.append(repo.getAbsLocalPath())
            else:
                self.ignored_repos.append(repo.getAbsLocalPath())

    def help():
        print """
git-ctx help
        """
    def print_all( self ):

        print self.git_repos
        print self.ignored_repos
        #ctxview.printView()

        #path = os.abs

    def status( self ):
        for repo_path in self.git_repos:
            if not os.path.isdir(repo_path):
                return ''
            os.chdir(repo_path)
            import subprocess
            args = [self.git, 'status', '--porcelain']
            p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stderr = p.stderr.read()
            stdout = p.stdout.read()
            retcode = p.wait()

            if retcode != 0:
                print stderr
                errorMessage("GIT execution failed with error code %d"%(retcode))
                exit(retcode)

            os.chdir(self.view_dir)
        for line in stdout.split('\n'):
            split_line = line.split()
            if len(split_line) == 3:
                if split_line[0] == '*' and split_line[1] == '(no' and split_line[2] == 'branch)':
                    return '(no branch)'
                if line.find('*') == 0:
                    branch = split_line[1]
                    return branch

        return ''

gitctx = GITCtx()
#gitctx.print_all()
if len(sys.argv) == 0:
	gitctx.help()
if sys.argv[1] == 'status':
	gitctx.status()
