# -*- coding: utf-8 -*-

import sys
#sys.path.append("/usr/lib/python2.6/")
#sys.path.append("/usr/lib/python2.6/lib-dynload")

import sublime, sublime_plugin
import subprocess, time
import tempfile
import os, signal

#import xml.parsers.expat
import re
import codecs
import glob
import hashlib
import shutil
import functools

# Information about where the plugin is running from
plugin_file = __file__
plugin_filepath = os.path.realpath(plugin_file)
plugin_path = os.path.dirname(plugin_filepath)

try: # Python 3

    # Import the features module, including the haxelib and key commands etc
    from .features import *
    from .features.haxelib import *

    # Import the helper functions and regex helpers
    from .HaxeHelper import runcmd, show_quick_panel
    from .HaxeHelper import spaceChars, wordChars, importLine, packageLine, compilerOutput
    from .HaxeHelper import compactFunc, compactProp, libLine, classpathLine, typeDecl
    from .HaxeHelper import libFlag, skippable, inAnonymous, extractTag
    from .HaxeHelper import variables, functions, functionParams, paramDefault
    from .HaxeHelper import isType, comments, haxeVersion, haxeFileRegex, controlStruct

    # import YAML parser
    yaml_path = os.path.join( plugin_path , "PyYAML-3.10/lib3/" )
    sys.path.append( yaml_path )
    import yaml

except (ValueError): # Python 2

    # Import the features module, including the haxelib and key commands etc
    from features import *
    from features.haxelib import *

    # Import the helper functions and regex helpers
    from HaxeHelper import runcmd, show_quick_panel
    from HaxeHelper import spaceChars, wordChars, importLine, packageLine, compilerOutput
    from HaxeHelper import compactFunc, compactProp, libLine, classpathLine, typeDecl
    from HaxeHelper import libFlag, skippable, inAnonymous, extractTag
    from HaxeHelper import variables, functions, functionParams, paramDefault
    from HaxeHelper import isType, comments, haxeVersion, haxeFileRegex, controlStruct

    # import YAML parser
    yaml_path = os.path.join( plugin_path , "PyYAML-3.10/lib/" )
    sys.path.append( yaml_path )
    import yaml

# For running background tasks

from subprocess import Popen, PIPE
try:
  STARTUP_INFO = subprocess.STARTUPINFO()
  STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
  STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
    STARTUP_INFO = None

# For parsing xml

from xml.etree import ElementTree
from xml.etree.ElementTree import XMLTreeBuilder

try :
    from elementtree import SimpleXMLTreeBuilder # part of your codebase
    ElementTree.XMLTreeBuilder = SimpleXMLTreeBuilder.TreeBuilder
except ImportError as e:
    pass # ST3

try :
    stexec = __import__("exec")
    ExecCommand = stexec.ExecCommand
    AsyncProcess = stexec.AsyncProcess
except ImportError as e :
    import Default
    stexec = getattr( Default , "exec" )
    ExecCommand = stexec.ExecCommand
    AsyncProcess = stexec.AsyncProcess
    unicode = str #dirty...


class HaxeLib :

    available = {}
    basePath = None

    def __init__( self , name , dev , version ):
        self.name = name
        self.dev = dev
        self.version = version
        self.classes = None
        self.packages = None

        if self.dev :
            self.path = self.version
            self.version = "dev"
        else :
            self.path = os.path.join( HaxeLib.basePath , self.name , ",".join(self.version.split(".")) )

        #print(self.name + " => " + self.path)

    def extract_types( self ):

        if self.dev is True or ( self.classes is None and self.packages is None ):
            self.classes, self.packages = HaxeComplete.inst.extract_types( self.path )

        return self.classes, self.packages

    @staticmethod
    def get( name ) :
        if( name in HaxeLib.available.keys()):
            return HaxeLib.available[name]
        else :
            sublime.status_message( "Haxelib : "+ name +" project not installed" )
            return None

    @staticmethod
    def get_completions() :
        comps = []
        for l in HaxeLib.available :
            lib = HaxeLib.available[l]
            comps.append( ( lib.name + " [" + lib.version + "]" , lib.name ) )

        return comps

    @staticmethod
    def scan( view ) :

        settings = view.settings()
        haxelib_path = settings.get("haxelib_path" , "haxelib")

        hlout, hlerr = runcmd( [haxelib_path , "config" ] )
        HaxeLib.basePath = hlout.strip()

        HaxeLib.available = {}

        hlout, hlerr = runcmd( [haxelib_path , "list" ] )

        for l in hlout.split("\n") :
            found = libLine.match( l )
            if found is not None :
                name, dev, version = found.groups()
                lib = HaxeLib( name , dev is not None , version )

                HaxeLib.available[ name ] = lib


inst = None

documentationStore = {}

class HaxeBuild :

    #auto = None
    targets = ["js","cpp","swf","neko","php","java","cs","x","python"]
    nme_targets = [
        ("Flash - test","flash -debug","test"),
        ("Flash - build only","flash -debug","build"),
        ("Flash - release","flash","build"),
        ("HTML5 - test","html5 -debug","test"),
        ("HTML5 - build only","html5 -debug","build"),
        ("C++ - test","cpp -debug","test"),
        ("C++ - build only","cpp -debug","build"),
        ("C++ - release","cpp","build"),
        ("Linux - test","linux -debug","test"),
        ("Linux - build only","linux -debug","build"),
        ("Linux - release","linux","build"),
        ("Linux 64 - test","linux -64 -debug","test"),
        ("Linux 64 - build only","linux -64 -debug","build"),
        ("Linux 64 - release","linux -64","build"),
        ("iOS - test in iPhone simulator","ios -simulator -debug","test"),
        ("iOS - test in iPad simulator","ios -simulator -ipad -debug","test"),
        ("iOS - update XCode project","ios -debug","update"),
        ("iOS - release","ios","build"),
        ("Android - test","android -debug","test"),
        ("Android - build only","android -debug","build"),
        ("Android - release","android","build"),
        ("WebOS - test", "webos -debug","test"),
        ("WebOS - build only", "webos -debug","build"),
        ("WebOS - release", "webos","build"),
        ("Neko - test","neko -debug","test"),
        ("Neko - build only","neko -debug","build"),
        ("Neko 64 - test","neko -64 -debug","test"),
        ("Neko 64 - build only","neko -64 -debug","build"),
        ("BlackBerry - test","blackberry -debug","test"),
        ("BlackBerry - build only","blackberry -debug","build"),
        ("BlackBerry - release","blackberry","build"),
        ("Emscripten - test", "emscripten -debug","test"),
        ("Emscripten - build only", "emscripten -debug","build"),
        ("Emscripten - release", "emscripten","build"),
    ]
    nme_target = ("Flash - test","flash -debug","test")

    flambe_targets = [
        ("Flash - test", "run flash --debug" ),
        ("Flash - build only", "build flash --debug" ),
        ("HTML5 - test", "run html --debug" ),
        ("HTML5 - build only" , "build html --debug"),
        ("Android - test" , "run android --debug"),
        ("Android - build only" , "build android --debug")
    ]
    flambe_target = ("Flash - run", "run flash --debug")

    def __init__(self) :

        self.args = []
        self.main = None
        self.target = "js"
        self.output = "No output"
        self.hxml = None
        self.nmml = None
        self.yaml = None
        self.classpaths = []
        self.libs = []
        self.classes = None
        self.packages = None
        self.openfl = False
        self.lime = False
        self.cwd = None

    def __eq__(self,other) :
        return self.__dict__ == other.__dict__

    def __cmp__(self,other) :
        return self.__dict__ == other.__dict__

    def to_string(self) :
        out = os.path.basename(self.output)
        if self.openfl :
            return "{out} (openfl / {target})".format(self=self, out=out, target=HaxeBuild.nme_target[0]);
        elif self.lime :
            return "{out} (lime / {target})".format(self=self, out=out, target=HaxeBuild.nme_target[0]);
        elif self.nmml is not None:
            return "{out} (NME / {target})".format(self=self, out=out, target=HaxeBuild.nme_target[0]);
        elif self.yaml is not None:
            return "{out} (Flambe / {target})".format(self=self, out=out, target=HaxeBuild.flambe_target[0]);
        else:
            return "{main} ({target}:{out})".format(self=self, out=out, main=self.main, target=self.target);
        #return "{self.main} {self.target}:{out}".format(self=self, out=out);

    def make_hxml( self ) :
        outp = "# Autogenerated "+self.hxml+"\n\n"
        outp += "# "+self.to_string() + "\n"
        outp += "-main "+ self.main + "\n"
        outp += "-" + self.target + " " + self.output + "\n"
        for a in self.args :
            outp += " ".join( list(a) ) + "\n"

        d = os.path.dirname( self.hxml ) + "/"

        # relative paths
        outp = outp.replace( d , "")
        outp = outp.replace( "-cp "+os.path.dirname( self.hxml )+"\n", "")

        outp = outp.replace("--no-output" , "")
        outp = outp.replace("-v" , "")

        #outp = outp.replace("dummy" , self.main.lower() )

        #print( outp )
        return outp.strip()

    def is_temp( self ) :
        return not os.path.exists( self.hxml )

    def get_types( self ) :
        if self.classes is None or self.packs is None :
            classes = []
            packs = []

            cp = []
            cp.extend( self.classpaths )

            for lib in self.libs :
                if lib is not None :
                    cp.append( lib.path )

            #print("extract types :")
            #print(cp)
            cwd = self.cwd
            if cwd is None :
                cwd = os.path.dirname( self.hxml )

            for path in cp :
                c, p = HaxeComplete.inst.extract_types( os.path.join( cwd , path ) )
                classes.extend( c )
                packs.extend( p )

            classes.sort()
            packs.sort()

            self.classes = classes;
            self.packs = packs;

        return self.classes, self.packs



