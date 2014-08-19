import sublime_plugin
import sublime
import os

try: # Python 3
    from ..HaxeHelper import HaxeComplete_inst, isType
except (ValueError): # Python 2
    from HaxeHelper import HaxeComplete_inst, isType

print("hello")
class HaxeAddHxml( sublime_plugin.WindowCommand ):

    def run( self , paths = [] ) : 
        for p in paths :
            i = HaxeComplete_inst();
            i.read_hxml( p );
