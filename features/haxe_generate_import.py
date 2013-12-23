import sublime
import sublime_plugin
import re

try: # Python 3
    from ..HaxeHelper import wordChars, importLine, packageLine, spaceChars
except (ValueError): # Python 2
    from HaxeHelper import wordChars, importLine, packageLine, spaceChars


class HaxeGenerateImport( sublime_plugin.TextCommand ):

    start = None
    size = None
    cname = None

    def get_end( self, src, offset ) :
        end = len(src)
        while offset < end:
            c = src[offset]
            offset += 1
            if not wordChars.match(c): break
        return offset - 1

    def get_start( self, src, offset ) :
        foundWord = 0
        offset -= 1
        while offset > 0:
            c = src[offset]
            offset -= 1
            if foundWord == 0:
                if spaceChars.match(c): continue
                foundWord = 1
            if not wordChars.match(c): break

        return offset + 2

    def is_membername( self, token ) :
        return token[0] >= "Z" or token == token.upper()

    def is_module( self , token ) :
        return re.search("[\.^][A-Z]+", token);

    def get_classname( self, view, src ) :
        loc = view.sel()[0]
        end = max(loc.a, loc.b)
        self.size = loc.size()
        if self.size == 0:
            end = self.get_end(src, end)
            self.start = self.get_start(src, end)
            self.size = end - self.start
        else:
            self.start = end - self.size

        self.cname = view.substr(sublime.Region(self.start, end)).rpartition(".")
        #print(self.cname)
        while (not self.cname[0] == "" and self.is_membername(self.cname[2])):
            self.size -= 1 + len(self.cname[2])
            self.cname = self.cname[0].rpartition(".")

    def compact_classname( self, edit, view ) :
        view.replace(edit, sublime.Region(self.start, self.start+self.size), self.cname[2])
        view.sel().clear()
        loc = self.start + len(self.cname[2])
        view.sel().add(sublime.Region(loc, loc))

    def get_indent( self, src, index ) :

        if src[index] == "\n": return index + 1
        return index

    def insert_import( self, edit, view, src) :
        cname = "".join(self.cname)
        clow = cname.lower()
        last = None

        for imp in importLine.finditer(src):
            if clow < imp.group(2).lower():
                ins = "{0}import {1};\n".format(imp.group(1), cname)
                view.insert(edit, self.get_indent(src, imp.start(0)), ins)
                return
            last = imp

        if not last is None:
            ins = ";\n{0}import {1}".format(last.group(1), cname)
            view.insert(edit, last.end(2), ins)
        else:
            pkg = packageLine.search(src)
            if not pkg is None:
                ins = "\n\nimport {0};".format(cname)
                view.insert(edit, pkg.end(0), ins)
            else:
                ins = "import {0};\n\n".format(cname)
                view.insert(edit, 0, ins)

    def run( self , edit ) :
        view = self.view
        src = view.substr(sublime.Region(0, view.size()))
        self.get_classname(view, src)

        if self.cname[1] == "":
            sublime.status_message("Nothing to import")
            print("Nothing to import")
            return

        self.compact_classname(edit, view)

        if re.search("import\s+{0};".format("".join(self.cname)), src):
            sublime.status_message("Already imported")
            print("Already imported")
            return

        self.insert_import(edit, view, src)

