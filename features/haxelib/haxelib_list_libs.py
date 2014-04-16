import sublime
import sublime_plugin
import textwrap

try: # Python 3
    from ...HaxeHelper import runcmd, show_quick_panel
except (ValueError): # Python 2
    from HaxeHelper import runcmd, show_quick_panel

print("HAXE : haxelib search ")

class HaxelibListLibs( sublime_plugin.WindowCommand ):
    def run(self):

        settings = self.window.active_view().settings()
        haxelib_path = settings.get("haxelib_path","haxelib")

        out,err = runcmd([ haxelib_path , "search"], " \n \n \n");
        lines = out.splitlines()

        if len(lines) > 0 :
            #remove the initial prompt
            lines[0] = lines[0].replace("Search word : ","")

        #sort alphabetically
        lines = sorted( lines , key = str.lower )

        #store for later
        self.libs = lines

        #show list
        show_quick_panel(self.window,lines,self.on_lib_select)


    def on_lib_select(self, index):
        if(index < 1):
            return

        name = self.libs[index]
        self.selected = name

        menu = []
        menu.append( ["Info", "haxelib info " + name] ) 
        menu.append( ["Install", "haxelib install " + name] )

        show_quick_panel(self.window, menu, self.on_action_selected)

    def on_action_selected(self, index):
        if(index < 0):
            return

        #info
        if index == 0:
            self.do_action("info",self.selected)
        #install
        elif index == 1:
            self.do_action("install",self.selected)

    def do_action(self,action,library):

        settings = self.window.active_view().settings()
        haxelib_path = settings.get("haxelib_path","haxelib")

        out,err = runcmd([ haxelib_path , action, self.selected]);
        lines = out.splitlines()

        # the description can be rather long,
        # so we just split it up some
        if action == "install":

            show_quick_panel(self.window,lines,None)
            return

        if action == "info":
            max_length = 60

            #store the desc
            desc = lines[2]
            #remove it from the list
            del lines[2]            
            
            #wrap it neatly
            descsplit = textwrap.wrap(desc,max_length) 

            #now replace the Desc: into it's own line
            descsplit[0] = descsplit[0].replace('Desc: ','')
            descsplit.append('')
            descsplit.reverse()

            #reinsert
            for d in descsplit:
                lines.insert(2,"\t\t"+d)

            #and the desc header
            lines.insert(2, 'Desc: ')

        for index, line in enumerate(lines):
            length = len(line)
            if(length > max_length):
                split_lines = textwrap.wrap(line,max_length)
                lines[index] = split_lines[0] + ' ...'
        
        show_quick_panel(self.window,lines,None)
