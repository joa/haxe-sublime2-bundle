import os.path
import codecs
import sublime
import sublime_plugin
import re

try: # Python 3
    from ..HaxeHelper import HaxeComplete_inst
except (ValueError): # Python 2
    from HaxeHelper import HaxeComplete_inst

posRe = re.compile("^(.*):(\\d+):\\ (lines|characters)\\ (\\d+)-(\\d+)$")

class HaxeFindDefinition( sublime_plugin.TextCommand ):

    def run( self , edit ) :

        view = self.view

        # get word under cursor
        word = view.word(view.sel()[0])

        # get utf-8 byte offset to the end of the word
        src = view.substr(sublime.Region(0, word.b))
        offset = len(codecs.encode(src, "utf-8")) + 1 # add 1 because offset is 1-based

        complete = HaxeComplete_inst()

        # save file and run completion
        temp = complete.save_temp_file( view )
        pos = complete.run_haxe(view, dict(
            mode="position",
            filename=view.file_name(),
            offset=offset,
            commas=None
        ))
        complete.clear_temp_file( view , temp )

        if pos is None:
            status = "Definition of '" + view.substr(sublime.Region(word.a, word.b)) + "' not found."
            self.view.set_status( "haxe-status", status )
            return
        else :
            pos = pos.strip()

        # parse position
        m = posRe.match(pos)
        filename = m.group(1)
        line = int(m.group(2)) - 1
        mode = m.group(3)
        start = int(m.group(4))
        if mode == "lines":
            start = 0

        if os.name == "nt":
            filename = self.get_windows_path(filename)

        # open definition file in the active window and go to given position
        window = sublime.active_window()
        view = window.open_file(filename)
        self.goto_pos(view, line, start)

    def get_windows_path(self, path):
        dir, file = os.path.split(path)
        for f in os.listdir(dir):
            if (f.lower() == file):
                return os.path.join(dir, f)
        return path

    def goto_pos(self, view, row, off):
        # wait until file is loaded
        if view.is_loading():
            sublime.set_timeout(lambda: self.goto_pos(view, row, off), 10)
            return

        pt = view.text_point(row, 0)

        # if there's a character offset, convert from utf-8 byte offset to actual character position
        if off > 0:
            line = view.substr(view.full_line(pt))
            src = codecs.encode(line, "utf-8")[:off]
            col = len(codecs.decode(src, "utf-8"))
            pt = view.text_point(row, col)

        # move cursor to given position
        view.sel().clear()
        view.sel().add(sublime.Region(pt))
        view.show_at_center(pt)
