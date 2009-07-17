import pysvn
import os

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def svn_get_login_callback( realm, username, may_save ):
    print "Subversion login:"
    username = raw_input( 'Username: ' )
    password = getpass.getpass( 'Password: ' )
    save_credentials = True
    return True, username, password, save_credentials


client = pysvn.Client()
client.callback_get_login = svn_get_login_callback

updatePath = os.path.join( os.environ['CONTEXO_ROOT'], 'rep', 'bc' )
client.update( updatePath )

raw_input( "Update completed, press any key.." )