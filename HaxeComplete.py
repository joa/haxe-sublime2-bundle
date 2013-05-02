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

from xml.etree import ElementTree
from xml.etree.ElementTree import XMLTreeBuilder
#from xml.etree import ElementTree
from elementtree import SimpleXMLTreeBuilder # part of your codebase
ElementTree.XMLTreeBuilder = SimpleXMLTreeBuilder.TreeBuilder

from subprocess import Popen, PIPE
from datetime import datetime

stexec = __import__("exec")

try:
  STARTUP_INFO = subprocess.STARTUPINFO()
  STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
  STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
	STARTUP_INFO = None

def runcmd( args, input=None ):
	#print(args)
	try:
		p = Popen([a.encode(sys.getfilesystemencoding()) for a in args], stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=STARTUP_INFO)
		if isinstance(input, unicode):
			input = input.encode('utf-8')
		out, err = p.communicate(input=input)
		return (out.decode('utf-8') if out else '', err.decode('utf-8') if err else '')
	except (OSError, ValueError) as e:
		err = u'Error while running %s: %s' % (args[0], e)
		return ("", err.decode('utf-8'))

compilerOutput = re.compile("^([^:]+):([0-9]+): (characters?|lines?) ([0-9]+)-?([0-9]+)? : (.*)", re.M)
compactFunc = re.compile("\(.*\)")
compactProp = re.compile(":.*\.([a-z_0-9]+)", re.I)
spaceChars = re.compile("\s")
wordChars = re.compile("[a-z0-9._]", re.I)
importLine = re.compile("^([ \t]*)import\s+([a-z0-9._]+);", re.I | re.M)
packageLine = re.compile("package\s*([a-z0-9.]*);", re.I)
libLine = re.compile("([^:]*):[^\[]*\[(dev\:)?(.*)\]")
classpathLine = re.compile("Classpath : (.*)")
typeDecl = re.compile("(class|typedef|enum|typedef)\s+([A-Z][a-zA-Z0-9_]*)\s*(<[a-zA-Z0-9_,]+>)?" , re.M )
libFlag = re.compile("-lib\s+(.*?)")
skippable = re.compile("^[a-zA-Z0-9_\s]*$")
inAnonymous = re.compile("[{,]\s*([a-zA-Z0-9_\"\']+)\s*:\s*$" , re.M | re.U )
extractTag = re.compile("<([a-z0-9_-]+).*\s(name|main|path)=\"([a-z0-9_./-]+)\"", re.I)
variables = re.compile("var\s+([^:;\s]*)", re.I)
functions = re.compile("function\s+([^;\.\(\)\s]*)", re.I)
functionParams = re.compile("function\s+[a-zA-Z0-9_]+\s*\(([^\)]*)", re.M)
paramDefault = re.compile("(=\s*\"*[^\"]*\")", re.M)
isType = re.compile("^[A-Z][a-zA-Z0-9_]*$")
comments = re.compile("(//[^\n\r]*?[\n\r]|/\*(.*?)\*/)", re.MULTILINE | re.DOTALL )

haxeVersion = re.compile("(Haxe|haXe) Compiler ([0-9]\.[0-9])",re.M)
bundleFile = __file__
bundlePath = os.path.abspath(bundleFile)
bundleDir = os.path.dirname(bundlePath)
#haxeFileRegex = "^([^:]*):([0-9]+): characters? ([0-9]+)-?[0-9]* :(.*)$"
haxeFileRegex = "^([^:]*\.hx):([0-9]+):.*$"
controlStruct = re.compile( "\s*(if|switch|for|while)\($" );

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
	def scan() :
		hlout, hlerr = runcmd( ["haxelib" , "config" ] )
		HaxeLib.basePath = hlout.strip()

		HaxeLib.available = {}

		hlout, hlerr = runcmd( ["haxelib" , "list" ] )

		for l in hlout.split("\n") :
			found = libLine.match( l )
			if found is not None :
				name, dev, version = found.groups()
				lib = HaxeLib( name , dev is not None , version )

				HaxeLib.available[ name ] = lib



