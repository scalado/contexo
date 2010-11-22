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
from contexo.ctx_common import errorMessage, warningMessage, infoMessage, userErrorExit

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
        self.git_commands = ['status', 'checkout', 'add', 'rm', 'reset']
        # some commands must be allowed to continue in other repos even if they failed in one
        # eg. one repo may be readonly and thus the other ones would not be able to push to.
        self.git_commands_continue_on_error = ['commit', 'push', 'branch']
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
        ctxview = ctx_view.CTXView(view_path=self.view_dir, updating=False, validate=False)

        for repo in ctxview.getRSpec().getRepositories():
            if repo.getRcs() == 'git':
                self.git_repos.append(repo)
            else:
                self.ignored_repos.append(repo)

    def help( self ):
        print """
git ctx is a component of the Contexo build system which integrates with the git toolsuite.
Any git command supplied to 'git ctx' will be executed for each subrepository in the view as defined by the Contexo .rspec.

git ctx performs all commands relative to the view root. Thus the output from git ctx status can be handled by the commands below.

usage: git ctx [git-command] [options] [--] <filepattern>...

git-command may be any of the following:
        """
        for git_command in self.git_commands:
            print '\t' + git_command
        print """
other commands are executed in each git repo.

Subversion repos are ignored.
"""
        sys.exit(42)

    def ignored_svn_repo_banner( self ):
        for ignored_repo in self.ignored_repos: 
            print 'git-ctx: ignoring \'svn\' repo: ' + os.path.basename(ignored_repo.getAbsLocalPath())
    def check_unmerged( self ):
        import subprocess
        for repo in self.git_repos:
            os.chdir(repo.getAbsLocalPath())
            args = [self.git, 'status', '--porcelain']
            p = subprocess.Popen(args, bufsize=4096, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stderr = p.stderr.read()
            stdout = p.stdout.read()
            #p.wait()
            for line in stdout.split('\n'):
                if line[1:2] == 'U' or line[:1] == 'U':
                    msg = 'there are unmerged changes in \''+os.path.basename(repo.getAbsLocalPath()) + '\', cannot continue'
                    userErrorExit(msg)
            os.chdir(self.view_dir)

    def status( self, git_argv ):
        self.ignored_svn_repo_banner()
        from colorama import init
        init()
        from colorama import Fore, Back, Style
        statusdict = dict()
        statusdict['M'] = set()
        statusdict['??'] = set()
        statusdict['A'] = set()
        statusdict['U'] = set()
        statusdict['R'] = set()
        statusdict['D'] = set()
        statusdict['C'] = set()

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
                    for key in [split_line[0], split_line[0][0], split_line[0][1]]:
                        if statusdict.has_key( key ):
                            statusdict[ key ].add( os.path.basename(repo_path) + '/' + split_line[1] )
        print '#'

        if len(statusdict['A']) > 0:
            print """# Changes to be committed:
#   (use "git ctx reset HEAD <file>..." to unstage)
#            """
            for new_file in statusdict['A']:
                print '#' + '\t' + 'new file:' + '\t' + Fore.GREEN + new_file + Style.RESET_ALL
            print '#'
        if len(statusdict['M']) > 0 or len(statusdict['D']) > 0 or len(statusdict['R']) > 0 or len(statusdict['C']) > 0:
            print """#
# Changed but not updated:
#   (use "git ctx add/rm <file>..." to update what will be committed)
#   (use "git ctx checkout -- <file>..." to discard changes in working directory)"""

            for modified_file in statusdict['M']:
                print '#' + '\t' + 'modified:' + '\t' + Fore.RED + modified_file + Style.RESET_ALL
            for deleted_file in statusdict['D']:
                print '#' + '\t' + 'deleted:' + '\t' + Fore.RED + deleted_file + Style.RESET_ALL
            # these two has not been observed in git 1.7, eventhough the git-status(1) documentation
            # mentions them
            for renamed_file in statusdict['R']:
                print '#' + '\t' + 'renamed:' + '\t' + Fore.RED + renamed_file + Style.RESET_ALL
            for copied_file in statusdict['C']:
                print '#' + '\t' + 'copied:' + '\t' + Fore.RED + copied_file + Style.RESET_ALL
            print '#'
        if len(statusdict['U']) > 0:
            print """# Unmerged paths:
#   (use "git ctx add/rm <file>..." as appropriate to mark resolution)
#           """
            for unmerged_file in statusdict['U']:
                # the Fore.RED is placed here to show similar output to git status
                print '#' + '\t' + Fore.RED + 'both modified:' + '\t' + unmerged_file + Style.RESET_ALL
            print '#'
        if len(statusdict['??']) > 0:
            print """# Untracked files:
#   (use "git ctx add <file>..." to include in what will be committed)
#           """

            for untracked_file in statusdict['??']:
                print '#' + '\t' + Fore.RED + untracked_file + Style.RESET_ALL
            print """no changes added to commit (use "git ctx add" and/or "git ctx commit -a")"""

    def generic( self, git_cmd, git_argv, translate_arguments = False, continue_on_error = False ):
        if git_cmd not in ['add', 'rm']:
            self.check_unmerged()
        self.ignored_svn_repo_banner()
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
            # git checkout can be used in the following scenario:
            # $ git checkout -b foo origin/bar
            if git_cmd == 'checkout' and git_argv.count('-b') != 0:
                translate_arguments = False

            if translate_arguments == True and len(valid_git_argv) != 0:
                args = [self.git, git_cmd ]
                args.extend(valid_git_argv)
                msg = ' executing \'' + self.git + ' ' + git_cmd
                for arg in valid_git_argv:
                    msg = msg + ' ' +arg
                msg = msg + '\' in ' + os.path.basename(repo_path)
                print 'git-ctx: ' + msg
                # TODO: doesn't work...
                #infoMessage(msg,0)

                p = subprocess.Popen(args, bufsize=4096, stdin=None)
                retcode = p.wait()

                if continue_on_error == False:
	            if retcode != 0:
        	        errorMessage("GIT execution failed with error code %d"%(retcode))
                        exit(retcode)

            elif translate_arguments == False:
                args = [self.git, git_cmd ]
                args.extend(git_argv)
                msg = ' executing \'' + self.git + ' ' + git_cmd
                for arg in git_argv:
                    msg = msg + ' ' +arg
                msg = msg + '\' in ' + os.path.basename(repo_path)
                print 'git-ctx: ' + msg
                # TODO: doesn't work...
                #infoMessage(msg,0)

                p = subprocess.Popen(args, bufsize=4096, stdin=None)
                retcode = p.wait()

                if continue_on_error == False:
	            if retcode != 0:
        	        errorMessage("GIT execution failed with error code %d"%(retcode))
                        exit(retcode)

            os.chdir(self.view_dir)
        sys.exit(0)

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
elif gitctx.git_commands_continue_on_error.count(sys.argv[1]):
    translate_arguments = True
    continue_on_error = True
    gitctx.generic(sys.argv[1], git_argv, translate_arguments, continue_on_error)
elif gitctx.git_commands.count(sys.argv[1]):
    translate_arguments = True
    gitctx.generic(sys.argv[1], git_argv, translate_arguments)
else:
    gitctx.generic(sys.argv[1], git_argv)

