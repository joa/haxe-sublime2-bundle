import sublime
import sublime_plugin

from ...HaxeHelper import runcmd

# from .haxelib_list_libs import HaxelibListLibs

print("HAXE : haxelib install ")

class HaxelibInstallLib( sublime_plugin.WindowCommand ):
    def run(self):

        menu = []
        menu.append(["Install by name", "Manually enter a library name"])
        menu.append(["Install from list", "Show a big list of libraries"])
        self.window.show_quick_panel(menu, self.on_select)
        
    def on_select(self,index):
        if(index < 0):
            return
        if(index == 0):
            self.window.show_input_panel("Enter lib name to install", "", self.on_input, None, None )
        elif index == 1:
            self.window.run_command("haxelib_list_libs")

    def on_input(self, value):
        if(value != ""):            
            out,err = runcmd(["haxelib" , "install", value]);
            outlines = out.splitlines()
            sublime.status_message(str(outlines));
            self.window.show_quick_panel(outlines, None, sublime.MONOSPACE_FONT)
        else:
            self.window.show_quick_panel( [["Invalid library name","Hit return to try again, escape to cancel"]], self.on_invalid )

    def on_invalid(self,index):
        if(index < 0):
            return

        sublime.run_command("haxelib_install_lib");