HaxeLib.scan()

inst = None
class HaxeBuild :

	#auto = None
	targets = ["js","cpp","swf","neko","php","java","cs"]
	nme_targets = [
		("Flash - test","flash -debug","test"),
		("Flash - build only","flash -debug","build"),
		("HTML5 - test","html5 -debug","test"),
		("HTML5 - build only","html5 -debug","build"),
		("C++ - test","cpp -debug","test"),
		("C++ - build only","cpp -debug","build"),
		("Linux - test","linux -debug","test"), 
		("Linux - build only","linux -debug","build"), 
		("Linux 64 - test","linux -64 -debug","test"),
		("Linux 64 - build only","linux -64 -debug","build"),
		("iOS - test in iPhone simulator","ios -simulator -debug","test"),
		("iOS - test in iPad simulator","ios -simulator -ipad -debug","test"),
		("iOS - update XCode project","ios -debug","update"),
		("Android - test","android -debug","test"),
		("Android - build only","android -debug","build"),
		("WebOS - test", "webos -debug","test"),
		("WebOS - build only", "webos -debug","build"),
		("Neko - test","neko -debug","test"),
		("Neko - build only","neko -debug","build"),
		("Neko 64 - test","neko -64 -debug","test"),
		("Neko 64 - build only","neko -64 -debug","build"),
		("BlackBerry - test","blackberry -debug","test"),
		("BlackBerry - build only","blackberry -debug","build")
	]
	nme_target = ("Flash - test","flash -debug","test")

	def __init__(self) :

		self.args = []
		self.main = None
		self.target = None
		self.output = "dummy.js"
		self.hxml = None
		self.nmml = None
		self.classpaths = []
		self.libs = []
		self.classes = None
		self.packages = None

	def to_string(self) :
		out = os.path.basename(self.output)
		if self.nmml is not None:
			return "{out} ({target})".format(self=self, out=out, target=HaxeBuild.nme_target[0]);
		else:
			return "{main} ({target}:{out})".format(self=self, out=out, main=self.main, target=self.target);
		#return "{self.main} {self.target}:{out}".format(self=self, out=out);

	def make_hxml( self ) :
		outp = "# Autogenerated "+self.hxml+"\n\n"
		outp += "# "+self.to_string() + "\n"
		outp += "-main "+ self.main + "\n"
		for a in self.args :
			outp += " ".join( list(a) ) + "\n"

		d = os.path.dirname( self.hxml ) + "/"

		# relative paths
		outp = outp.replace( d , "")
		outp = outp.replace( "-cp "+os.path.dirname( self.hxml )+"\n", "")

		outp = outp.replace("--no-output " , "")
		outp = outp.replace("-v" , "")

		outp = outp.replace("dummy" , self.main.lower() )

		#print( outp )
		return outp.strip()

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
			for path in cp :
				c, p = HaxeComplete.inst.extract_types( os.path.join( os.path.dirname( self.hxml ), path ) )
				classes.extend( c )
				packs.extend( p )

			classes.sort()
			packs.sort()

			self.classes = classes;
			self.packs = packs;

		return self.classes, self.packs


