###############################################################################
#
#   ctx_export.py
#   Component or Contexo - (c) Scalado AB 2009
#
#   Author: Robert Alm 
#
#   ------------
#
#
###############################################################################

from ctx_common import userErrorExit, infoMessage, getUserCfgDir, setInfoMessageVerboseLevel
import ctx_cfg
import os

export_header = "$EXPORT_PACKAGE$"

#CONTEXO_CFG_FILE    = 'contexo.cfg'
#cfgFile = ctx_cfg.CFGFile (os.path.join( getUserCfgDir(), CONTEXO_CFG_FILE ))
#setInfoMessageVerboseLevel( int(cfgFile.getVerboseLevel()) )

#------------------------------------------------------------------------------
class CTXExportData:
    def __init__( self ):

        self.msgSender = 'CTXExportData'
        self.export_data = dict()

    #--------------------------------------------------------------------------
    # Sets all export data items. Any existing data is truncated.
    #--------------------------------------------------------------------------
    def setExportData( self, modules, components, do_tests, build_session,
                       dependency_manager, view, env, cmdline_options ):

        from ctx_repo import REPO_PATH_SECTIONS

        self.export_data = dict()
        self.export_data['MODULES']       = modules if modules != None and len(modules) else list()
        self.export_data['COMPONENTS']    = components if components != None and len(components) else None
        self.export_data['TESTS']         = do_tests
        self.export_data['SESSION']       = build_session
        self.export_data['DEPMGR']        = dependency_manager
        self.export_data['ENV']           = env
        #self.export_data['OUTPUT_DIR']    = cmdline_options.output

        self.export_data['PATHS']         = dict()
        for section in REPO_PATH_SECTIONS:
            self.export_data['PATHS'][section.upper()] = view.getItemPaths(section)

        # TODO: RSpecFile can't be pickled for some reason. When it has been solved,
        # remove this code and simply pass the RSpecFile object to the client plugin.
        # Note that existing plugins then have to be updated.
        self.export_data['RSPEC']         = dict()
        view_rspec = view.getRSpec()
        if view_rspec != None:
            def recurse_level(rspec, tree):
                #print tree
                tree[rspec.getFilename()] = dict()
                for imp_rspec in rspec.getImports():
                    tree[rspec.getFilename()] = recurse_level( imp_rspec, tree[rspec.getFilename()] )
                    
                return tree
            # 
            self.export_data['RSPEC'] = recurse_level( view_rspec, self.export_data['RSPEC'] )
    
        #print self.export_data['RSPEC']
    #------------------------------------------------------------------------------
    # Sends the export_package as a pickle-dump to stdout. The package is directly
    # preceeded by a header with the following format:
    #
    # $EXPORT_PACKAGE:##$
    #
    # Where ## is an alphanumeric number specifying the size in characters of the
    # exported chunk.
    # This function is intended to be used by the main system when sending export
    # data to an export handler. The inverse of this method is receive().
    #
    #------------------------------------------------------------------------------
    def dispatch( self ):
        import pickle
        import sys
        
        export_dump = pickle.dumps( self.export_data )
        package = '%s%d$'%(export_header, len(export_dump))
        
        infoMessage("Dispatching package to 'stdout'", 2)
        
        sys.stdout.write( package )
        sys.stdout.write( export_dump )
    
    #--------------------------------------------------------------------------
    # Processes all data from stdin. Prints anything not recognized as part of 
    # the export data as normal text to stdout.
    # The export buffer is unpickled and then replaces all existing export data
    # items.
    #
    # This function is intended to be used by the receiving export handler.
    #
    #--------------------------------------------------------------------------
    def receive( self ):
        import pickle
        import sys
   
        data_buffer = str(sys.stdin.read())
    
        #
        # Locate package header
        #
        
        i = data_buffer.rfind( export_header )
        
        if i == -1:
            print data_buffer #Most likely errors from main system
            infoMessage("\n********** Export handler entry point **********\n\n", 2)
            userErrorExit("Ctx export failed because of previous errors! Check the log for previous errors.")
            
        #
        # Extract package size
        #
        
        i += len(export_header)
        size_s = ""
        header_len = len(export_header)
        while data_buffer[i] != '$':
            size_s += data_buffer[i]
            header_len += 1
            i += 1
            
        header_len += 1
        package_start = i+1
        package_size  = int(size_s)
        package_end   = package_start + package_size
        
        #
        # Extract package chunk, and print everything else as regular text
        #
        
        package_dump = data_buffer[ package_start : package_end ]
        print data_buffer[ 0 : package_start - header_len ]
        print data_buffer[ package_end : -1 ]

        infoMessage("\n********** Export handler entry point **********\n\n", 2)
        
        #
        #  Unpickle
        #        
        
        self.export_data = pickle.loads( package_dump )
        