class HaxeDisplayCompletion( sublime_plugin.TextCommand ):

    def run( self , edit ) :
        #print("completing")
        view = self.view

        view.run_command( "auto_complete" , {
            "api_completions_only" : True,
            "disable_auto_insert" : True,
            "next_completion_if_showing" : False
        } )


class HaxeInsertCompletion( sublime_plugin.TextCommand ):

    def run( self , edit ) :
        #print("insert completion")
        view = self.view

        view.run_command( "insert_best_completion" , {
            "default" : ".",
            "exact" : True
        } )

class HaxeSaveAllAndBuild( sublime_plugin.TextCommand ):
    def run( self , edit ) :
        complete = HaxeComplete.inst
        view = self.view
        view.window().run_command("save_all")
        complete.run_build( view )

class HaxeRunBuild( sublime_plugin.TextCommand ):
    def run( self , edit ) :
        complete = HaxeComplete.inst
        view = self.view

        complete.run_build( view )


class HaxeSelectBuild( sublime_plugin.TextCommand ):
    def run( self , edit ) :
        complete = HaxeComplete.inst
        view = self.view

        complete.select_build( view )


class HaxeHint( sublime_plugin.TextCommand ):
    def run( self , edit , input = "" ) :
        complete = HaxeComplete.inst
        view = self.view

        if input == "(":
            sel = view.sel()
            emptySel = True
            for r in sel :
                if not r.empty() :
                    emptySel = False
                    break

            autoMatch = view.settings().get("auto_match_enabled",False)

            if autoMatch :
                if emptySel :
                    view.run_command( "insert_snippet" , {
                        "contents" : "($0)"
                    })
                else :
                    view.run_command( "insert_snippet" , {
                        "contents" : "(${0:$SELECTION})"
                    })
            else :
                view.run_command("insert" , {
                    "characters" : "("
                })
        else :
            view.run_command("insert" , {
                "characters" : input
            })

        autocomplete = view.settings().get("auto_complete",True)
        if not autocomplete :
            return

        for r in view.sel() :
            comps, hints = complete.get_haxe_completions( self.view , r.end() )

            fn_name = complete.get_current_fn_name(self.view, r.end())

            if view.settings().get("haxe_smart_snippets",False) :
                snippet = ""
                i = 1
                for h in hints :
                    var = str(i)+": " + h + " ";
                    var = var.replace("{","\{")
                    var = var.replace("}","\}")
                    if snippet == "":
                        snippet = var
                    else:
                        snippet = snippet + ",${" + var + "}"
                    i = i+1

                #print( hints )
                view.run_command( "insert_snippet" , {
                    "contents" : "${"+snippet+"}"
                })

            #view.set_status("haxe-status", status)
            #sublime.status_message(status)
            #if( len(comps) > 0 ) :
            #   view.run_command('auto_complete', {'disable_auto_insert': True})


