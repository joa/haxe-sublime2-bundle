import sublime_plugin
import sublime

try: # Python 3
    from ..HaxeHelper import HaxeComplete_inst
except (ValueError): # Python 2
    from HaxeHelper import HaxeComplete_inst

class HaxeRestartServer( sublime_plugin.WindowCommand ):

    def run( self ) :
        view = sublime.active_window().active_view()
        HaxeComplete_inst().stop_server()
        HaxeComplete_inst().start_server( view )