class HaxeInstallLib( sublime_plugin.WindowCommand ):
	def run(self):
		out,err = runcmd(["haxelib" , "search" , " "]);
		libs = out.splitlines()
		self.libs = libs[0:-1]

		menu = []
		for l in self.libs :
			if l in HaxeLib.available :
				menu.append( [ l + " [" + HaxeLib.available[l].version + "]" , "Remove" ] )
			else :
				menu.append( [ l , 'Install' ] )

		menu.append( ["Upgrade libraries"] )

		self.window.show_quick_panel(menu,self.install)

	def install( self, i ):
		if i < 0 :
			return

		if i == len(self.libs) :
			cmd = ["haxelib" , "upgrade" ]
		else :
			lib = self.libs[i]
			if lib in HaxeLib.available :
				cmd = ["haxelib" , "remove" , lib ]
			else :
				cmd = ["haxelib" , "install" , lib ]


		self.window.run_command("haxelib_exec", {
			"cmd": cmd,
			#"working_dir": os.path.dirname()
		})


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
		complete = HaxeComplete.inst
		view = self.view
		src = view.substr(sublime.Region(0, view.size()))
		self.get_classname(view, src)

		if self.cname[1] == "":
			sublime.status_message("Nothing to import")
			return

		self.compact_classname(edit, view)

		if re.search("import\s+{0};".format("".join(self.cname)), src):
			sublime.status_message("Already imported")
			return

		self.insert_import(edit, view, src)


class HaxeDisplayCompletion( sublime_plugin.TextCommand ):

	def run( self , edit ) :
		#print("completing")
		view = self.view
		s = view.settings();

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

		for r in view.sel() :
			comps = complete.get_haxe_completions( self.view , r.end() )
			#print(status);
			#view.set_status("haxe-status", status)
			#sublime.status_message(status)
			#if( len(comps) > 0 ) :
			#	view.run_command('auto_complete', {'disable_auto_insert': True})


class HaxeRestartServer( sublime_plugin.WindowCommand ):

	def run( self ) :
		view = sublime.active_window().active_view()
		HaxeComplete.inst.stop_server()
		HaxeComplete.inst.start_server( view )


