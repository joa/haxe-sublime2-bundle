import sublime_plugin
import sublime
import os

try: # Python 3
    from ..HaxeHelper import HaxeComplete_inst, isType
except (ValueError): # Python 2
    from HaxeHelper import HaxeComplete_inst, isType

print("hello")
class HaxeAddHxml( sublime_plugin.WindowCommand ):

    # add builds from hxml and append to project settings
    def run( self , paths = [] ) : 
        win = self.window

        for p in paths :
            if os.path.isfile( p ) :
                for b in HaxeComplete_inst().read_hxml( p ) :
                    HaxeComplete_inst().add_build( b )

                if( int(sublime.version()) > 3000 ) : 
                    proj = win.project_file_name()
                    if proj is not None :
                        proj_path = os.path.dirname( proj )
                        rel_path = os.path.relpath( p , proj_path )
                    else :
                        rel_path = p

                    data = win.project_data()
                    
                    if 'settings' not in data :
                        data['settings'] = {}
                    if 'haxe_builds' not in data['settings'] :
                        data['settings']['haxe_builds'] = []

                    build_files = data['settings']['haxe_builds'];
                    build_files.append( rel_path )

                    win.set_project_data( data )

    def is_enabled( self , paths = [] ) :
        for p in paths :
            if os.path.isfile( p ) :
                return True

        return False

                
