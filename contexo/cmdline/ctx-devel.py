#!/usr/bin/env python
import sys
import os.path

(systempath,  commandlinedir) = os.path.split( os.path.dirname(__file__) )
(rootpath,  systemdir) = os.path.split( systempath)

sys.path.insert(1,  str(os.path.join(rootpath, 'otherlibs' ) ) )
sys.path.insert(1, str( rootpath ))
execfile(os.path.join(systempath,  commandlinedir,  'ctx.py'))
