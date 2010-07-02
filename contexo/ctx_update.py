#! /usr/bin/env python

#############################################################################
# Contexo live update module.                                               #
# By Manuel Astudillo (c) 2007.                                             #
#                                                                           #
#                                                                           #
# This utility shall be placed in contexo/update directory, with other      #
# support files such as: config files, pre_update.py, post_update.py, etc.  #
#                                                                           #
#############################################################################

try:
    import pysvn
except:
    print "\n*** Error: pysvn module is required but it was not found in the system!\n"
    print "please download it and install it before running this script:\n"
    print "http://pysvn.tigris.org/servlets/ProjectDocumentList?folderID=1768"
    exit()
    
from urlparse import urlparse
import shutil
import sys
import os.path
from os.path import join
from ctx_common import getUserTempDir, getContexoRoot, infoMessage, errorMessage, ctxExit

user = "update"
pwd  = "j44cKz1mn"
release_url = "https://svn.scalado.com/contexo/releases"

def compare_version ( a, b ):
    if ( a == b ):
        return 0
    elif ( a > b ):
        return 1
    else:
        return -1              

def release_cmp ( x, y ):
    return compare_version ( x[0], y[0] )
    
def get_current_version (contexo_root):
    version_file = join (join (contexo_root, "update"), "ctx_version")
    if os.path.exists (version_file):
        f = open ( version_file )
        version = f.read ().strip()
        f.close ()
        return version
    else:
        return 'ctx-0.0.0'
        
def is_valid_release ( release ):
    ctx = release.split("-")
    if len (ctx) != 2:
        return False
    
    if ctx[0] != "ctx":
        return False
    
    if len(ctx[1].split(".")) != 3:
        return False
        
    return True
       
def get_login( realm, username, may_save ):
    return True, user, pwd, False
    
def ssl_server_trust_prompt( trust_dict ):
    return True, 0, False
   
    
def get_release_list(svn_client, repos):
    rel_list = svn_client.list ( repos,recurse=False )

    rel_dict = dict()

    for item in rel_list:
        path = item[0].path
        release = os.path.basename(urlparse (path)[2])
    
        if is_valid_release ( release ):
            rel_dict[release] = path

        
    return rel_dict

#
# Return a list of updates
#
def get_required_list(svn_client, cur_rel, rel_dict):
    
    s = sorted(rel_dict, reverse=True)
    release = s[0]
    req_list = []
    
    while release > cur_rel:
        
        if not rel_dict.has_key(release):
            print "Error: missing required release " + release
            return []
            
        req_list.append ( ( release, rel_dict[release] ))
        
        prop = svn_client.propget ( "contexo-require", rel_dict[release] )
        if len(prop) > 0:
            req_rel =prop.items()[0][1]
            if req_rel == release:
                print "Error: required release: " + release + " cannot be updated automatically!"
                return []
            if is_valid_release ( req_rel ) and req_rel > cur_rel:
                release = req_rel
            else:
                break
        else:
            break
                   
    req_list.sort(release_cmp)
    return req_list
    
    
def is_time_to_update( interval ):
    import cPickle
    import datetime
    
    contexo_cfg_dir = getUserTempDir ()

    #
    # load last update
    #
    date_file = os.path.join ( contexo_cfg_dir, "date_file.ctx" )
    
    if os.path.exists ( date_file ):
        f = open ( date_file, 'rb' )
        date = cPickle.load ( f )
        f.close ()
        if datetime.date.today() - date < datetime.timedelta (interval):
            return False
        else:
            os.remove ( date_file )
       
    f = open ( date_file, 'wb' )
    cPickle.dump ( datetime.date.today(), f )
    f.close ()
    return True
            
def update_to_release ( svn_client, release, contexo_root ):

    cur_rel = get_current_version ( contexo_root )

    infoMessage("Updating " + cur_rel + " to release: " + release[0], 0) 
    
    update_dir = os.path.join (contexo_root, "update" )
    
    #
    # call system/pre_update.py
    #
    os.chdir (update_dir)
    execfile ( "pre_update.py" )
    
    #
    # Svn switch to release ( would like to export here )
    #
    shutil.rmtree ( contexo_root, ignore_errors = True )
    svn_client.export( release[1], contexo_root, force=True )
    
    #
    # install modules
    # call system/install_pymods.py
    #
    system_dir = os.path.join (contexo_root, "system" )
    os.chdir (system_dir)
    execfile( "install_pymods.py" )
    
    #
    # Perform other post update activities
    # call system/post_update.py
    #
    os.chdir (update_dir)
    execfile ( "post_update.py" )

def update_tool():
    infoMessage("Running contexo update tool (c) Scalado 2007", 0)

    try:
        contexo_root = os.path.abspath(getContexoRoot ())
   
        svn_client = pysvn.Client ()

        svn_client.callback_get_login = get_login
        svn_client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        rel_dict = get_release_list (svn_client, release_url )

        # Get current release ( check property: contexo-release )
        cur_rel = get_current_version ( contexo_root )

        if len(rel_dict) > 0:
            update_list = get_required_list (svn_client, cur_rel, rel_dict )

        #</>
        # If len (update_list) > 0, there are updates to perform. 
        #
        update = False
        if len ( update_list ) > 0:
            update = raw_input ("Updates available, update to the latest version? (y)/(n)")
            if update == 'y':
                for item in update_list:
                    update_to_release ( svn_client, item, contexo_root )

                cur_rel = get_current_version ( contexo_root )
                infoMessage("Contexo is up-to-date. Current installed version is: " + cur_rel, 0) 
    
                update = True
    
        cur_rel = get_current_version ( contexo_root )
        infoMessage("Contexo is up-to-date. Current installed version is: " + cur_rel, 0) 
    
        return update
    except:
        infoMessage("Contexo failed to be updated...")
        return False
    
if is_time_to_update ( 1 ):
    if update_tool () == True:
        ctxExit(0)
        
        

