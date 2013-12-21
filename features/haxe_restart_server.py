import sublime_plugin
import sublime

class HaxeRestartServer( sublime_plugin.WindowCommand ):

    def run( self ) :
        view = sublime.active_window().active_view()
        HaxeComplete.inst.stop_server()
        HaxeComplete.inst.start_server( view )
