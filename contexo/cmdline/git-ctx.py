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
from contexo.ctx_common import errorMessage, warningMessage

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
        # instead of manually specifying view (as is the de facto uage convention for contexo)
        # search backwards in path until an rspec file is found (the de-facto
        # git usage convention)
        self.view_dir = os.path.abspath('')
        while not dir_has_rspec(self.view_dir):
            os.chdir('..')
            if self.view_dir == os.path.abspath(''):
                errorMessage('rspec not found, git ctx must be launched from a valid Contexo view')
                exit(2)
            self.view_dir = os.path.abspath('')
        # ctxview default args: view_path, access_policy=AP_PREFER_REMOTE_ACCESS, updating=False, validate=True
        # keep the validate=False if there is any repo under svn control, otherwise things will be very slow
        ctxview = ctx_view.CTXView(self.view_dir, 1, False, False)

        for repo in ctxview.getRSpec().getRepositories():
            if repo.getRcs() == 'git':
                self.git_repos.append(repo)
            #else:
            #    self.ignored_repos.append(repo.getAbsLocalPath())

    def help( self ):
        print """
git ctx is a component of the Contexo build system which integrates with the git toolsuite.
Any git command supplied to 'git ctx' will be executed for each subrepository in the view as defined by the Contexo .rspec.

usage: git ctx [git-command] [options] [--] <filepattern>...

git-command may be any of the following:
        """
        git_commands = ['branch', 'status', 'commit', 'checkout', 'add', 'rm', 'reset']
        for git_command in git_commands:
            print '\t' + git_command
        sys.exit(42)
    def print_all( self ):

        print self.git_repos
        print self.ignored_repos
        #ctxview.printView()

        #path = os.abs

        print """# Untracked files:
#   (use "git ctx add <file>..." to include in what will be committed)
#"""

    def status( self, git_argv ):
        from colorama import init
        init()
        from colorama import Fore, Back, Style
        statusdict = dict()
        statusdict[' M'] = list()
        statusdict['??'] = list()
        statusdict['A '] = list()
        statusdict[' U'] = list()
        statusdict[' R'] = list()
        statusdict[' D'] = list()

        untracked_files = list()
        modified_files = list()
        for repo in self.git_repos:
            repo_path = repo.getAbsLocalPath()
            if not os.path.isdir(repo_path):
                return ''
            os.chdir(repo_path)
            import subprocess
            args = [self.git, 'status', '--porcelain']
            args.extend(git_argv)
            p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stderr = p.stderr.read()
            stdout = p.stdout.read()
            retcode = p.wait()

            if retcode != 0:
                print stderr
                errorMessage("GIT execution failed with error code %d"%(retcode))
                exit(retcode)

            os.chdir(self.view_dir)
            print "# %s is on branch %s"%(os.path.basename(repo_path), repo.getBranch())
            for line in stdout.split('\n'):
                if len(line) > 3:
                    split_line = [ line[:2], line[3:] ]
                    if statusdict.has_key( split_line[0] ):
                        statusdict[ split_line[0] ].append( os.path.basename(repo_path) + '/' + split_line[1] )
                    else:
                        warningMessage("unknown git file status code %s"%(split_line[0]))
        print '#'

        if len(statusdict['A ']) > 0:
            print """# Changes to be committed:
#   (use "git reset HEAD <file>..." to unstage)
#            """
            for new_file in statusdict['A ']:
                print '#' + '\t' + 'new file:' + '\t' + Fore.GREEN + new_file + Style.RESET_ALL
            print '#'
        if len(statusdict[' M']) > 0 or len(statusdict[' D']) > 0:
            print """#
# Changed but not updated:
#   (use "git ctx add/rm <file>..." to update what will be committed)
#   (use "git ctx checkout -- <file>..." to discard changes in working directory)"""

            for modified_file in statusdict[' M']:
                print '#' + '\t' + 'modified:' + '\t' + Fore.RED + modified_file + Style.RESET_ALL
            for deleted_file in statusdict[' D']:
                print '#' + '\t' + 'deleted: ' + '\t' + Fore.RED + deleted_file + Style.RESET_ALL
            print '#'
        if len(statusdict['??']) > 0:
            print """# Untracked files:
#   (use "git ctx add <file>..." to include in what will be committed)
#           """

            for untracked_file in statusdict['??']:
                print '#' + '\t' + Fore.RED + untracked_file + Style.RESET_ALL
            print """no changes added to commit (use "git add" and/or "git commit -a")"""

    def generic_translateargs( self, git_cmd, git_argv ):
        from colorama import init
        init()
        from colorama import Fore, Back, Style
        for repo in self.git_repos:
            repo_path = repo.getAbsLocalPath()
            if not os.path.isdir(repo_path):
                return ''
            os.chdir(repo_path)

            import subprocess
            dashfile = False
            repo_name = os.path.basename(repo_path)
            repo_git_argv = list()
            # count arguments that are valid for the current repo
            # valid arguments are 
            # 1. those that begins with the name of the repo-dir with a preceeding '/', we're dealing with a file within the repo
            # 2. those that do not contain a '/', which most likely are comments or branch names
            #
            # arguments that begin with a '-' are options and are passed to the git command in a normal way IF there are valid arguments as specified above.
            
            valid_git_argv = list()
            for arg in git_argv:
                # if it starts with repo name...
                if arg[:len(repo_name + '/')] == repo_name + '/':
                    tmparg = arg.replace(os.path.basename(repo_path)+'/','',1)
                    repo_git_argv.append(tmparg)
                    valid_git_argv.append(tmparg)
                # if the argument is an option to be used for all...
                elif arg[0] == '-' and arg != '--':
                    repo_git_argv.append(arg)
                # if arg is the repo name...
                if arg == repo_name:
                    tmparg = '.'
                    repo_git_argv.append(tmparg)
                    valid_git_argv.append(tmparg)
                # if no / is found in the arg...
                if arg.find('/') == -1:
                    repo_git_argv.append(arg)
                    valid_git_argv.append(arg)
            if len(valid_git_argv) != 0:
                args = [self.git, git_cmd ]
                args.extend(valid_git_argv)
                print Fore.MAGENTA + 'ctx-git' + Fore.GREEN + ':' + Style.RESET_ALL,
                sys.stdout.write(' executing \'' + self.git + ' ' + git_cmd)
                for arg in valid_git_argv:
                    sys.stdout.write(' '+arg)
                print '\' in ' + os.path.basename(repo_path)

                p = subprocess.Popen(args, bufsize=4096, stdin=None)
                retcode = p.wait()

                if retcode != 0:
                    errorMessage("GIT execution failed with error code %d"%(retcode))
                    exit(retcode)

                os.chdir(self.view_dir)
        sys.exit(0)
 
    def generic( self, git_cmd, git_argv ):
        from colorama import init
        init()
        from colorama import Fore, Back, Style

        for repo in self.git_repos:
            repo_path = repo.getAbsLocalPath()
            if not os.path.isdir(repo_path):
                return ''
            os.chdir(repo_path)

            import subprocess
            args = [self.git, git_cmd ]
            args.extend(git_argv)
            print os.path.abspath('')
            print Fore.MAGENTA + 'ctx-git' + Fore.GREEN + ':' + Style.RESET_ALL,
            sys.stdout.write(' executing \'' + self.git + ' ' + git_cmd)
            for arg in git_argv:
                sys.stdout.write(' '+arg)
            print '\' in ' + os.path.basename(repo_path)


            p = subprocess.Popen(args, bufsize=4096, stdin=None)
            retcode = p.wait()

            if retcode != 0:
                errorMessage("GIT execution failed with error code %d"%(retcode))
                exit(retcode)

            os.chdir(self.view_dir)
        sys.exit(retcode)
    

gitctx = GITCtx()

if len(sys.argv) == 1:
    gitctx.help()
    sys.exit(1)
if sys.argv[1] == '-h' or sys.argv[1] == '--help':
    gitctx.help()
    sys.exit(1)
#
git_argv = list(sys.argv[2:])
if sys.argv[1] == 'status':
    gitctx.status(git_argv)
elif sys.argv[1] == 'add' or sys.argv[1] == 'rm' or sys.argv[1] == 'checkout' or sys.argv[1] == 'reset' or sys.argv[1] == 'commit':
    gitctx.generic_translateargs(sys.argv[1], git_argv)
else:
    gitctx.generic(sys.argv[1], git_argv)