class HaxeComplete( sublime_plugin.EventListener ):

    #folder = ""
    #buildArgs = []
    currentBuild = None
    selectingBuild = False
    builds = []
    errors = []

    currentCompletion = {
        "inp" : None,
        "outp" : None
    }

    classpathExclude = ['.git','_std']
    classpathDepth = 2

    stdPaths = []
    stdPackages = []
    #stdClasses = ["Void","Float","Int","UInt","Null","Bool","Dynamic","Iterator","Iterable","ArrayAccess"]
    stdClasses = []
    stdCompletes = []

    visibleCompletionList = [] # This will contain the list of visible completions, if there is one.

    panel = None
    serverMode = False
    serverProc = None
    serverPort = 6000

    compilerVersion = 2
    inited = False

    def __init__(self):
        #print("init haxecomplete")
        HaxeComplete.inst = self

    def __del__(self) :
        self.stop_server()


    def extract_types( self , path , depth = 0 ) :

        classes = []
        packs = []
        hasClasses = False

        #print(path)
        if not os.path.exists( path ) :
            print('Warning: path %s doesn´t exists.'%path);
            return classes, packs

        for fullpath in glob.glob( os.path.join(path,"*.hx") ) :
            f = os.path.basename(fullpath)

            cl, ext = os.path.splitext( f )

            if cl not in HaxeComplete.stdClasses:
                s = codecs.open( os.path.join( path , f ) , "r" , "utf-8" , "ignore" )
                src = comments.sub( "" , s.read() )

                clPack = "";
                for ps in packageLine.findall( src ) :
                    clPack = ps

                if clPack == "" :
                    packDepth = 0
                else:
                    packDepth = len(clPack.split("."))

                for decl in typeDecl.findall( src ):
                    t = decl[1]
                    params = decl[2]

                    if( packDepth == depth ) : # and t == cl or cl == "StdTypes"
                        if t == cl or cl == "StdTypes":
                            classes.append( t + params )
                        else:
                            classes.append( cl + "." + t + params )

                        hasClasses = True


        if hasClasses or depth <= self.classpathDepth :

            for f in os.listdir( path ) :

                cl, ext = os.path.splitext( f )

                if os.path.isdir( os.path.join( path , f ) ) and f not in self.classpathExclude :
                    packs.append( f )
                    subclasses,subpacks = self.extract_types( os.path.join( path , f ) , depth + 1 )
                    for cl in subclasses :
                        classes.append( f + "." + cl )


        classes.sort()
        packs.sort()
        return classes, packs


    def highlight_errors( self , view ) :
        fn = view.file_name()
        line_regions = []
        char_regions = []

        if fn is None :
            return

        for e in self.errors :
            if fn.endswith(e["file"]) :
                metric = e["metric"]
                l = e["line"]
                left = e["from"]
                right = e["to"]

                if metric.startswith("character") :
                    # retrieve character positions from utf-8 bytes offset reported by compiler
                    line = view.substr(view.line(view.text_point(l, 0))).encode("utf-8")
                    left = len(line[:left].decode("utf-8"))
                    right = len(line[:right].decode("utf-8"))

                    a = view.text_point(l,left)
                    b = view.text_point(l,right)
                    char_regions.append( sublime.Region(a,b))
                else :
                    a = view.text_point(left,0)
                    b = view.text_point(right,0)
                    line_regions.append( sublime.Region(a,b))

                view.set_status("haxe-status" , "Error: " + e["message"] )

        view.add_regions("haxe-error-lines" , line_regions , "invalid" , "light_x_bright" , sublime.DRAW_OUTLINED )
        view.add_regions("haxe-error" , char_regions , "invalid" , "light_x_bright" , sublime.DRAW_OUTLINED )

    def on_post_save( self , view ) :
        if view.score_selector(0,'source.hxml') > 0:
            self.clear_build(view)

    def on_activated( self , view ) :
        return self.on_open_file( view )

    def on_load( self, view ) :
        return self.on_open_file( view )

    def on_open_file( self , view ) :
        if view.is_loading() :
            return;

        if view.score_selector(0,'source.haxe.2') > 0 :
            HaxeCreateType.on_activated( view )
        elif view.score_selector(0,'source.hxml,source.erazor,source.nmml') == 0:
            return

        self.init_plugin( view )
        # HaxeProjects.determine_type()
        
        self.extract_build_args( view )
        self.get_build( view )
        self.generate_build( view )
        self.highlight_errors( view )

    def on_pre_save( self , view ) :
        if view.score_selector(0,'source.haxe.2') == 0 :
            return []

        fn = view.file_name()

        if fn is not None :
            path = os.path.dirname( fn )
            if not os.path.isdir( path ) :
                os.makedirs( path )

    def __on_modified( self , view ):
        win = sublime.active_window()
        if win is None :
            return None

        isOk = ( win.active_view().buffer_id() == view.buffer_id() )
        if not isOk :
            return None

        sel = view.sel()
        caret = 0
        for s in sel :
            caret = s.a

        if caret == 0 :
            return None

        if view.score_selector(caret,"source.haxe") == 0 or view.score_selector(caret,"string,comment,keyword.control.directive.conditional.haxe.2") > 0 :
            return None

        src = view.substr(sublime.Region(0, view.size()))
        ch = src[caret-1]
        #print(ch)
        if ch not in ".(:, " :
            view.run_command("haxe_display_completion")
        #else :
        #   view.run_command("haxe_insert_completion")


    def generate_build(self, view) :

        fn = view.file_name()

        if fn is not None and self.currentBuild is not None and fn == self.currentBuild.hxml and view.size() == 0 :
            view.run_command("insert_snippet",{
                "contents" : self.currentBuild.make_hxml()
            })


    def select_build( self , view ) :
        scopes = view.scope_name(view.sel()[0].end()).split()

        if 'source.hxml' in scopes:
            view.run_command("save")

        self.extract_build_args( view , True )


    def find_nmml( self, folder ) :
        nmmls = glob.glob( os.path.join( folder , "*.nmml" ) )
        nmmls += glob.glob( os.path.join( folder , "*.xml" ) )
        nmmls += glob.glob( os.path.join( folder , "*.lime" ) )

        for build in nmmls:
            # yeah...
            if not os.path.exists( build ) :
                continue

            currentBuild = HaxeBuild()
            currentBuild.hxml = build
            currentBuild.nmml = build
            currentBuild.openfl = build.endswith("xml")
            currentBuild.lime = build.endswith("lime")
            buildPath = os.path.dirname(build)

            # TODO delegate compiler options extractions to NME 3.2:
            # runcmd("nme diplay project.nmml nme_target")

            outp = "NME"
            f = codecs.open( build , "r+", "utf-8" , "ignore" )
            while 1:
                l = f.readline()
                if not l :
                    break;
                m = extractTag.search(l)
                if not m is None:
                    #print(m.groups())
                    tag = m.group(1)
                    name = m.group(3)
                    if (tag == "app"):
                        currentBuild.main = name
                        mFile = re.search("\\b(file|title)=\"([a-z0-9_-]+)\"", l, re.I)
                        if not mFile is None:
                            outp = mFile.group(2)
                    elif (tag == "haxelib"):
                        currentBuild.libs.append( HaxeLib.get( name ) )
                        currentBuild.args.append( ("-lib" , name) )
                    elif (tag == "haxedef"):
                        currentBuild.args.append( ("-D", name) )
                    elif (tag == "classpath" or tag == "source"):
                        currentBuild.classpaths.append( os.path.join( buildPath , name ) )
                        currentBuild.args.append( ("-cp" , os.path.join( buildPath , name ) ) )
                else: # NME 3.2
                    mPath = re.search("\\bpath=\"([a-z0-9_-]+)\"", l, re.I)
                    if not mPath is None:
                        #print(mPath.groups())
                        path = mPath.group(1)
                        currentBuild.classpaths.append( os.path.join( buildPath , path ) )
                        currentBuild.args.append( ("-cp" , os.path.join( buildPath , path ) ) )

            outp = os.path.join( folder , outp )

            if currentBuild.openfl or currentBuild.lime :
                if self.compilerVersion >= 3 :
                    currentBuild.target = "swf"
                else :
                    currentBuild.target = "swf9"

            else :
                currentBuild.target = "cpp"
                currentBuild.args.append( ("--remap", "flash:nme") )
            #currentBuild.args.append( ("-cpp", outp) )
            currentBuild.output = outp

            if currentBuild.main is not None :
                self.add_build( currentBuild )

    def find_yaml( self, folder ) :
        yamls = glob.glob( os.path.join( folder , "flambe.yaml") )

        for build in yamls :

            # yeah...
            if not os.path.exists( build ) :
                continue

            currentBuild = HaxeBuild()
            currentBuild.hxml = build
            currentBuild.yaml = build
            buildPath = os.path.dirname( build )

            yaml_data = yaml.load( codecs.open( build , "r+" , "utf-8" , "ignore" ) )

            currentBuild.main = yaml_data['main']
            currentBuild.args.append( ("-lib","flambe") )

            flambe_lib = HaxeLib.get("flambe")
            currentBuild.libs.append( flambe_lib )

            srcDir = os.path.join( buildPath , "src" )
            currentBuild.args.append( ("-cp" , srcDir ) )
            currentBuild.classpaths.append( srcDir )

            self.add_build( currentBuild )


    def read_hxml( self, build ) :
        #print("Reading build " + build );

        buildPath = os.path.dirname(build);

        spl = build.split("@")
        if( len(spl) == 2 ) :
            buildPath = spl[0]
            build = os.path.join( spl[0] , spl[1] )

        if not os.path.exists( build ) :
            return None

        #print( buildPath, build )
        
        currentBuild = HaxeBuild()
        currentBuild.hxml = build
        currentBuild.cwd = buildPath

        #print( currentBuild )
        
        f = codecs.open( build , "r+" , "utf-8" , "ignore" )

        while 1:
            l = f.readline()
            if not l :
                break;
            if l.startswith("--next") :
                self.add_build( currentBuild )
                currentBuild = HaxeBuild()
                currentBuild.hxml = build
                currentBuild.cwd = buildPath

            l = l.strip()

            if l.startswith("-main") :
                spl = l.split(" ")
                if len( spl ) == 2 :
                    currentBuild.main = spl[1]
                else :
                    sublime.status_message( "Invalid build.hxml : no Main class" )

            if l.startswith("-lib") :
                spl = l.split(" ")
                if len( spl ) == 2 :
                    lib = HaxeLib.get( spl[1] )
                    currentBuild.libs.append( lib )
                else :
                    sublime.status_message( "Invalid build.hxml : lib not found" )

            if l.startswith("-cmd") :
                spl = l.split(" ")
                currentBuild.args.append( ( "-cmd" , " ".join(spl[1:]) ) )

            #if l.startswith("--connect") and HaxeComplete.inst.serverMode :
            #   currentBuild.args.append( ( "--connect" , str(self.serverPort) ))

            for flag in [ "lib" , "D" , "swf-version" , "swf-header", "debug" , "-no-traces" , "-flash-use-stage" , "-gen-hx-classes" , "-remap" , "-no-inline" , "-no-opt" , "-php-prefix" , "-js-namespace" , "-interp" , "-macro" , "-dead-code-elimination" , "-remap" , "-php-front" , "-php-lib", "dce" , "-js-modern" , "swf-lib" ] :
                if l.startswith( "-"+flag ) :
                    currentBuild.args.append( tuple(l.split(" ") ) )

                    break

            for flag in [ "resource" , "xml" , "java-lib" , "net-lib" ] :
                if l.startswith( "-"+flag ) :
                    spl = l.split(" ")
                    outp = os.path.join( buildPath , " ".join(spl[1:]) )
                    currentBuild.args.append( ("-"+flag, outp) )

                    break

            #print(HaxeBuild.targets)
            for flag in HaxeBuild.targets :
                if l.startswith( "-" + flag + " " ) :

                    spl = l.split(" ")
                    #outp = os.path.join( folder , " ".join(spl[1:]) )
                    outp = " ".join(spl[1:])
                    #currentBuild.args.append( ("-"+flag, outp) )

                    currentBuild.target = flag
                    currentBuild.output = outp
                    break

            if l.startswith("-cp "):
                cp = l.split(" ")
                #view.set_status( "haxe-status" , "Building..." )
                cp.pop(0)
                classpath = " ".join( cp )
                absClasspath = classpath#os.path.join( buildPath , classpath )
                currentBuild.classpaths.append( absClasspath )
                currentBuild.args.append( ("-cp" , absClasspath ) )

        if len(currentBuild.classpaths) == 0:
            currentBuild.classpaths.append( buildPath )
            currentBuild.args.append( ("-cp" , buildPath ) )


        if currentBuild.main is None:
            currentBuild.main = '[No Main]'

        return currentBuild

    def add_build( self , build ) :
        if build not in self.builds :
            self.builds.append( build )

    def find_hxml( self, folder ) :
        hxmls = glob.glob( os.path.join( folder , "*.hxml" ) )

        for build in hxmls:
            currentBuild = self.read_hxml( build );
            if currentBuild is not None :
                self.add_build( currentBuild )


    def find_build_file( self , folder ) :
        self.find_hxml(folder)
        self.find_nmml(folder)
        self.find_yaml(folder)

    def extract_build_args( self , view , forcePanel = False ) :

        # extract build files from project
        build_files = view.settings().get('haxe_builds') 
        if build_files is not None :
            for b in build_files :
                if( int(sublime.version()) > 3000 ) : 
                    # files are relative to project file name
                    proj = view.window().project_file_name()
                    if( proj is not None ) :
                        proj_path = os.path.dirname( proj )
                        b = os.path.join( proj_path , b )

                currentBuild = self.read_hxml( b );
                if currentBuild is not None :
                    self.add_build( currentBuild )

        fn = view.file_name()
        settings = view.settings()
        win = view.window()
        folder = None
        file_folder = None
        # folder containing the file, opened in window
        project_folder = None
        win_folders = []
        folders = []

        if fn is not None :
            file_folder = folder = os.path.dirname(fn)

        # find window folder containing the file
        if win is not None :
            win_folders = win.folders()
            for f in win_folders:
                if f + os.sep in fn :
                    project_folder = folder = f
                    

        crawl_folders = []

        # go up all folders from file to project or root
        if file_folder is not None :
            f = file_folder 
            prev = None
            while prev != f and ( project_folder is None or project_folder in f ):
                crawl_folders.append( f )
                prev = f
                f = os.path.split( f )[0]
         
        # crawl other window folders
        for f in win_folders :
            if f not in crawl_folders :
                crawl_folders.append( f )

        for f in crawl_folders :
            self.find_build_file( f )

        if len(self.builds) == 1:
            if forcePanel :
                sublime.status_message("There is only one build")

            # will open the build file
            #if forcePanel :
            #   b = self.builds[0]
            #   f = b.hxml
            #   v = view.window().open_file(f,sublime.TRANSIENT)

            self.set_current_build( view , int(0), forcePanel )

        elif len(self.builds) == 0 and forcePanel :
            sublime.status_message("No hxml or nmml file found")

            f = os.path.join(folder,"build.hxml")

            self.currentBuild = None
            self.get_build(view)
            self.currentBuild.hxml = f

            #for whatever reason generate_build doesn't work without transient
            v = view.window().open_file(f,sublime.TRANSIENT)

            self.set_current_build( view , int(0), forcePanel )

        elif len(self.builds) > 1 and forcePanel :
            buildsView = []
            for b in self.builds :
                #for a in b.args :
                #   v.append( " ".join(a) )
                buildsView.append( [b.to_string(), os.path.basename( b.hxml ) ] )

            self.selectingBuild = True
            sublime.status_message("Please select your build")
            show_quick_panel( view.window() , buildsView , lambda i : self.set_current_build(view, int(i), forcePanel) , sublime.MONOSPACE_FONT )

        elif settings.has("haxe-build-id"):
            self.set_current_build( view , int(settings.get("haxe-build-id")), forcePanel )

        else:
            self.set_current_build( view , int(0), forcePanel )


    def set_current_build( self , view , id , forcePanel ) :

        if id < 0 or id >= len(self.builds) :
            id = 0

        view.settings().set( "haxe-build-id" , id )

        if len(self.builds) > 0 :
            self.currentBuild = self.builds[id]
            view.set_status( "haxe-build" , self.currentBuild.to_string() )
        else:
            #self.currentBuild = None
            view.set_status( "haxe-build" , "No build" )

        self.selectingBuild = False

        if forcePanel and self.currentBuild is not None: # choose NME target

            if self.currentBuild.nmml is not None:
                sublime.status_message("Please select a NME target")
                nme_targets = []
                for t in HaxeBuild.nme_targets :
                    nme_targets.append( t[0] )

                show_quick_panel( view.window() , nme_targets, lambda i : self.select_nme_target(i, view))

            elif self.currentBuild.yaml is not None:
                sublime.status_message("Please select a Flambe target")
                flambe_targets = []
                for t in HaxeBuild.flambe_targets :
                    flambe_targets.append( t[0] )

                show_quick_panel( view.window() , flambe_targets, lambda i : self.select_flambe_target(i, view))



    def select_nme_target( self, i, view ):
        target = HaxeBuild.nme_targets[i]

        if self.currentBuild.nmml is not None:
            HaxeBuild.nme_target = target
            view.set_status( "haxe-build" , self.currentBuild.to_string() )

    def select_flambe_target( self , i , view ):
        target = HaxeBuild.flambe_targets[i]
        if self.currentBuild.yaml is not None:
            HaxeBuild.flambe_target = target
            view.set_status( "haxe-build" , self.currentBuild.to_string() )


    def run_build( self , view ) :

        err, comps, status = self.run_haxe( view )
        view.set_status( "haxe-status" , status )


    def clear_output_panel(self, view) :
        win = view.window()

        self.panel = win.get_output_panel("haxe")

    def panel_output( self , view , text , scope = None ) :
        win = view.window()
        if self.panel is None :
            self.panel = win.get_output_panel("haxe")

        panel = self.panel

        text = datetime.now().strftime("%H:%M:%S") + " " + text;

        edit = panel.begin_edit()
        region = sublime.Region(panel.size(),panel.size() + len(text))
        panel.insert(edit, panel.size(), text + "\n")
        panel.end_edit( edit )

        if scope is not None :
            icon = "dot"
            key = "haxe-" + scope
            regions = panel.get_regions( key );
            regions.append(region)
            panel.add_regions( key , regions , scope , icon )
        #print( err )
        win.run_command("show_panel",{"panel":"output.haxe"})

        return self.panel

    def get_toplevel_completion( self , src , src_dir , build ) :
        cl = []
        comps = [("trace","trace"),("this","this"),("super","super"),("else","else")]

        src = comments.sub("",src)

        localTypes = typeDecl.findall( src )
        for t in localTypes :
            if t[1] not in cl:
                cl.append( t[1] )

        packageClasses, subPacks = self.extract_types( src_dir )
        for c in packageClasses :
            if c not in cl:
                cl.append( c )

        imports = importLine.findall( src )
        imported = []
        for i in imports :
            imp = i[1]
            imported.append(imp)
            #dot = imp.rfind(".")+1
            #clname = imp[dot:]
            #cl.append( imp )
            #print( i )

        #print cl
        buildClasses , buildPacks = build.get_types()

        tarPkg = None
        targetPackages = ["flash","flash9","flash8","neko","js","php","cpp","cs","java","nme"]

        compilerVersion = HaxeComplete.inst.compilerVersion

        if build.target is not None :
            tarPkg = build.target
            if tarPkg == "x":
                tarPkg = "neko"

            # haxe 2
            if tarPkg == "swf9" :
                tarPkg = "flash"

            # haxe 3
            if tarPkg == "swf8" :
                tarPkg = "flash8"

            if tarPkg == "swf" :
                if compilerVersion >= 3 :
                    tarPkg = "flash"
                else :
                    tarPkg = "flash8"

        if not build.openfl and not build.lime and build.nmml is not None or HaxeLib.get("nme") in build.libs :
            tarPkg = "nme"
            targetPackages.extend( ["jeash","neash","browser","native"] )

        #print( "tarpkg : " + tarPkg );
        #for c in HaxeComplete.stdClasses :
        #   p = c.split(".")[0]
        #   if tarPkg is None or (p not in targetPackages) or (p == tarPkg) :
        #       cl.append(c)

        cl.extend( imported )
        cl.extend( HaxeComplete.stdClasses )
        cl.extend( buildClasses )
        cl = list(set(cl)) # unique
        cl.sort();

        packs = []
        stdPackages = []
        #print("target : "+build.target)
        for p in HaxeComplete.stdPackages :
            #print(p)
            #if p == "flash9" or p == "flash8" :
            #   p = "flash"
            if tarPkg is None or (p not in targetPackages) or (p == tarPkg) :
                stdPackages.append(p)

        packs.extend( stdPackages )
        packs.extend( buildPacks )
        packs.sort()

        for v in variables.findall(src) :
            comps.append(( v + "\tvar" , v ))

        for f in functions.findall(src) :
            if f not in ["new"] :
                comps.append(( f + "\tfunction" , f ))


        #TODO can we restrict this to local scope ?
        for paramsText in functionParams.findall(src) :
            cleanedParamsText = re.sub(paramDefault,"",paramsText)
            paramsList = cleanedParamsText.split(",")
            for param in paramsList:
                a = param.strip();
                if a.startswith("?"):
                    a = a[1:]

                idx = a.find(":")
                if idx > -1:
                    a = a[0:idx]

                idx = a.find("=")
                if idx > -1:
                    a = a[0:idx]

                a = a.strip()
                cm = (a + "\tvar", a)
                if cm not in comps:
                    comps.append( cm )

        for c in cl :
            #print(c)
            spl = c.split(".")
            #if spl[0] == "flash9" or spl[0] == "flash8" :
            #   spl[0] = "flash"

            top = spl[0]
            #print(spl)

            clname = spl.pop()
            pack = ".".join(spl)
            display = clname

            # remove parameters
            clname = clname.split('<')[0]

            #if pack in imported:
            #   pack = ""

            if pack != "" :
                display += "\t" + pack
            else :
                display += "\tclass"

            spl.append(clname)

            if pack in imported or c in imported :
                cm = ( display , clname )
            else :
                cm = ( display , ".".join(spl) )

            if cm not in comps and tarPkg is None or (top not in targetPackages) or (top == tarPkg) : #( build.target is None or (top not in HaxeBuild.targets) or (top == build.target) ) :
                comps.append( cm )

        for p in packs :
            cm = (p + "\tpackage",p)
            if cm not in comps :
                comps.append(cm)


        return comps

    def clear_build( self , view ) :
        self.currentBuild = None
        self.currentCompletion = {
            "inp" : None,
            "outp" : None
        }

    def get_build( self , view ) :

        fn = view.file_name()
        win = view.window()

        if win is None or fn is None :
            return

        if fn is not None and self.currentBuild is None and view.score_selector(0,"source.haxe.2") > 0 :

            src_dir = os.path.dirname( fn )
            src = view.substr(sublime.Region(0, view.size()))

            build = HaxeBuild()
            #build.target = "js"

            folder = os.path.dirname(fn)
            folders = win.folders()
            for f in folders:
                if f in fn :
                    folder = f

            pack = []
            for ps in packageLine.findall( src ) :
                if ps == "":
                    continue

                pack = ps.split(".")
                for p in reversed(pack) :
                    spl = os.path.split( src_dir )
                    if( spl[1] == p ) :
                        src_dir = spl[0]

            cl = os.path.basename(fn)

            #if int(sublime.version() < 3000) :
            #    cl = cl.encode('ascii','ignore')

            cl = cl[0:cl.rfind(".")]

            main = pack[0:]
            main.append( cl )
            build.main = ".".join( main )

            build.output = os.path.join(folder,build.main.lower() + ".js")

            build.args.append( ("-cp" , src_dir) )
            build.args.append( ("--no-output",) )
            #build.args.append( ("-main" , build.main ) )

            #build.args.append( ("-js" , build.output ) )
            #build.args.append( ("--no-output" , "-v" ) )

            build.hxml = os.path.join( src_dir , "build.hxml")

            #build.hxml = os.path.join( src_dir , "build.hxml")
            self.currentBuild = build

        if self.currentBuild is not None :
            view.set_status( "haxe-build" , self.currentBuild.to_string() )

        return self.currentBuild


    def run_nme( self, view, build ) :

        settings = view.settings()
        haxelib_path = settings.get("haxelib_path" , "haxelib")

        if build.openfl :
            cmd = [haxelib_path,"run","openfl"]
        elif build.lime :
            cmd = [haxelib_path,"run","lime"]
        else :
            cmd = [haxelib_path,"run","nme"]

        cmd += [ HaxeBuild.nme_target[2], os.path.basename(build.nmml) ]
        target = HaxeBuild.nme_target[1].split(" ")
        cmd.extend(target)

        view.window().run_command("exec", {
            "cmd": cmd,
            "working_dir": os.path.dirname(build.nmml),
            "file_regex": haxeFileRegex #"^([^:]*):([0-9]+): characters [0-9]+-([0-9]+) :.*$"
        })
        return ("" , [], "" )

    def run_flambe( self , view , build ):
        cmd = [ "flambe.cmd" if os.name == "nt" else "flambe" ]

        cmd += HaxeBuild.flambe_target[1].split(" ")

        view.window().run_command("exec", {
            "cmd": cmd,
            "working_dir": os.path.dirname(build.yaml),
            "file_regex": haxeFileRegex #"^([^:]*):([0-9]+): characters [0-9]+-([0-9]+) :.*$"
        })
        return ("" , [], "" )

    def init_plugin( self , view ) :

        if self.inited :
            return

        self.inited = True

        HaxeLib.scan( view )

        settings = view.settings()
        haxepath = settings.get("haxe_path","haxe")

        out, err = runcmd( [haxepath, "-main", "Nothing", "-v", "--no-output"] )

        _, versionOut = runcmd([haxepath, "-v"])

        m = classpathLine.match(out)
        if m is not None :
            HaxeComplete.stdPaths = set(m.group(1).split(";")) - set([".","./"])

        for p in HaxeComplete.stdPaths :
            #print("std path : "+p)
            if len(p) > 1 and os.path.exists(p) and os.path.isdir(p):
                classes, packs = self.extract_types( p )
                HaxeComplete.stdClasses.extend( classes )
                HaxeComplete.stdPackages.extend( packs )

        ver = re.search(haxeVersion , versionOut)

        if ver is not None :
            self.compilerVersion = float(ver.group(2))

            if self.compilerVersion >= 3 :
                HaxeBuild.targets.append("swf8")
            else :
                HaxeBuild.targets.append("swf9")

            self.serverMode = float(ver.group(2)) * 100 >= 209

        buildServerMode = settings.get('haxe_build_server_mode', True)
        completionServerMode = settings.get('haxe_completion_server_mode',True)

        self.serverMode = self.serverMode and (buildServerMode or completionServerMode)

        self.start_server( view )

    def start_server( self , view = None ) :
        #self.stop_server()
        if self.serverMode and self.serverProc is None :
            try:
                haxepath = "haxe"

                env = os.environ.copy()

                merged_env = env.copy()

                if view is not None :
                    user_env = view.settings().get('build_env')
                    if user_env:
                        merged_env.update(user_env)


                if view is not None :
                    settings = view.settings()
                    if settings.has("haxe_library_path") :
                        env["HAXE_LIBRARY_PATH"] = settings.get("haxe_library_path",".")
                        env["HAXE_STD_PATH"] = settings.get("haxe_library_path",".")

                    haxepath = settings.get("haxe_path" , "haxe")

                self.serverPort+=1
                cmd = [haxepath , "--wait" , str(self.serverPort) ]
                print("Starting Haxe server on port "+str(self.serverPort))

                #self.serverProc = Popen(cmd, env=env , startupinfo=STARTUP_INFO)
                self.serverProc = Popen(cmd, env = merged_env, startupinfo=STARTUP_INFO)
                self.serverProc.poll()

            except(OSError, ValueError) as e:
                err = u'Error starting Haxe server %s: %s' % (" ".join(cmd), e)
                sublime.error_message(err)

    def stop_server( self ) :

        if self.serverProc is not None :
            self.serverProc.terminate()
            self.serverProc.kill()
            self.serverProc.wait()

        self.serverProc = None
        del self.serverProc


    def run_haxe( self, view , display = None) :

        self.init_plugin( view )

        build = self.get_build( view )
        settings = view.settings()

        autocomplete = display is not None

        if not autocomplete and build is not None and build.nmml is not None :
            return self.run_nme( view, build )

        if not autocomplete and build is not None and build.yaml is not None :
            return self.run_flambe( view , build )

        fn = view.file_name()

        if fn is None :
            return

        comps = []
        self.errors = []
        args = []


        cwd = build.cwd 
        if cwd is None :
            cwd = os.path.dirname( build.hxml )

        args.extend( build.args )

        buildServerMode = settings.get('haxe_build_server_mode', True)
        completionServerMode = settings.get('haxe_completion_server_mode',True)

        if self.serverMode and ( ( completionServerMode and autocomplete ) or ( buildServerMode and not autocomplete ) ) :
            args.append(("--connect" , str(HaxeComplete.inst.serverPort)))
            args.append(("--cwd" , cwd ))
        #args.append( ("--times" , "-v" ) )
        if not autocomplete :
            args.append( ("-main" , build.main ) )
            args.append( ("-"+build.target , build.output ) )
            #args.append( ("--times" , "-v" ) )
        else:

            display_arg = display["filename"] + "@" + str( display["offset"] )
            if display["mode"] is not None :
                display_arg += "@" + display["mode"]

            args.append( ("-D", "st_display" ) )
            args.append( ("--display", display_arg ) )
            args.append( ("--no-output",) )
            args.append( ("-"+build.target , build.output ) )
            #args.append( ("-cp" , plugin_path ) )
            #args.append( ("--macro" , "SourceTools.complete()") )


        haxepath = settings.get( 'haxe_path' , 'haxe' )
        cmd = [haxepath]
        for a in args :
            cmd.extend( list(a) )

        #
        # TODO: replace runcmd with run_command('exec') when possible (haxelib, maybe build)
        #
        if not autocomplete :
            encoded_cmd = []
            for c in cmd :
                #if isinstance( c , unicode) :
                #   encoded_cmd.append( c.encode('utf-8') )
                #else :
                    encoded_cmd.append( c )

            #print(encoded_cmd)

            env = {}
            if settings.has("haxe_library_path") :
                env["HAXE_LIBRARY_PATH"] = settings.get("haxe_library_path",".")
                env["HAXE_STD_PATH"] = settings.get("haxe_library_path",".")

            view.window().run_command("haxe_exec", {
                "cmd": encoded_cmd,
                "working_dir": cwd,
                "file_regex": haxeFileRegex,
                "env" : env
            })
            return ("" , [], "" )


        #print(" ".join(cmd))
        res, err = runcmd( cmd, "" )

        if not autocomplete :
            self.panel_output( view , " ".join(cmd) )

        status = ""

        if (not autocomplete) and (build.hxml is None) :
            #status = "Please create an hxml file"
            self.extract_build_args( view , True )
        elif not autocomplete :
            # default message = build success
            status = "Build success"


        #print(err)
        hints = []
        msg = ""
        tree = None
        pos = None

        commas = 0
        if display is not None and display["commas"] is not None :
            commas = display["commas"]

        if int(sublime.version()) >= 3000 :
            x = "<root>"+err+"</root>"
        else :
            x = "<root>"+err.encode("ASCII",'ignore')+"</root>"

        try :
            tree = ElementTree.XML(x);

        except Exception as e :
            print(e)
            print("invalid xml")

        if tree is not None :
            for i in tree.getiterator("type") :
                hint = i.text.strip()
                spl = hint.split(" -> ")

                types = [];
                pars = 0;
                currentType = [];

                for t in spl :
                    currentType.append( t )
                    if "(" in t or "{" in t :
                        pars += 1
                    if ")" in t or "}" in t :
                        pars -= 1

                    if pars == 0 :
                        types.append( " -> ".join( currentType ) )
                        currentType = []

                ret = types.pop()
                msg = "";

                if commas >= len(types) :
                    if commas == 0 or hint == "Dynamic" :
                        msg = hint + ": No autocompletion available"
                        #view.window().run_command("hide_auto_complete")
                        #comps.append((")",""))
                    else :
                        msg =  "Too many arguments."
                else :
                    hints = types[commas:]
                    #print(hints)
                    if hints == ["Void"] :
                        hints = []
                        msg = "Void"
                    else :
                        msg = ", ".join(hints)

            status = msg

            # This will attempt to get the full name of what we're trying to complete.
            # E.g. we type in self.blarg.herp(), this will get "self.blarg".
            fn_name = self.get_current_fn_name(view, view.sel()[0].end())

            pos = tree.findtext("pos")
            li = tree.find("list")

            if li is not None :

                pos = li.findtext("pos")

                for i in li.getiterator("i"):
                    name = i.get("n")
                    sig = i.find("t").text
                    doc = i.find("d").text

                    #if doc is None: doc = "No documentation found."
                    insert = name
                    hint = name
                    doc_data = { 'hint' : name , 'doc' : doc }
                    documentationStore[fn_name + "." + name] = doc_data

                    if sig is not None :

                        types = sig.split(" -> ")
                        ret = types.pop()

                        if( len(types) > 0 ) :
                            #cm = name + "("
                            cm = name
                            if len(types) == 1 and types[0] == "Void" :
                                types = []
                                #cm += ")"
                                hint = name + "()\t"+ ret
                                insert = cm
                                doc_data['hint'] = hint
                            else:
                                hint = name + "( " + " , ".join( types ) + " )\t" + ret
                                doc_data['hint'] = hint # update before compacting

                                if len(hint) > 40: # compact arguments
                                    hint = compactFunc.sub("(...)", hint);
                                insert = cm
                        else :
                            hint = name + "\t" + ret
                            doc_data['hint'] = hint
                    else :
                        if re.match("^[A-Z]",name ) :
                            hint = name + "\tclass"
                        else :
                            hint = name + "\tpackage"
                        doc_data['hint'] = hint

                    #if doc is not None :
                    #   hint += "\t" + doc
                    #   print(doc)

                    if len(hint) > 40: # compact return type
                        m = compactProp.search(hint)
                        if not m is None:
                            hint = compactProp.sub(": " + m.group(1), hint)

                    comps.append( ( hint, insert ) )

        if len(hints) == 0 and len(comps) == 0:
            err = re.sub( u"\(display(.*)\)" ,"",err)

            lines = err.split("\n")
            l = lines[0].strip()

            if len(l) > 0 and status == "":
                if l == "<list>" or l == "<type>":
                    status = "No autocompletion available"
                elif not re.match( haxeFileRegex , l ):
                    status = l
                else :
                    status = ""

            self.errors = self.extract_errors( err, cwd )

        if display is not None and display["mode"] == "position":
            return pos
        else:
            return ( err, comps, status , hints )

    def extract_errors( self , str , cwd ):
        errors = []

        for infos in compilerOutput.findall(str) :
            infos = list(infos)
            #print(infos)
            f = infos.pop(0)

            if not os.path.isabs(f):
                f = os.path.normpath(os.path.join(cwd, f))

            l = int( infos.pop(0) )-1

            metric = infos.pop(0)

            left = int( infos.pop(0) )
            right = infos.pop(0)
            if right != "" :
                right = int( right )
            else :
                right = left+1

            m = infos.pop(0)

            if metric.startswith("line") :
                left -= 1

            errors.append({
                "file" : f,
                "line" : l,
                "metric" : metric,
                "from" : left,
                "to" : right,
                "message" : m
            })

        #print(errors)
        if len(errors) > 0:
            sublime.status_message(errors[0]["message"])

        return errors


    def on_query_completions(self, view, prefix, locations):
        #print("complete")
        pos = locations[0]
        scopes = view.scope_name(pos).split()
        #print(scopes)
        offset = pos - len(prefix)
        comps = []
        if offset == 0 :
            return comps

        for s in scopes :
            if s == "keyword.control.directive.conditional.haxe.2" or s.split(".")[0] in ["string","comment"] :
                return comps

        if 'source.hxml' in scopes:
            comps = self.get_hxml_completions( view , offset )

        if 'source.haxe.2' in scopes :
            if view.file_name().endswith(".hxsl") :
                comps = self.get_hxsl_completions( view , offset )
            else :
                comps,hints = self.get_haxe_completions( view , offset )

        return comps


    def save_temp_file( self , view ) :

        fn = view.file_name()

        tdir = os.path.dirname(fn)
        temp = os.path.join( tdir , os.path.basename( fn ) + ".tmp" )

        src = view.substr(sublime.Region(0, view.size()))

        if not os.path.exists( tdir ):
            os.mkdir( tdir )

        if os.path.exists( fn ):
            # copy saved file to temp for future restoring
            shutil.copy2( fn , temp )

        # write current source to file
        f = codecs.open( fn , "wb" , "utf-8" , "ignore" )
        f.write( src )
        f.close()

        return temp

    def clear_temp_file( self , view , temp ) :

        fn = view.file_name()

        if os.path.exists( temp ) :
            shutil.copy2( temp , fn )
            os.remove( temp )
        else:
            # fn didn't exist in the first place, so we remove it
            os.remove( fn )

    def get_current_fn_name(self, view, offset):
        nonfunction_chars = "\t -=+{}[];':\"?/><,!@#$%^&*()"
        source = view.substr(sublime.Region(0, view.size()))
        source = source[:offset-1]

        closest_nonfunction_char_idx = -1

        for ch in nonfunction_chars:
            idx = source.rfind(ch)
            if idx > closest_nonfunction_char_idx:
                closest_nonfunction_char_idx = idx

        fn_name = source[closest_nonfunction_char_idx + 1:]
        return fn_name


    def get_haxe_completions( self , view , offset ):

        src = view.substr(sublime.Region(0, view.size()))
        fn = view.file_name()
        src_dir = os.path.dirname(fn)

        if fn is None :
            return

        hints = []
        show_hints = True

        #find actual autocompletable char.
        toplevelComplete = False
        userOffset = completeOffset = offset
        prev = src[offset-1]
        commas = 0
        comps = []
        #print("prev : "+prev)
        if prev not in "(." :
            fragment = view.substr(sublime.Region(0,offset))
            prevDot = fragment.rfind(".")
            prevPar = fragment.rfind("(")
            prevComa = fragment.rfind(",")
            prevColon = fragment.rfind(":")
            prevBrace = fragment.rfind("{")
            prevSymbol = max(prevDot,prevPar,prevComa,prevBrace,prevColon)

            if prevSymbol == prevComa:
                closedPars = 0
                closedBrackets = 0

                for i in range( prevComa , 0 , -1 ) :
                    c = src[i]

                    if c == ")" :
                        closedPars += 1
                    elif c == "(" :
                        if closedPars < 1 :
                            completeOffset = i+1
                            break
                        else :
                            closedPars -= 1
                    elif c == "," :
                        if closedPars == 0 and closedBrackets == 0 :
                            commas += 1
                    elif c == "{" : # TODO : check for { ... , ... , ... } to have the right comma count
                        closedBrackets -= 1
                        if closedBrackets < 0 :
                            commas = 0

                    elif c == "}" :
                        closedBrackets += 1

                #print("commas : " + str(commas))
                #print("closedBrackets : " + str(closedBrackets))
                #print("closedPars : " + str(closedPars))
                if closedBrackets < 0 :
                    show_hints = False
            else :

                completeOffset = max( prevDot + 1, prevPar + 1 , prevColon + 1 )
                skipped = src[completeOffset:offset]
                toplevelComplete = skippable.search( skipped ) is None and inAnonymous.search( skipped ) is None

        completeChar = src[completeOffset-1]
        inControlStruct = controlStruct.search( src[0:completeOffset] ) is not None

        toplevelComplete = toplevelComplete or completeChar in ":(," or inControlStruct

        if toplevelComplete :
            #print("toplevel")
            comps = self.get_toplevel_completion( src , src_dir , self.get_build( view ) )
            #print(comps)

        offset = completeOffset

        if src[offset-1]=="." and src[offset-2] in ".1234567890" :
            #comps.append(("... [iterator]",".."))
            comps.append((".","."))

        if toplevelComplete and (inControlStruct or completeChar not in "(,") :
            return comps,hints

        inp = (fn,offset,commas,src[0:offset-1])
        if self.currentCompletion["inp"] is None or inp != self.currentCompletion["inp"] :

            byte_offset = len(codecs.encode(src[0:offset], "utf-8"))
            temp = self.save_temp_file( view )
            ret , haxeComps , status , hints = self.run_haxe( view , { "filename" : fn , "offset" : byte_offset , "commas" : commas , "mode" : None })
            self.clear_temp_file( view , temp )

            if completeChar not in "(," :
                comps = haxeComps

            self.currentCompletion["outp"] = (ret,comps,status,hints)
        else :
            ret, comps, status , hints = self.currentCompletion["outp"]

        self.currentCompletion["inp"] = inp

        #print(ret)
        #print(status)
        #print(status)

        view.set_status( "haxe-status", status )

        #sublime.status_message("")
        if not show_hints :
            hints = []

        self.visibleCompletionList = comps
        return comps,hints

    def get_hxsl_completions( self , view , offset ) :
        comps = []
        for t in ["Float","Float2","Float3","Float4","Matrix","M44","M33","M34","M43","Texture","CubeTexture","Int","Color","include"] :
            comps.append( ( t , "hxsl Type" ) )
        return comps

    def get_hxml_completions( self , view , offset ) :
        src = view.substr(sublime.Region(0, offset))
        currentLine = src[src.rfind("\n")+1:offset]
        m = libFlag.match( currentLine )
        if m is not None :
            return HaxeLib.get_completions()
        else :
            return []

    def savetotemp( self, path, src ):
        f = tempfile.NamedTemporaryFile( delete=False )
        f.write( src )
        return f


