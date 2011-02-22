
import os.path
import ctx_common

homedir = ctx_common.getUserCfgDir()
default_config = {   'cdef-paths': os.path.join(homedir, 'cdef'),
                    'bconf-paths': os.path.join(homedir, 'bconf'),
                      'env-paths': os.path.join(homedir, 'env'),
                      'verbosity': 1,
                   'current-view': '' }

def getFullConfigFileName():
    return os.path.join(ctx_common.getUserCfgDir(), 'config.py')

def serialize(config):
    pass

def readconfig():
    env = dict()
    env['config'] = default_config
    env['contexo_config_dir'] = ctx_common.getUserCfgDir()
    env['user_home_dir'] = ctx_common.getUserDir()
    try:
        execfile(   getFullConfigFileName(),  {},  env )
    except Exception, e:
        import sys
        print('Configuration Error: %s'%str(e))
        sys.exit(2)
