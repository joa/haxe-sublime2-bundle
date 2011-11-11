import sublime, sublime_plugin
import subprocess
import tempfile
import os
import xml.parsers.expat
from xml.etree import ElementTree
from subprocess import Popen, PIPE

try:
    STARTUP_INFO = subprocess.STARTUPINFO()
    STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
	STARTUP_INFO = None

class CloseParenthesis( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		self.view.run_command('auto_complete', {
			'disable_auto_insert': True,
			'completions' : [
				{"trigger" : "aaaa", "content" : "aaaa"},
				{"trigger" : "bbbb", "content" : "bbbb"}
			]
		})


	
class HaxeHint( sublime_plugin.TextCommand ):
	def run( self , edit ) :
		complete = HaxeComplete()
		view = self.view

		sel = view.sel()
		for r in sel :
			ret , comps , status = complete.run_haxe( self.view , r.end() )
			sublime.status_message( status )
			if( len(comps) > 0 ) :
				view.run_command('auto_complete', {'disable_auto_insert': True})

		
		

class HaxeComplete( sublime_plugin.EventListener ):

	#folder = ""
	#buildArgs = []

	def on_activated( self , view ) :
		return self.extract_build_args( view)

	def extract_build_args( self , view ) :
		print("extracting build args")
		scopes = view.scope_name(view.sel()[0].end()).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes:
			return []

		fn = view.file_name()
		settings = view.settings()

		folder = os.path.dirname(fn)
		
		folders = view.window().folders()
		for f in folders:
			if f in fn :
				folder = f

		settings.set("haxe-complete-folder", folder)

		buildArgs = []
		build = os.path.join( folder , "build.hxml" );
		buildPath = os.path.dirname(build);
		if os.path.exists( build ) :
			# print("build file exists")
			f = open( build , "r+" )
			while 1:
				l = f.readline() 
				if not l: 
					break;
				l = l.strip()
				if l.startswith("-lib ") or l.startswith("-D ") :
					for a in l.split(" ") :
						buildArgs.append( a )
				if l.startswith("-cp "):
					cp = l.split(" ")
					buildArgs.append( cp.pop(0) )
					classpath = " ".join( cp )
					buildArgs.append( os.path.join( buildPath , classpath ) )
		
		settings.set("haxe-complete-build-args", buildArgs)

		#print( self.buildArgs )

		

	def run_haxe( self, view , offset ) :

		print("running haxe")

		src = view.substr(sublime.Region(0, view.size()))
		fn = view.file_name()
		settings = view.settings()

		#folders = view.window().folders()
		#folder = os.path.dirname(fn)
		#for f in folders:
		#	if f in fn :
		#		folder = f
		
		#find actual autocompletable char.
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
		tdir = os.path.dirname(fn)
		temp = os.path.join(tdir, "AutoComplete_.hx")
		if not os.path.exists( tdir ):
			os.mkdir( tdir )
		f = open( temp, "wb" )
		f.write( src )
		f.close()
		#f = self.savetotemp( tmp_path, src )

		src_dir = os.path.dirname(fn)

		#print( "Saved %s" % temp )
		#haxe -js dummy.js -cp c:\devx86\www\notime\js\haxe --display c:\devx86\www\notime\js\haxe\autocomplete\Test.hx@135

		args = ["haxe" , "-js" , "dummy.js"]
		
		#buildArgs = view.window().settings
		if settings.has("haxe-complete-build-args"):
			args.extend( settings.get('haxe-complete-build-args') )	

		#print(args)
		#args = [ "haxe", "-js", "dummy.js", "-cp", src_dir, "--display", temp + "@" + str(offset) ]
		#args = [ "haxe",src_dir+"/../build.hxml" , "--display", temp + "@" + str(offset) ]
		args.append("-cp")
		args.append( src_dir )
		
		args.append("--display")
		args.append(temp + "@" + str(offset))

		#print(" ".join(args))
		res, err = self.runcmd( args, "" )

		#print( "err: %s" % err )
		#print( "res: %s" % res )
		
		comps = []
		status = ""

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
						msg =  "Too many arguments "
				else :
					msg = "Expecting " + types[commas] 

				if( msg ) :
					msg =  " ( " + " , ".join( types ) + " ) : " + ret + "      " + msg
				
				print( msg )
				status = msg
			
			#print( err )

			for i in tree.getiterator("i"):
				name = i.get("n")
				sig = i.find("t").text
				if sig is not None :
					types = sig.split(" -> ")
					ret = types.pop()
						
					if( len(types) > 0 ) :
						comps.append( (name + "( " + " , ".join( types ) + " ) : "+ ret, name) )
					else : 
						comps.append( (name + " : "+ ret, name ))
				else :
					comps.append( (name , name) )
			
		except xml.parsers.expat.ExpatError as e:
			status = err.split("\n")[0]
			status = status.replace( temp , fn )
			#status = status.replace( self.folder , "" )
			status = status.strip()

			print(err)
			

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

		offset = pos - len(prefix)

		ret , comps , status = self.run_haxe( view , offset )
		sublime.status_message( status )
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