class HaxeCreateType( sublime_plugin.WindowCommand ):

	classpath = None
	currentFile = None
	currentSrc = None
	currentType = None

	def run( self , paths = [] , t = "class" ) :
		builds = HaxeComplete.inst.builds
		HaxeCreateType.currentType = t
		view = sublime.active_window().active_view()
		scopes = view.scope_name(view.sel()[0].end()).split()

		pack = [];

		if len(builds) == 0 :
			HaxeComplete.inst.extract_build_args(view)

		if len(paths) == 0 :
			fn = view.file_name()
			paths.append(fn)

		for path in paths :

			if os.path.isfile( path ) :
				path = os.path.dirname( path )

			if HaxeCreateType.classpath is None :
				HaxeCreateType.classpath = path

			for b in builds :
				for cp in b.classpaths :
					if path.startswith( cp ) :
						HaxeCreateType.classpath = path[0:len(cp)]
						for p in path[len(cp):].split(os.sep) :
							if "." in p :
								break
							elif p :
								pack.append(p)

		if HaxeCreateType.classpath is None :
		 	if len(builds) > 0 :
				HaxeCreateType.classpath = builds[0].classpaths[0]

		# so default text ends with .
		if len(pack) > 0 :
			pack.append("")

		win = sublime.active_window()
		sublime.status_message( "Current classpath : " + HaxeCreateType.classpath )
		win.show_input_panel("Enter "+t+" name : " , ".".join(pack) , self.on_done , self.on_change , self.on_cancel )

	def on_done( self , inp ) :

		fn = self.classpath;
		parts = inp.split(".")
		pack = []

		while( len(parts) > 0 ):
			p = parts.pop(0)

			fn = os.path.join( fn , p )
			if isType.match( p ) :
				cl = p
				break;
			else :
				pack.append(p)

		if len(parts) > 0 :
			cl = parts[0]

		fn += ".hx"

		HaxeCreateType.currentFile = fn
		t = HaxeCreateType.currentType
		src = "\npackage " + ".".join(pack) + ";\n\n"+t+" "+cl+" "
		if t == "typedef" :
			src += "= "
		src += "{\n\n\t\n\n}"
		HaxeCreateType.currentSrc = src

		v = sublime.active_window().open_file( fn )

	@staticmethod
	def on_activated( view ) :
		if view.file_name() == HaxeCreateType.currentFile and view.size() == 0 :
			e = view.begin_edit()
			view.insert(e,0,HaxeCreateType.currentSrc)
			view.end_edit(e)
			sel = view.sel()
			sel.clear()
			pt = view.text_point(5,1)
			sel.add( sublime.Region(pt,pt) )


	def on_change( self , inp ) :
		sublime.status_message( "Current classpath : " + HaxeCreateType.classpath )
		#print( inp )

	def on_cancel( self ) :
		None

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

	stdPaths = []
	stdPackages = []
	#stdClasses = ["Void","Float","Int","UInt","Null","Bool","Dynamic","Iterator","Iterable","ArrayAccess"]
	stdClasses = []
	stdCompletes = []

	panel = None
	serverMode = False
	serverProc = None
	serverPort = 6000

	compilerVersion = 2

	def __init__(self):
		#print("init haxecomplete")
		HaxeComplete.inst = self

		out, err = runcmd( ["haxe", "-main", "Nothing", "-v", "--no-output"] )

		_, versionOut = runcmd(["haxe", "-v"])

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

	def __del__(self) :
		self.stop_server()


	def extract_types( self , path , depth = 0 ) :

		classes = []
		packs = []
		hasClasses = False

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

					if( packDepth == depth ) : # and t == cl or cl == "StdTypes"
						if t == cl or cl == "StdTypes":
							classes.append( t )
						else:
							classes.append( cl + "." + t )

						hasClasses = True


		if hasClasses or depth == 0 :

			for f in os.listdir( path ) :

				cl, ext = os.path.splitext( f )

				if os.path.isdir( os.path.join( path , f ) ) and f not in HaxeComplete.stdPackages :
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

		for e in self.errors :
			if fn.endswith(e["file"]) :
				metric = e["metric"]
				l = e["line"]
				left = e["from"]
				right = e["to"]

				if metric.startswith("character") :
					a = view.text_point(l,left)
					b = view.text_point(l,right)
					char_regions.append( sublime.Region(a,b))
				else :
					a = view.text_point(left,0)
					b = view.text_point(right,0)
					line_regions.append( sublime.Region(a,b))

				view.set_status("haxe-status" , "Error: " + e["message"] )

		view.add_regions("haxe-error-lines" , line_regions , "invalid" , "light_x_bright" , sublime.DRAW_OUTLINED )
		view.add_regions("haxe-error" , char_regions , "invalid" , "light_x_bright" )


	def on_load( self, view ) :

		if view.score_selector(0,'source.haxe.2') > 0 :
			HaxeCreateType.on_activated( view )
		elif view.score_selector(0,'source.hxml,source.erazor,source.nmml') == 0:
			return

		self.generate_build( view )
		self.highlight_errors( view )


	def on_post_save( self , view ) :
		if view.score_selector(0,'source.hxml') > 0:
			self.clear_build(view)

	def on_activated( self , view ) :
		if view.score_selector(0,'source.haxe.2') > 0 :
			HaxeCreateType.on_activated( view )
		elif view.score_selector(0,'source.hxml,source.erazor,source.nmml') == 0:
			return

		self.get_build(view)
		self.extract_build_args( view )

		self.generate_build(view)
		self.highlight_errors( view )

	def on_pre_save( self , view ) :
		if view.score_selector(0,'source.haxe.2') > 0 :
			return []

		fn = view.file_name()
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
		#	view.run_command("haxe_insert_completion")


	def generate_build(self, view) :

		fn = view.file_name()

		if self.currentBuild is not None and fn == self.currentBuild.hxml and view.size() == 0 :
			e = view.begin_edit()
			hxmlSrc = self.currentBuild.make_hxml()
			view.insert(e,0,hxmlSrc)
			view.end_edit(e)


	def select_build( self , view ) :
		scopes = view.scope_name(view.sel()[0].end()).split()

		if 'source.hxml' in scopes:
			view.run_command("save")

		self.extract_build_args( view , True )


	def find_nmml( self, folder ) :
		nmmls = glob.glob( os.path.join( folder , "*.nmml" ) )

		for build in nmmls:
			currentBuild = HaxeBuild()
			currentBuild.hxml = build
			currentBuild.nmml = build
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
			currentBuild.target = "cpp"
			currentBuild.args.append( ("--remap", "flash:nme") )
			currentBuild.args.append( ("-cpp", outp) )
			currentBuild.output = outp

			if currentBuild.main is not None :
				self.builds.append( currentBuild )

	def find_hxml( self, folder ) :
		hxmls = glob.glob( os.path.join( folder , "*.hxml" ) )
		for build in hxmls:

			currentBuild = HaxeBuild()
			currentBuild.hxml = build
			buildPath = os.path.dirname(build);

			# print("build file exists")
			f = codecs.open( build , "r+" , "utf-8" , "ignore" )
			while 1:
				l = f.readline()
				if not l :
					break;
				if l.startswith("--next") :
					self.builds.append( currentBuild )
					currentBuild = HaxeBuild()
					currentBuild.hxml = build

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
				#	currentBuild.args.append( ( "--connect" , str(self.serverPort) ))

				for flag in [ "lib" , "D" , "swf-version" , "swf-header", "debug" , "-no-traces" , "-flash-use-stage" , "-gen-hx-classes" , "-remap" , "-no-inline" , "-no-opt" , "-php-prefix" , "-js-namespace" , "-interp" , "-macro" , "-dead-code-elimination" , "-remap" , "-php-front" , "-php-lib", "-dce" , "-js-modern" , "swf-lib" ] :
					if l.startswith( "-"+flag ) :
						currentBuild.args.append( tuple(l.split(" ") ) )

						break

				for flag in [ "resource" , "xml" , "x" , "java-lib" ] :
					if l.startswith( "-"+flag ) :
						spl = l.split(" ")
						outp = os.path.join( folder , " ".join(spl[1:]) )
						currentBuild.args.append( ("-"+flag, outp) )

						break

				#print(HaxeBuild.targets)
				for flag in HaxeBuild.targets :
					if l.startswith( "-" + flag + " " ) :
					
						spl = l.split(" ")
						#outp = os.path.join( folder , " ".join(spl[1:]) )
						outp = " ".join(spl[1:])
						currentBuild.args.append( ("-"+flag, outp) )

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
                        self.builds.append( currentBuild )



	def extract_build_args( self , view , forcePanel = False ) :

		self.builds = []

		fn = view.file_name()

		settings = view.settings()

		folder = os.path.dirname(fn)

		folders = view.window().folders()
		if len(folders) == 1:
			folder = folders[0]
		else:
			for f in folders:
				if f + "/" in fn :
					folder = f

		# settings.set("haxe-complete-folder", folder)
		self.find_hxml(folder)
		self.find_nmml(folder)

		if len(self.builds) == 1:
			if forcePanel :
				sublime.status_message("There is only one build")

			# will open the build file
			#if forcePanel :
			#	b = self.builds[0]
			#	f = b.hxml
			#	v = view.window().open_file(f,sublime.TRANSIENT)

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
				#	v.append( " ".join(a) )
				buildsView.append( [b.to_string(), os.path.basename( b.hxml ) ] )

			self.selectingBuild = True
			sublime.status_message("Please select your build")
			view.window().show_quick_panel( buildsView , lambda i : self.set_current_build(view, int(i), forcePanel) , sublime.MONOSPACE_FONT )

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

				view.window().show_quick_panel(nme_targets, lambda i : self.select_nme_target(i, view))


	def select_nme_target( self, i, view ):
		target = HaxeBuild.nme_targets[i]
		if self.currentBuild.nmml is not None:
			HaxeBuild.nme_target = target
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

		if build.nmml is not None or HaxeLib.get("nme") in build.libs :
			tarPkg = "nme"
			targetPackages.extend( ["jeash","neash","browser","native"] )

		#print( "tarpkg : " + tarPkg );
		#for c in HaxeComplete.stdClasses :
		#	p = c.split(".")[0]
		#	if tarPkg is None or (p not in targetPackages) or (p == tarPkg) :
		#		cl.append(c)

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
			#	p = "flash"
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
			#	spl[0] = "flash"

			top = spl[0]
			#print(spl)

			clname = spl.pop()
			pack = ".".join(spl)
			display = clname

			#if pack in imported:
			#	pack = ""

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

		if self.currentBuild is None and view.score_selector(0,"source.haxe.2") > 0 :

			fn = view.file_name()
			src_dir = os.path.dirname( fn )
			src = view.substr(sublime.Region(0, view.size()))

			build = HaxeBuild()
			build.target = "js"

			folder = os.path.dirname(fn)
			folders = view.window().folders()
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
			cl = cl.encode('ascii','ignore')
			cl = cl[0:cl.rfind(".")]

			main = pack[0:]
			main.append( cl )
			build.main = ".".join( main )

			build.output = os.path.join(folder,build.main.lower() + ".js")

			build.args.append( ("-cp" , src_dir) )
			#build.args.append( ("-main" , build.main ) )

			build.args.append( ("-js" , build.output ) )
			#build.args.append( ("--no-output" , "-v" ) )

			build.hxml = os.path.join( src_dir , "build.hxml")

			#build.hxml = os.path.join( src_dir , "build.hxml")
			self.currentBuild = build

		return self.currentBuild


	def run_nme( self, view, build ) :

		cmd = [ "haxelib", "run", "nme", HaxeBuild.nme_target[2], os.path.basename(build.nmml) ]
		target = HaxeBuild.nme_target[1].split(" ")
		cmd.extend(target)
		cmd.append("-debug")

		view.window().run_command("exec", {
			"cmd": cmd,
			"working_dir": os.path.dirname(build.nmml),
			"file_regex": "^([^:]*):([0-9]+): characters [0-9]+-([0-9]+) :.*$"
		})
		return ("" , [], "" )

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

					haxepath = settings.get("haxe_path" , "haxe")

				self.serverPort+=1
				cmd = [haxepath , "--wait" , str(self.serverPort) ]
				#self.serverProc = Popen(cmd, env=env , startupinfo=STARTUP_INFO)
				self.serverProc = Popen(cmd, env = merged_env, startupinfo=STARTUP_INFO)
				self.serverProc.poll()
			except(OSError, ValueError) as e:
				err = u'Error starting server %s: %s' % (" ".join(cmd), e)
				sublime.error_message(err)

	def stop_server( self ) :

		if self.serverProc is not None :
			self.serverProc.terminate()
			self.serverProc.kill()
			self.serverProc.wait()

		self.serverProc = None
		del self.serverProc


	def run_haxe( self, view , display = None , commas = 0 ) :

		self.start_server( view )

		build = self.get_build( view )
		settings = view.settings()

		autocomplete = display is not None

		if autocomplete is False and build is not None and build.nmml is not None:
			return self.run_nme(view, build)

		fn = view.file_name()
		src = view.substr(sublime.Region(0, view.size()))
		src_dir = os.path.dirname(fn)
		tdir = os.path.dirname(fn)
		temp = os.path.join( tdir , os.path.basename( fn ) + ".tmp" )

		comps = []

		self.errors = []

		args = []

		cwd = os.path.dirname( build.hxml )

		#buildArgs = view.window().settings


		args.extend( build.args )
		buildServerMode = settings.get('haxe_build_server_mode', True)

		if self.serverMode and (autocomplete or buildServerMode) : #and autocomplete:
			args.append(("--connect" , str(HaxeComplete.inst.serverPort)))
			args.append(("--cwd" , cwd ))
		#args.append( ("--times" , "-v" ) )
		if not autocomplete :
			args.append( ("-main" , build.main ) )
			#args.append( ("--times" , "-v" ) )
		else:
			args.append( ("-D", "st_display" ) )
			args.append( ("--display", display ) )
			args.append( ("--no-output",) )
			#args.append( ("-cp" , bundleDir ) )
			#args.append( ("--macro" , "SourceTools.complete()") )


		haxepath = settings.get( 'haxe_path' , 'haxe' )
		cmd = [haxepath]
		for a in args :
			cmd.extend( list(a) )

		#print( cmd )
		#
		# TODO: replace runcmd with run_command('exec') when possible (haxelib, maybe build)
		#
		if not autocomplete :
			encoded_cmd = []
			for c in cmd :
				#if isinstance( c , unicode) :
				#	encoded_cmd.append( c.encode('utf-8') )
				#else :
					encoded_cmd.append( c )

			#print(encoded_cmd)

			env = {}
			if settings.has("haxe_library_path") :
				env["HAXE_LIBRARY_PATH"] = settings.get("haxe_library_path",".")

			view.window().run_command("haxe_exec", {
				"cmd": encoded_cmd,
				"working_dir": cwd,
				"file_regex": haxeFileRegex,
				"env" : env
			})
			return ("" , [], "" )


		#print(cmd)
		res, err = runcmd( cmd, "" )
		#print(err)

		if not autocomplete :
			self.panel_output( view , " ".join(cmd) )

		#print( res.encode("utf-8") )
		status = ""

		if (not autocomplete) and (build.hxml is None) :
			#status = "Please create an hxml file"
			self.extract_build_args( view , True )
		elif not autocomplete :
			# default message = build success
			status = "Build success"


		#print(err)
		hints = []
		tree = None

		try :
			x = "<root>"+err.encode('utf-8')+"</root>";
			tree = ElementTree.XML(x);

		except Exception, e:
		#	print(e)
			print("invalid xml")

		if tree is not None :
			for i in tree.getiterator("type") :
				hint = i.text.strip()
				types = hint.split(" -> ")
				ret = types.pop()
				msg = "";

				if commas >= len(types) :
					if commas == 0 :
						msg = hint + ": No autocompletion available"
						#view.window().run_command("hide_auto_complete")
						#comps.append((")",""))
					else:
						msg =  "Too many arguments."
				else :
					msg = ", ".join(types[commas:])

				if msg :
					#msg =  " ( " + " , ".join( types ) + " ) : " + ret + "      " + msg
					hints.append( msg )

			if len(hints) > 0 :
				status = " | ".join(hints)

			li = tree.find("list")
			if li is not None :
				for i in li.getiterator("i"):
					name = i.get("n")
					sig = i.find("t").text
					doc = i.find("d").text #nothing to do
					insert = name
					hint = name

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
							else:
								hint = name + "( " + " , ".join( types ) + " )\t" + ret
								if len(hint) > 40: # compact arguments
									hint = compactFunc.sub("(...)", hint);
								insert = cm
						else :
							hint = name + "\t" + ret
					else :
						if re.match("^[A-Z]",name ) :
							hint = name + "\tclass"
						else :
							hint = name + "\tpackage"

					#if doc is not None :
					#	hint += "\t" + doc
					#	print(doc)

					if len(hint) > 40: # compact return type
						m = compactProp.search(hint)
						if not m is None:
							hint = compactProp.sub(": " + m.group(1), hint)

					comps.append( ( hint, insert ) )

		if len(hints) == 0 and len(comps) == 0:
			err = err.replace( temp , fn )
			err = re.sub( u"\(display(.*)\)" ,"",err)

			lines = err.split("\n")
			l = lines[0].strip()

			if len(l) > 0 :
				if l == "<list>" :
					status = "No autocompletion available"
				elif not re.match( haxeFileRegex , l ):
					status = l
				else :
					status = ""

			#regions = []

			# for infos in compilerOutput.findall(err) :
			# 	infos = list(infos)
			# 	f = infos.pop(0)
			# 	l = int( infos.pop(0) )-1
			# 	left = int( infos.pop(0) )
			# 	right = infos.pop(0)
			# 	if right != "" :
			# 		right = int( right )
			# 	else :
			# 		right = left+1
			# 	m = infos.pop(0)

			# 	self.errors.append({
			# 		"file" : f,
			# 		"line" : l,
			# 		"from" : left,
			# 		"to" : right,
			# 		"message" : m
			# 	})

			# 	if( f == fn ):
			# 		status = m

			# 	if not autocomplete :
			# 		w = view.window()
			# 		if not w is None :
			# 			w.open_file(f+":"+str(l)+":"+str(right) , sublime.ENCODED_POSITION  )
			# 	#if not autocomplete

			self.errors = self.extract_errors( err )
			#self.highlight_errors( view )

		#print(status)
		return ( err, comps, status )

	def extract_errors( self , str ):
		errors = []

		for infos in compilerOutput.findall(str) :
			infos = list(infos)
			print(infos)
			f = infos.pop(0)
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
				comps = self.get_haxe_completions( view , offset )

		return comps

	def get_haxe_completions( self , view , offset ):

		src = view.substr(sublime.Region(0, view.size()))
		fn = view.file_name()
		src_dir = os.path.dirname(fn)
		tdir = os.path.dirname(fn)
		temp = os.path.join( tdir , os.path.basename( fn ) + ".tmp" )

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
						if closedPars == 0 :
							commas += 1
					elif c == "{" : # TODO : check for { ... , ... , ... } to have the right comma count
						commas = 0
						closedBrackets -= 1
					elif c == "}" :
						closedBrackets += 1

				#print("closedBrackets : " + str(closedBrackets))

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
			return comps

		if not os.path.exists( tdir ):
			os.mkdir( tdir )

		if os.path.exists( fn ):
			# copy saved file to temp for future restoring
			shutil.copy2( fn , temp )

		# write current source to file
		f = codecs.open( fn , "wb" , "utf-8" , "ignore" )
		f.write( src )
		f.close()

		inp = (fn,offset,commas,src[0:offset-1])
		if self.currentCompletion["inp"] is None or inp != self.currentCompletion["inp"] :
			ret , haxeComps , status = self.run_haxe( view , fn + "@" + str(offset) , commas )

			if completeChar not in "(," :
				comps = haxeComps

			self.currentCompletion["outp"] = (ret,comps,status)
		else :
			ret, comps, status = self.currentCompletion["outp"]

		self.currentCompletion["inp"] = inp

		#print(ret)
		#print(status)
		#print(status)

		view.set_status( "haxe-status", status )

		#os.remove(temp)
		if os.path.exists( temp ) :
			shutil.copy2( temp , fn )
			os.remove( temp )
		else:
			# fn didn't exist in the first place, so we remove it
			os.remove( fn )

		#sublime.status_message("")

		return comps

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


class HaxeExecCommand(stexec.ExecCommand):
    def finish(self, *args, **kwargs):
        super(HaxeExecCommand, self).finish(*args, **kwargs)
        outp = self.output_view.substr(sublime.Region(0, self.output_view.size()))
        hc = HaxeComplete.inst
        hc.errors = hc.extract_errors( outp )
        hc.highlight_errors( self.window.active_view() )

    def run(self, cmd = [], file_regex = "", line_regex = "", working_dir = "",
            encoding = "utf-8", env = {}, quiet = False, kill = False,
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

        self.encoding = encoding
        self.quiet = quiet

        self.proc = None
        if not self.quiet:
            self.append_data( None, "Running " + " ".join(cmd).encode('utf-8') + "\n" )
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

        err_type = OSError
        if os.name == "nt":
            err_type = WindowsError

        try:
            # Forward kwargs to AsyncProcess
            self.proc = stexec.AsyncProcess(cmd, merged_env, self, **kwargs)
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



class HaxelibExecCommand(stexec.ExecCommand):
    def finish(self, *args, **kwargs):
        super(HaxelibExecCommand, self).finish(*args, **kwargs)
        HaxeLib.scan()

    def is_visible():
    	return false