class HaxeShowDocumentation( sublime_plugin.TextCommand ) :
    def run( self , edit ) :

        view = self.view
        complete = HaxeComplete.inst
        sel = view.sel()[0]

        # [('ID\tInt', 'ID'), ('_acceleration\tflixel.util.FlxPoint', '_acceleration'), ('_angleChanged\tBool', '_angleChanged'),
        current_function = complete.get_current_fn_name(view, sel.end() + 1)
        function_qualifications = current_function[:current_function.rfind(".")] + "." # If we have something like foo.bar.baz, this will return just foo.bar.
        current_function = current_function[current_function.rfind(".") + 1:] # And this will return baz.

        # Find what the autocompletion box is likely autocompleting to.

        possible_function_names = [x[0].split("\t")[0] for x in complete.visibleCompletionList]
        possible_function_names = [(x[:x.find("(")] if x.find("(") != -1 else x) for x in possible_function_names]

        matching_function_names = []

        for x in range(0, len(current_function)):
            smaller_name = current_function[:-x] if x != 0 else current_function # first try quux, then quu, then qu, then q. the if/else is a weird special case of slice notation.

            matching_function_names = [fn for fn in possible_function_names if fn.startswith(smaller_name)]

            if len(matching_function_names) > 0: break

        if len(matching_function_names) == 0: return

        best_match = matching_function_names[0]

        self.show_documentation(function_qualifications + best_match, edit)

    # Actually display the documentation in the documentation window.
    def show_documentation(self, fn_name, edit):
        window = sublime.active_window()

        if fn_name not in documentationStore:
            return

        doc_data = documentationStore[fn_name]

        hint = doc_data['hint'].split("\t")

        if( hint[1] == 'class' ) :
            hint_text = hint[1] + " " + hint[0]
        elif( hint[1] == 'package' ) :
            hint_text = hint[1] + " " + hint[0] + ";"
        else:
            hint_text = " : ".join( hint )

        documentation_text = "\n" + hint_text + "\n\n"

        documentation_lines = []

        if doc_data['doc'] is not None :
            documentation_lines = doc_data['doc'].split("\n")
        else :
            documentation_lines = ["","No documentation.",""]

        documentation_text += "/**\n";

        for line in documentation_lines:
            # Strip leading whitespace.
            line = line.strip()

            # Strip out any leading astericks.
            if len(line) > 0 and line[0] == "*":
                line = line[2:]

            documentation_text += line + "\n"

        documentation_text += "**/\n";

        doc_view = window.get_output_panel('haxe-doc');
        doc_view.set_syntax_file('Packages/Haxe/Haxe.tmLanguage')
        doc_view.settings().set('word_wrap', True)
        doc_view.insert(edit, doc_view.size(), documentation_text + "\n")
        window.run_command("show_panel", {"panel": "output.haxe-doc"})


