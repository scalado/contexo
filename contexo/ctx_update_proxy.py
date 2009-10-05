import os
from os.path import join
from ctx_common import *

if os.environ.has_key ("CONTEXO_ROOT"):
    contexo_root = os.environ['CONTEXO_ROOT']
    update = join ( join ( join ( contexo_root, "system"), "core"),"ctx_update.py")
    execfile (update)
else:
    errorMessage("Error: CONTEXO_ROOT is not defined")



