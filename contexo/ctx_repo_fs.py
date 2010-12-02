###############################################################################
#                                                                             #
#   ctx_repo_fs.py                                                            #
#   Component of Contexo - (c) Scalado AB 2009                                #
#                                                                             #
#   Author: Robert Alm                                                        #
#                                                                             #
#   ------------                                                              #
#                                                                             #
#   Implementation of CTXRepository for regular file systems                  #
#                                                                             #
###############################################################################

from ctx_repo import *
from ctx_common import ctxAssert, userErrorExit, infoMessage

#------------------------------------------------------------------------------
def genTreeChecksum( root_folder, md5_checksum ):
    ctxAssert( os.path.isdir(root_folder), "Existance of folder must be checked prior to this call" )

    folder_items = os.listdir( root_folder )

    for item_name in folder_items:

        md5_checksum.update( item_name )

        item_path = os.path.join( root_folder, item_name )

        if os.path.isdir( item_path ):
            genTreeChecksum( item_path, md5_checksum ) # POINT OF RECURSION
        else:
            ctxAssert( os.path.isfile(item_path), "Path concatenation probably went wrong here" )

            f = open( item_path, 'rb' )
            contents = f.read()
            f.close()
            md5_checksum.update( contents )

    return md5_checksum

#------------------------------------------------------------------------------
# This function compares two tree structures and evaluates if they are equal
# by checksum comparison. The checksums are generated from file/folder
# structure and file contents. Returns True if trees are equal, else False.
#------------------------------------------------------------------------------
def treesAreEqual( root_folderA, root_folderB ):
    import hashlib

    md5_checksum = hashlib.md5()
    md5_checksum = genTreeChecksum( root_folderA, md5_checksum )
    checksumA = md5_checksum.hexdigest()

    md5_checksum = hashlib.md5()
    md5_checksum = genTreeChecksum( root_folderB, md5_checksum )
    checksumB = md5_checksum.hexdigest()

    return bool(checksumA == checksumB)


#------------------------------------------------------------------------------
class CTXRepositoryFS(CTXRepository):
    def __init__(self, id_name, local_path, href, rev):
        self.path = os.path.join(local_path, id_name)

        if href == None:
            # No remote repo source given, see if we have a local representation
            if os.path.exists( self.path ):
                href = self.path

        if href == None:
            userErrorExit("No HREF specified for repository '%s'. Failed to aquire HREF from local copy '%s'"\
                           %(id_name, self.getAbsLocalPath()))

        CTXRepository.__init__( self, id_name, local_path, href, None, version_control=False )
        self.msgSender = "CTXRepositoryFS"

    #--------------------------------------------------------------------------
    def isLocal(self):
        return os.path.isdir( self.getAbsLocalPath() )

    def getRcs(self):
       return ''
    #--------------------------------------------------------------------------
    def update(self):
        if not treesAreEqual( self.getAbsLocalPath(), self.getHref() ):

            print '\n'
            infoMessage("Regular file repository '%s' is out of sync.\n'%s' and '%s' doesn't match. The system is unable to\nperform intelligent synchronization of non-revisioned repositories.\nDo you want to overwrite (delete and replace) the local copy '%s'\nwith the contents of the remote copy '%s'?"\
                %(self.getID(), self.getAbsLocalPath(), self.getHref(), self.getAbsLocalPath(), self.getHref() ), 0)
            choice = raw_input( "> yes/no: " ).lower()

            while choice not in ['yes','no']:
                infoMessage("Invalid choice, try again.", 0)
                choice = raw_input( "> yes/no: " ).lower()

            if choice == 'yes':
                infoMessage("Updating (replacing) local copy '%s' with '%s'"\
                    %(self.getAbsLocalPath(), self.getHref()), 1)

                shutil.rmtree( self.getAbsLocalPath() )
                shutil.copytree( self.getHref(), self.getAbsLocalPath() )

            elif choice == 'no':
                infoMessage("Skipping update of repository '%s'"%self.getID(), 2)

            else:
                ctxAssert( False, "Unhandled choice" )
        else:
            infoMessage("Repository '%s' (%s) is up to date"%(self.getID(), self.getHref()), 1)

    #--------------------------------------------------------------------------
    def checkout(self):
        import shutil
        import ctx_view
        ctxAssert( self.isLocal() == False,
                   "This method should not be called without first checking for an existing local copy." )

        infoMessage("Checking out repository '%s' (%s) to '%s'"
            %(self.getID(), self.getHref(), self.getAbsLocalPath()), 1)
        shutil.copytree( self.getHref(), self.getAbsLocalPath() )

    #--------------------------------------------------------------------------
    def checkValidRevision(self):
        # Not applicable to non revisioned repositories
        return True

    #--------------------------------------------------------------------------
    def checkValid(self, updating ):
        # TODO: Check that local/remote representation matches the set
        # access policy.
        return True
