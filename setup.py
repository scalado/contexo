from distutils.core import setup
import shutil
import sys
import os

#------------------------------------------------------------------------------
def win32reg_add_to_path( path ):
    import _winreg

    KEY_PATH = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment' 
    
    root_key = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
    key      = _winreg.OpenKey( root_key, KEY_PATH, 0, _winreg.KEY_ALL_ACCESS )
    path_var = _winreg.QueryValueEx( key, "path" )[0]
    
    exists = False
    for path_item in path_var.lower().split(u';'):
        if path.lower().rstrip('\\/;') == path_item.rstrip('\\/'):
            exists = True

    if not exists:
        path_var += ';%s'%( path.strip(';') )
        _winreg.SetValueEx( key, "path", 0, _winreg.REG_EXPAND_SZ, path_var )

    # To trigger system wide event about the change:
    #  win32gui.SendMessage(win32con.HWND_BROADCAST, 
    #                       win32con.WM_SETTINGCHANGE, 
    #                       0, 
    #                       'Environment') 
    #
    # Requires modules win32gui and win32con
    #
    #

    _winreg.CloseKey( key )
    _winreg.CloseKey( root_key )

#------------------------------------------------------------------------------
def win32reg_add_dword_value( key_path, val_name, value ):
    import _winreg
    root_key = _winreg.ConnectRegistry( None, _winreg.HKEY_LOCAL_MACHINE )
    key = _winreg.OpenKey( root_key, key_path, 0, _winreg.KEY_ALL_ACCESS )
    _winreg.SetValueEx( key, val_name, 0, _winreg.REG_DWORD, value )
    _winreg.CloseKey( key )
    _winreg.CloseKey( root_key )


############# ENTRY POINT #####################################################

shutil.rmtree('build', 1)

setup(name="Contexo",
      version="0.4.0",
      description="Contexo build system",
      author="Manuel Astudillo",
      author_email="manuel.astudillo@scalado.com",
      url="http://www.scalado.com",
      scripts =  ['contexo/cmdline/ctx.py', 'contexo/cmdline/ctx.bat'],
      package_dir = { 'contexo.defaults':'defaults' ,'': 'otherlibs',  'contexo':'contexo'},  #the '':'otherlibs' is a hack to make it load argparse without a package, from a subdirectory otherlibs
      package_data={ 'contexo.defaults': ['contexo.cfg', 'config.py', 'bconfs/*', 'cdefs/*' ], 'contexo.plugins.export': ['msvc.bat','rspectree.bat'] },
      packages = [ 'contexo.defaults', 'contexo' ,  'contexo.platform', 'contexo.plugins', 'contexo.plugins.export' ],
      py_modules = ['argparse']  #this will overwrite argparse if you already have it
     )


#
# --- WINDOWS SPECIFICS ---
#
if sys.platform == 'win32':

    import contexo.ctx_common as ctx_common
    import shutil
    from os.path import join as pjoin

    python_path    = os.path.dirname( sys.executable )
    contexo_path   = pjoin( python_path, 'Lib\site-packages\contexo' )
    default_bconfs = pjoin( contexo_path, 'defaults/bconfs' )
    default_cdefs  = pjoin( contexo_path, 'defaults/cdefs' )
    
    
    # Create user profile directories
    for subdir in ['plugins', 'bconf', 'cdef', 'env']:
        subdir = pjoin( ctx_common.getUserCfgDir(), subdir )
        if not os.path.exists( subdir ):
            os.makedirs( subdir )

    # Copy standard bconf items
    for bconf in os.listdir( default_bconfs ):
        dst = pjoin(ctx_common.getUserCfgDir(), 'bconf', bconf)
        if not os.path.exists( dst ):
            shutil.copyfile( pjoin(default_bconfs, bconf), dst )
    
    # Copy standard cdef items
    for cdef in os.listdir( default_cdefs ):
        dst = pjoin(ctx_common.getUserCfgDir(), 'cdef', cdef)
        if not os.path.exists( dst ):
            shutil.copyfile( pjoin(default_cdefs, cdef), dst )
    
    # Copy standard config
    dst = pjoin(ctx_common.getUserCfgDir(), 'contexo.cfg')
    if not os.path.exists( dst ):
        shutil.copyfile( pjoin(contexo_path, 'defaults/contexo.cfg'), dst )
                
            
    #
    # Add registry value to fix the Windows problem that piped scripts
    # doesn't get executed with the python interpreter.
    # Example:
    # ctx.py export [params] | msvc.py [params]
    # msvc.py isn't executed here with the python interpreter, unless
    # we use it explicitly:
    # ctx.py export [params] | python.exe msvc.py [params]
    #
    # In order to make it work without specifying python.exe, we add
    # the registry value "InheritConsoleHandles" in 
    # HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer
    # with DWORD decimal value 1.
    #
    
    key = r'Software\Microsoft\Windows\CurrentVersion\Policies\Explorer'
    win32reg_add_dword_value( key, r'InheritConsoleHandles', 1 )
    
    #
    # Add standard contexo paths to windows environment PATH
    #

    # The Python installation path
    win32reg_add_to_path( python_path )

    # The Python##/Script directory
    scripts_path = os.path.join( python_path, 'Scripts' )
    win32reg_add_to_path( scripts_path )
    
    # The contexo plugin directories
    system_export_plugins_path = os.path.join( python_path, 
                                               'Lib\site-packages\contexo\plugins\export' )
    win32reg_add_to_path( system_export_plugins_path )

    # The user plugins directory
    user_plugins_path = os.path.join( ctx_common.getUserCfgDir(), 'plugins' )
    win32reg_add_to_path( user_plugins_path )

# End of Win32 specific stuff    
    
    