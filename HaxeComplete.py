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

class HaxeComplete( sublime_plugin.EventListener ):
	def on_query_completions(self, view, prefix, locations):
		pos = locations[0]
		scopes = view.scope_name(pos).split()
		#sublime.status_message( scopes[0] )
		if 'source.haxe.2' not in scopes:
			return []

		offset = pos - len(prefix)
		src = view.substr(sublime.Region(0, view.size()))
		fn = view.file_name()
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

		args = [ "haxe", "-js", "dummy.js", "-cp", src_dir, "--display", temp + "@" + str(offset) ]
		res, err = self.runcmd( args, "" )

		#print( "err: %s" % err )

		comps = []
		try:
			tree = ElementTree.XML( err )
			for i in tree.getiterator("i"):
				name = i.get("n")
				sig = i.find("t").text
				comps.append( (name + "(" + sig + ")", name) )
		except xml.parsers.expat.ExpatError as e:
			sublime.status_message( err )

		#print( str(args) )
		#print( "res: %s" % res )
		#print( "err: %s" % err )
		#sublime.error_message("Hello!!!")
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
