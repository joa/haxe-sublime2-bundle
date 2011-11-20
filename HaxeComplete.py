import sublime, sublime_plugin
import subprocess
import tempfile
import os
import xml.parsers.expat
import re
import codecs
import glob
import hashlib
import shutil
from xml.etree import ElementTree
from subprocess import Popen, PIPE

try:
    STARTUP_INFO = subprocess.STARTUPINFO()
    STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
	STARTUP_INFO = None


compilerOutput = re.compile("([^:]+):([0-9]+): characters? ([0-9]+)-?([0-9]+)? : (.*)")
packageLine = re.compile("package ([a-z_.]*);")

inst = None
class HaxeBuild :

	#auto = None

	def __init__(self) :

		self.args = []
		self.main = "Main"
		self.target = "js"
		self.output = "dummy.js"
		self.hxml = None

	def to_string(self) :
		out = os.path.basename(self.output)
		return "{self.main} {self.target}:{out}".format(self=self, out=out);
	
	def make_hxml( self ) :
		
		outp = "# "+self.to_string() + "\n"
		outp += "-main "+ self.main + "\n"
		for a in self.args :
			outp += " ".join( list(a) ) + "\n"
		
		d = os.path.dirname( self.hxml ) + "/"
		outp = outp.replace( d , "")
		outp = outp.replace("--no-output " , "")
		#print( outp )
		return outp



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
	def run( self , edit ) :
		#print("haxe hint")
		
		complete = HaxeComplete.inst
		view = self.view
		
		sel = view.sel()
		for r in sel :
			ret , comps , status = complete.run_haxe( self.view , r.end() )
			#view.set_status("haxe-status", status )
			if( len(comps) > 0 ) :
				view.run_command('auto_complete', {'disable_auto_insert': True})


