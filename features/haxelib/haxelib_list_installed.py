import sublime
import sublime_plugin

try: # Python 3
    from ...HaxeHelper import runcmd, show_quick_panel
except (ValueError): # Python 2
    from HaxeHelper import runcmd, show_quick_panel
   
print("HAXE : haxelib list ")

class HaxelibListInstalled( sublime_plugin.WindowCommand ):
    def run(self, paths = [] , t = "list"):
        
        self.action = t

        settings = self.window.active_view().settings()
        haxelib_path = settings.get("haxelib_path","haxelib")

        out,err = runcmd([haxelib_path , "list"]);

        libs = out.splitlines()
        
        self.libs = []        
        menu = []
        for _lib in libs :
            libname,libcurrent,libversions = self.haxelib_parse_libversions(_lib)
            menu.append([ libname + "   " + libcurrent , libversions ])
            self.libs.append(libname)

        self.window.show_quick_panel( menu, self.on_select )

    def on_select(self, index) :
        if(index < 0):
            return;

        if(self.action == "remove"):
            self.do_remove(self.libs[index])
        elif(self.action == "update"):
            self.do_update(self.libs[index])

    def do_remove(self,library):
    
        sublime.status_message("Please wait, removing haxelib " + library);

        settings = self.window.active_view().settings()
        haxelib_path = settings.get("haxelib_path","haxelib")

        out,err = runcmd([haxelib_path , "remove", library]);
        sublime.status_message(str(out))
        show_quick_panel(self.window, out.splitlines(), None)

    def do_update(self,library):
    
        sublime.status_message("Please wait, updating haxelib " + library);

        settings = self.window.active_view().settings()
        haxelib_path = settings.get("haxelib_path","haxelib")

        out,err = runcmd([haxelib_path , "update", library]);
        sublime.status_message(str(out))        
        show_quick_panel(self.window, out.splitlines(), None)

    def haxelib_parse_libversions( self, libinfo ):
        # the info comes in along these lines format: 3.0.2 [3.0.4]
        # so first : is the lib name, the ones inside of [ ] is active and 
        # the rest are installed but not active.
        first_colon = libinfo.find(':');
        libname = ''
        versions = 'unknown'
        active_version = 'unknown'

        #parse the lib name and versions separately
        if(first_colon != -1) :
            libname = libinfo[0:first_colon]
            versions = libinfo[first_colon+1:].split()

        # now parse the versions into active and inactive list
        for _version in versions:
            if(_version.find("[") != -1):
                active_version = _version

        #remove the active from the list
        if active_version in versions: versions.remove(active_version)

        #parse for better output
        versions_str = (", ".join(str(x) for x in versions)).replace('dev:','')
        active_version_str = str(active_version).replace('dev:','')
        active_str = str(active_version).strip('[]')

        #nicer output if none others
        if(versions_str == ""):
            versions_str = "none"

        #parse the dev flag
        if(active_str.find("dev:") != -1):
            active_str = "dev"

        return libname, active_version_str, "active: " +active_str +"   installed: " + versions_str
