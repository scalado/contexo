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

import os.path
from contexo import ctx_repo
from contexo import ctx_rspec
from contexo import ctx_view

class GITCtx:
    def __init__( self ):
	self.git_repos = list()
	self.ignored_repos = list()
	print 'foo'
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
	view_dir = os.path.abspath('')
	ctxview = ctx_view.CTXView(view_dir)
	#ctxview.printView()

	#path = os.abs

gitctx = GITCtx()
gitctx.print_all()

#argparser?