class HaxeComplete( sublime_plugin.EventListener ):

	#folder = ""
	#buildArgs = []
	currentBuild = None
	selectingBuild = False
	builds = []
	errors = []

	def __init__(self):
		HaxeComplete.inst = self

	def highlight_errors( self , view ) :
		fn = view.file_name()
		regions = []

		for e in self.errors :
			if e["file"] == fn :
				l = e["line"]
				left = e["from"]
				right = e["to"]
				a = view.text_point(l,left)
				b = view.text_point(l,right)

				regions.append( sublime.Region(a,b))

				view.set_status("haxe-status" , "Error: " + e["message"] )
				
		view.add_regions("haxe-error" , regions , "invalid" , "dot" )


	def on_load( self, view ) :
		scopes = view.scope_name(view.sel()[0].end()).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes and 'source.hxml' not in scopes:
			return []
		
		fn = view.file_name()

		if not self.currentBuild is None and fn == self.currentBuild.hxml and view.size() == 0 :
			e = view.begin_edit()
			hxmlSrc = self.currentBuild.make_hxml()
			print(hxmlSrc)
			view.insert(e,0,hxmlSrc)
			view.end_edit(e)

		self.highlight_errors( view )
		
	
	def on_activated( self , view ) :
		scopes = view.scope_name(view.sel()[0].end()).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes and 'source.hxml' not in scopes:
			return []
		
		self.extract_build_args( view )
		self.highlight_errors( view )


	def select_build( self , view ) :
		self.extract_build_args( view , True )

	def extract_build_args( self , view , forcePanel = False ) :
		scopes = view.scope_name(view.sel()[0].end()).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes and 'source.hxml' not in scopes:
			return []
		
		#print("extracting build args")
		
		self.builds = []

		fn = view.file_name()
		settings = view.settings()

		folder = os.path.dirname(fn)
		
		folders = view.window().folders()
		for f in folders:
			if f in fn :
				folder = f

		settings.set("haxe-complete-folder", folder)

		hxmls = glob.glob( os.path.join( folder , "*.hxml" ) )

		for build in hxmls:

			currentBuild = HaxeBuild()
			currentBuild.hxml = build
			buildPath = os.path.dirname(build);

			# print("build file exists")
			f = open( build , "r+" )
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
					currentBuild.main = l.split(" ")[1]
				for flag in ["lib" , "D"] :
					if l.startswith( "-"+flag ) :
						currentBuild.args.append( tuple(l.split(" ") ) )
						#for a in l.split(" ") :
						#	currentArgs.append( a )
						break
				for flag in ["js" , "php" , "cpp" , "neko"] :
					if l.startswith( "-"+flag ) :
						spl = l.split(" ")
						outp = os.path.join( folder , " ".join(spl[1:]) )
						currentBuild.args.append( ("-"+flag, outp) )
						
						currentBuild.target = flag
						currentBuild.output = outp
						break
				if l.startswith("-cp "):
					cp = l.split(" ")
					view.set_status( "haxe-status" , "Building..." )
					cp.pop(0)
					classpath = " ".join( cp )
					currentBuild.args.append( ("-cp" , os.path.join( buildPath , classpath ) ) )

			if len(currentBuild.args) > 0 :
				self.builds.append( currentBuild )
		
		if len(self.builds) == 0 and forcePanel :
			sublime.status_message("No hxml file found...")
			
			self.run_haxe(view,False)

			f = os.path.join(folder,"build.hxml")
			v = view.window().open_file(f)
			
			if not self.currentBuild is None :
				self.currentBuild.hxml = f

		elif len(self.builds) > 1 and forcePanel :
			buildsView = []
			for b in self.builds :
				#for a in b.args :
				#	v.append( " ".join(a) )
				buildsView.append( [b.to_string(), os.path.basename( b.hxml ) ] )

			self.selectingBuild = True
			sublime.status_message("Please select your build")
			view.window().show_quick_panel( buildsView , lambda i : self.set_current_build(view,i) , sublime.MONOSPACE_FONT )
		
		elif settings.has("haxe-build-id"):
			self.set_current_build( view , settings.get("haxe-build-id") )
		
		else:
			self.set_current_build( view , 0 )



	def set_current_build( self , view , id ) :
		#print("setting current build #"+str(id))
		#print(len(self.builds))
		#print(build)
		if id >= 0 and len(self.builds) > id :
			view.settings().set( "haxe-build-id" , id )
			self.currentBuild = self.builds[id]
			view.set_status( "haxe-build" , self.currentBuild.to_string() )
		else:
			self.currentBuild = None
			view.set_status( "haxe-build" , "No build" )

		self.selectingBuild = False

	def run_build( self , view ) :
		view.run_command("save")
		view.set_status( "haxe-status" , "Building..." )
		err, comps, status = self.run_haxe( view )
		print( err )
		view.set_status( "haxe-status" , status )
		#if not "success" in status :
			#sublime.error_message( err )

	def run_haxe( self, view , offset = None ) :

		#print("running haxe")
		autocomplete = not offset is None
		build = self.currentBuild
		src = view.substr(sublime.Region(0, view.size()))
		fn = view.file_name()
		settings = view.settings()
		src_dir = os.path.dirname(fn)
		tdir = os.path.dirname(fn)
		temp = os.path.join( tdir , os.path.basename( fn ) + ".tmp" )

		self.errors = []

		pack = []
		for ps in packageLine.findall( src ) :
			pack = ps.split(".")
			for p in pack : 
				spl = os.path.split( src_dir )
				if( spl[1] == p ) :
					src_dir = spl[0]


		#find actual autocompletable char.
		if autocomplete : 
			userOffset = offset
			prev = src[offset-1]
			fragment = view.substr(sublime.Region(0,offset))
			
			if prev != "(" and prev != "." :
				prevDot = fragment.rfind(".")
				prevPar = fragment.rfind("(")
				offset = max(prevDot+1, prevPar+1)

			commas = len(view.substr(sublime.Region(offset,userOffset)).split(","))-1
			
			#tdir = os.path.join(os.path.dirname(fn), "_autocomplete")
			#temp = os.path.join(tdir, os.path.basename(fn))
			if not os.path.exists( tdir ):
				os.mkdir( tdir )
			
			if os.path.exists( fn ):
				# copy saved file to temp for future restoring
				shutil.copy2( fn , temp )
			
			# write current source to file
			f = codecs.open( fn , "wb" , "utf-8" )
			f.write( src )
			f.close()
		#f = self.savetotemp( tmp_path, src )

		#print( "Saved %s" % temp )
		#haxe -js dummy.js -cp c:\devx86\www\notime\js\haxe --display c:\devx86\www\notime\js\haxe\autocomplete\Test.hx@135

		args = []
		
		#buildArgs = view.window().settings
		if build is None:
			build = HaxeBuild()
			build.target = "js"

			folder = os.path.dirname(fn)
			folders = view.window().folders()
			for f in folders:
				if f in fn :
					folder = f

			build.output = os.path.join(folder,"dummy.js")

			cl = os.path.basename(fn)
			cl = cl.encode('ascii','ignore')
			cl = cl[0:cl.rfind(".")]
			main = pack[0:]
			main.extend( [ cl ] )
			build.main = ".".join( main )

			build.args.append( ("-cp" , src_dir) )
			#build.args.append( ("-main" , build.main ) )

			build.args.append( ("-js" , build.output ) )
			build.args.append( ("--no-output" , "-v" ) )
			
			self.currentBuild = build	
		
		args.extend( build.args )	
		
		if not autocomplete :
			args.append( ("-main" , build.main ) )
		else:
			args.append( ("--display", fn + "@" + str(offset) ) )
			args.append( ("--no-output" , "-v" ) )
			
		#elif build is None : 
			
		#else:
			#args.append( ( "-v" ) )

		cmd = ["haxe"]
		for a in args :
			cmd.extend( list(a) )
		
		print( " ".join(cmd))
		res, err = self.runcmd( cmd, "" )

		#print( "err: %s" % err )
		#print( "res: %s" % res )
		
		comps = []
		
		if autocomplete :
			#os.remove(temp)
			if os.path.exists( temp ) :
				shutil.copy2( temp , fn )
				os.remove( temp )
			else:
				# fn didn't exist in the first place, so we remove it
				os.remove( fn )
			
			status = "No autocompletion available"
		elif build.hxml is None :
			status = "Please create an hxml file"
			
		else :
			status = "Build success!"
			#status += "   "+build.to_string()
			#if not build.hxml is None :
			#	status += " (" + os.path.basename(build.hxml) + ")"
			
			print(status)
		
		try:
			tree = ElementTree.XML( err )

			if tree.tag == "type" :
				hint = tree.text.strip()
				types = hint.split(" -> ")
				ret = types.pop()
				msg = "";
				if commas >= len(types) :
					if commas == 0 :
						msg = ""
						#view.window().run_command("insert" , {'characters':")"})
						#comps.append((")",""))
					else:
						msg =  "Too many arguments."
				else :
					msg = ", ".join(types[commas:]) 

				if( msg ) :
					#msg =  " ( " + " , ".join( types ) + " ) : " + ret + "      " + msg
					status = msg
				
			
			for i in tree.getiterator("i"):
				name = i.get("n")
				sig = i.find("t").text
				doc = i.find("d").text #nothing to do
				if sig is not None :
					types = sig.split(" -> ")
					ret = types.pop()
						
					if( len(types) > 0 ) :
						cm = name + "("
						if len(types) == 1 and types[0] == "Void" :
							types = []
							cm += ")"
							comps.append( (name + "() : "+ ret, cm ) )
						else:
							comps.append( (name + "( " + " , ".join( types ) + " ) : "+ ret, cm ) )
					
					else : 
						comps.append( (name + " : "+ ret, name ))
				else :
					if re.match("^[A-Z]",name ) :
						comps.append( ( name + " [class]" , name ) )
					else :
						comps.append( ( name , name ) )
				#if doc is not None :
				#	comps.append(("[" + doc.strip() + "]" , doc ))

			if len(comps) > 0 :
				status = "Autocompleting..."
			
		except xml.parsers.expat.ExpatError as e:

			err = err.replace( temp , fn )
			err = re.sub("\(display(.*)\)","",err)

			lines = err.split("\n")
			l = lines[0].strip()
			
			if len(l) > 0:
				status = l

			#comps.append((" " , " "))
			#comps.append(("[" + status + "]"," " ))

			regions = []
			
			for infos in compilerOutput.findall(err) :
				infos = list(infos)
				f = infos.pop(0)
				l = int( infos.pop(0) )-1
				left = int( infos.pop(0) )
				right = infos.pop(0)
				if right != "" :
					right = int( right )
				else :
					right = left+1
				m = infos.pop(0)

				self.errors.append({
					"file" : f,
					"line" : l,
					"from" : left,
					"to" : right,
					"message" : m
				})
				
				if( f == fn ):
					status = m
					
				if not autocomplete :
					view.window().open_file(f+":"+str(l)+":"+str(right) , sublime.ENCODED_POSITION  )
				#if not autocomplete

			self.highlight_errors( view )

		
		return ( err, comps, status )

		#print( str(args) )
		#print( "res: %s" % res )
		#print( "err: %s" % err )
		#sublime.error_message("Hello!!!")
		#return comps
	

	def on_query_completions(self, view, prefix, locations):
		
		pos = locations[0]
		scopes = view.scope_name(pos).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes:
			return []
		
		#view.set_status( "haxe-status", "Autocompleting..." )
		#print("haxe completion")
		offset = pos - len(prefix)

		ret , comps , status = self.run_haxe( view , offset )
		view.set_status( "haxe-status", status )

		return comps
		
	
	def savetotemp( self, path, src ):
		f = tempfile.NamedTemporaryFile( delete=False )
		f.write( src )
		return f

	def runcmd( self, args, input=None ):
		try:
			p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=STARTUP_INFO)
			if isinstance(input, unicode):
				input = input.encode('utf-8')
			out, err = p.communicate(input=input)
			return (out.decode('utf-8') if out else '', err.decode('utf-8') if err else '')
		except (OSError, ValueError) as e:
			err = u'Error while running %s: %s' % (args[0], e)
			return ("", err)