class HaxeExecCommand(ExecCommand):
    def finish(self, *args, **kwargs):
        super(HaxeExecCommand, self).finish(*args, **kwargs)
        outp = self.output_view.substr(sublime.Region(0, self.output_view.size()))
        hc = HaxeComplete.inst
        hc.errors = hc.extract_errors( outp, self.output_view.settings().get("result_base_dir") )
        hc.highlight_errors( self.window.active_view() )

    def run(self, cmd = [],  shell_cmd = None, file_regex = "", line_regex = "", working_dir = "",
            encoding = None, env = {}, quiet = False, kill = False,
            # Catches "path" and "shell"
            **kwargs):

        if kill:
            if self.proc:
                self.proc.kill()
                self.proc = None
                self.append_data(None, "[Cancelled]")
            return

        if not hasattr(self, 'output_view'):
            # Try not to call get_output_panel until the regexes are assigned
            self.output_view = self.window.get_output_panel("exec")

        # Default the to the current files directory if no working directory was given
        if (working_dir == "" and self.window.active_view()
                        and self.window.active_view().file_name()):
            working_dir = os.path.dirname(self.window.active_view().file_name())

        self.output_view.settings().set("result_file_regex", file_regex)
        self.output_view.settings().set("result_line_regex", line_regex)
        self.output_view.settings().set("result_base_dir", working_dir)

        # Call get_output_panel a second time after assigning the above
        # settings, so that it'll be picked up as a result buffer
        self.window.get_output_panel("exec")

        if encoding is None :
            if int(sublime.version()) >= 3000 :
                encoding = sys.getfilesystemencoding()
            else:
                encoding = "utf-8"

        self.encoding = encoding
        self.quiet = quiet

        self.proc = None
        if not self.quiet:
            if int(sublime.version()) >= 3000 :
                print( "Running " + " ".join(cmd) )
            else :
                print( "Running " + " ".join(cmd).encode('utf-8') )

            sublime.status_message("Building")

        show_panel_on_build = sublime.load_settings("Preferences.sublime-settings").get("show_panel_on_build", True)
        if show_panel_on_build:
            self.window.run_command("show_panel", {"panel": "output.exec"})

        merged_env = env.copy()
        if self.window.active_view():
            user_env = self.window.active_view().settings().get('build_env')
            if user_env:
                merged_env.update(user_env)

        # Change to the working dir, rather than spawning the process with it,
        # so that emitted working dir relative path names make sense
        if working_dir != "":
            os.chdir(working_dir)

        self.debug_text = ""
        if shell_cmd:
            self.debug_text += "[shell_cmd: " + shell_cmd + "]\n"
        else:
            self.debug_text += "[cmd: " + str(cmd) + "]\n"
        self.debug_text += "[dir: " + str(os.getcwd()) + "]\n"
        if "PATH" in merged_env:
            self.debug_text += "[path: " + str(merged_env["PATH"]) + "]"
        else:
            self.debug_text += "[path: " + str(os.environ["PATH"]) + "]"

        err_type = OSError
        if os.name == "nt":
            err_type = WindowsError

        try:
            # Forward kwargs to AsyncProcess
            if int(sublime.version()) >= 3000 :
                self.proc = AsyncProcess(cmd, None, merged_env, self, **kwargs)
            else :

                self.proc = AsyncProcess([c.encode(sys.getfilesystemencoding()) for c in cmd], merged_env, self, **kwargs)
        except err_type as e:
            self.append_data(None, str(e) + "\n")
            self.append_data(None, "[cmd:  " + str(cmd) + "]\n")
            self.append_data(None, "[dir:  " + str(os.getcwdu()) + "]\n")
            if "PATH" in merged_env:
                self.append_data(None, "[path: " + str(merged_env["PATH"]) + "]\n")
            else:
                self.append_data(None, "[path: " + str(os.environ["PATH"]) + "]\n")
            if not self.quiet:
                self.append_data(None, "[Finished]")


    def is_visible():
        return false

    def on_data(self, proc, data):
        sublime.set_timeout(functools.partial(self.append_data, proc, data), 0)

    def on_finished(self, proc):
        sublime.set_timeout(functools.partial(self.finish, proc), 1)

class HaxelibExecCommand(ExecCommand):
    def finish(self, *args, **kwargs):
        super(HaxelibExecCommand, self).finish(*args, **kwargs)
        HaxeLib.scan( sublime.active_window().active_view() )

    def is_visible():
        return false
