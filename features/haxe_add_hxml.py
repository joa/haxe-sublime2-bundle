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
            if os.path.exists( p ) :
                HaxeComplete_inst().read_hxml( p );
                if( int(sublime.version()) > 3000 ) : 
                    proj = win.project_file_name()
                    if proj is not None :
                        proj_path = os.path.dirname( proj )
                        rel_path = os.path.relpath( p , proj_path )
                        data = win.project_data()
                        print(data)
                        if data['settings'] is None :
                            data['settings'] = {}
                        if data['settings']['haxe_build_files'] is None :
                            data['settings']['haxe_build_files'] = []

                        build_files = data['settings']['haxe_build_files'];
                        build_files.append( rel_path )

                        win.set_project_data( data )

                
