import sublime, sublime_plugin
import os, glob
import re, codecs
import time

import xml.etree.ElementTree as etree

from .HaxeHelper import runcmd, show_quick_panel
from .HaxeHelper import extractTag, extractTagName, haxeFileRegex
from .HaxeComplete import plugin_path

#
#	Haxe: Select project command
#
#  		this is for when there are multiple found project files
# 		and we don't want to guess wrong - the user must explicitly choose one.
#

class HaxeSelectProject(sublime_plugin.WindowCommand) :
	def run( self ) :
		project = HaxeProjects.active_project()
		if not project is None : 
			project.run_selected_build_target()
			project.project_file_list = project.find_possible_project_file()
			show_quick_panel( sublime.active_window(), project.project_file_list, project.on_selected_project )

class HaxeRunProjectBuild(sublime_plugin.WindowCommand) :
	def run( self ) :
		project = HaxeProjects.active_project()
		if not project is None : 
			self.window.run_command("save_all")
			project.run_selected_build_target()

class HaxeChooseBuildTarget(sublime_plugin.WindowCommand) :
	def run( self ) :
		project = HaxeProjects.active_project()
		if not project is None : 
			project.get_build_targets(True)		


#
#	Haxe project file helper
#
#		Stores the current project xml nodes for xml based projects
#		and determines what project configuration to load based on the file contents
#
#
#	The process is as follows :
#		> Try to ascertain a project type from known types, using find_possible_project_file
#		> If it finds 0, it will assume straight haxe and generate a hxml for you. 
#		  If it finds > 1, it will display a popup to select the correct project file
#		  If it finds 1, it will continue to try and guess based on the project type.
#
#		> When guessing, it loads the settings files from ./ProjectSettings/ and checks:
#		  Does the extension of the project file match the project type? If so, assume that it is that type
#
#		> Once a project type is determined by guessing (or selecting), and this is a nme/openfl/lime based 
#		  project the project xml nodes (except <haxelib/>) are stored for general use, 
#		  haxelibs are read from the haxelib run lime display projectfile cpp command. 
#		  This ensures that all included haxelibs from all possible paths are included.
#		
#		> haxelibs, classpaths, defines are stored in the project info
#
#	    > ready for user to select a build type, or optionally automatically show a select build list
#

active_projects = {}

class HaxeProjects() :

	def __init__( self ):		
		print(">>> New haxe project reporting in")
		self.build_info_cache = None
		self.haxelib_cache = None
		self.selected_project = None
		self.selected_build = None
		self.project = None
		self.settings = None

#
# Called from anywhere to get the window project instance, if any
#
	@staticmethod
	def active_project():

		project = None
		#first we have to see if there is a loaded project up in this window
		print("> check for existing project session on window")
		sublime_proj = sublime.active_window().project_data()
		

		#if there is, we can fetch it from the cache of active projects
		if "project" in sublime_proj:
			project_file = sublime_proj["project"]
			print("> found project in window, running with " + project_file)
			print(active_projects)
			if not project_file in active_projects:
				print("> project not found, reloading data")
				project = HaxeProjects._create_project_instance(project_file)				
			else:
				print("> project found ok")
				project = active_projects[project_file]

		#otherwise we need a new project instance
		else:
			print("> no active project found in the window")
			project = HaxeProjects._create_project_instance()

		sublime_proj["project"] = project.selected_project
		sublime.active_window().set_project_data( sublime_proj )

		return project
#
# Called from this class to create project instances
#
	@staticmethod
	def _create_project_instance(project_file=None):

		theproject = HaxeProjects()

		#try and find project files in the folder
		if project_file is None:
			print("> find possible project files")
			theproject.find_possible_project_file()
		else:
			print("> using existing project file " + project_file)
			theproject.selected_project = project_file

		#if there is an automatically selected one,
		#we can progress to attempting to guess and parse it
		print("> Did we find a single project to use?")
		if(theproject.selected_project != None):
			print("> YES, found, " + theproject.selected_project )
			active_projects[theproject.selected_project] = theproject		
			print("> continuing to load project" )	
			project = theproject.attempt_load_project_file()
			guess = theproject.best_guess()
			print("> project : " + str(project))
			print("> guess : " + guess)
			return theproject	
		else:
			print("> NO, no discernable project, here")
			del theproject

		return
		

	@staticmethod
	def determine_type():
				
		project = HaxeProjects.active_project()

		if project != None:			
			print("> further project data loading...")			
			project.post_project_select()
		else:
			print("> no automatically loadable project found. use the command palette.")

		return

		

		#if there is an automatically selected one,
		#we can progress to attempting to guess and parse it
		print("> check for silver bullet, project found?")
		if(theproject.selected_project != None):
			if not "project" in sublime_proj:
				print("> YES, found, no active project, attempting to load!")
				project = theproject.attempt_load_project_file()
				guess = theproject.best_guess()
				print("> project : " + str(project))
				print("> guess : " + guess)
				if project != None:
					if(guess != ''):
						print("> project selected ok, performing post select step")
						#now we can try and get the list of libraries and such 
						theproject.post_project_select()
					else:
						print("> guess was blank, assuming it's straight haxe")
			else:
				print(">Project loaded. Doing nothing for now.")
		else:

			print("No suitable project files")
			sublie.status_message("No suitable haxe project files found")

#
# Search the open folders for any possible files to use as a project
#
	def best_guess(self):
		guess = ''
		#load the possible project setting types
		project_settings_list = self.load_project_settings()
		#lets fine ours by the extension, and the current project
		for project_type in project_settings_list:
			ext = project_type.get("extension")

			if not ext is None:
				if self.project['type'] == ext:
					guess = project_type.get("name")
					self.settings = project_type

		self.guess = guess
		return guess

#
# Called when the project select dialog picks a file instead
#
	def on_selected_project(self,index):
		self.selected_project = theproject.project_file_list[index]
		self.attempt_load_project_file()
		self.post_project_select()

#
# Called if this is a openfl/nme/lime based project, and should go for additional info
#
	def post_project_select(self):
		if self.guess != '':
			print("> post project selection, valid build project")
			print("> get build info")
			self.get_build_info()
			print("> get build targets")
			self.get_build_targets()
		else:
			print("> handling different project typeee")

#
# Search the open folders for any possible files to use as a project
#
	def find_possible_project_file(self):
		
		project_types = ('*.xml', '*.nmml', '*.hxml')

		folders = sublime.active_window().folders()
		possible_project_files = []

		for file_type in project_types:
			possible_project_files.extend( glob.glob( os.path.join(folders[0],file_type) ) )

		count = len(possible_project_files)
		self.project_file_list = possible_project_files

		#Too cold
		if(count == 0):
			self.selected_project = None
			sublime.active_window().active_view().set_status("haxe-build","No suitable haxe project found (" + " ".join(project_types) + ")")
		#Too hot
		elif(count > 1):
			self.selected_project = None
			sublime.active_window().active_view().set_status("haxe-build","Multiple Projects Found, use Haxe: Select Project File")			
		#Just right
		else:
			self.selected_project = possible_project_files[0]
			return [self.selected_project]

		return possible_project_files

#
# Handle the possible types of projects based 
#

	def attempt_load_project_file(self):

		print("attempt_load_project_file")

		fileinfo = self.selected_project.split(os.extsep, 1)
		raw_ext = os.path.splitext(self.selected_project)[1].lower()
		ext = fileinfo[1].lower()
		filename = os.path.basename(fileinfo[0])

		if raw_ext == '.xml' or raw_ext == '.nmml':
			self.project = self.parse_xml_project(self.selected_project, filename, ext)
		else:
			self.project = self.parse_hxml_project(self.selected_project, filename, ext)

		return self.project

#
# Load possible configurations from the ProjectSettings
#
	def load_project_settings(self):		
		print("haxe : Looking for settings files in " + plugin_path + "/ProjectSettings")
		#work out the project file path from the plugin location, so it isn't harcoded
		project_settings_path = os.path.join(plugin_path,"ProjectSettings")
		#fetch the list of files from the folder
		list_of_setting_paths = glob.glob( os.path.join(project_settings_path,"*.sublime-settings") )
		#strip the file path and just keep the basename, because sublime settings wants a base name
		list_of_setting_paths = [os.path.basename(setting_path) for setting_path in list_of_setting_paths]
		
		#now we read each of these, storing them into the local settings
		project_settings = []
		for setting_file in list_of_setting_paths:
			project_settings.append( sublime.load_settings(setting_file) )
	
		return project_settings

#
# Runs a build using the specified build option
#
	def run_selected_build_target(self):
		if(self.project == None):
			return 

		if(self.selected_build == None):
			self.get_build_targets()

		build_command = self.settings.get("run")
		build_targets = self.settings.get('build_targets')
		build_args = build_targets[self.selected_build]

		for arg in build_args:			
			build_command.append(arg)
			if arg == "build" or arg == "test" or arg == "update" or arg == "run":
				build_command.append(self.selected_project)

		sublime.status_message("Running : " + str(build_command))
		# out,err = runcmd( build_command )
		sublime.active_window().run_command("exec", {
            "cmd": build_command,
            "working_dir": self.project["path"],
            "file_regex": haxeFileRegex #"^([^:]*):([0-9]+): characters [0-9]+-([0-9]+) :.*$"
        })
		
#
# Return a project specific set of build options
#
	def get_build_targets(self, force=False):
		if(self.project == None):
			return 

		if(self.selected_build != None and force != True):
			return 

		targets_list = self.settings.get('build_targets')
		target_display_list = []
		for target in targets_list:
			target_display_list.append(target)

		target_display_list.sort(key=str.lower)
		self.target_display_list = target_display_list

		print("> No build target selected, showing target menu")

		show_quick_panel(sublime.active_window(),target_display_list,self.on_build_target_selected)

	def on_build_target_selected(self,index):
		if(index < 0):
			return

		self.selected_build = self.target_display_list[index];
		self.project["build"] = self.selected_build
		targets_list = self.settings.get('build_targets')
		build_command = targets_list[self.selected_build]
		print("> Build target selected - " + self.selected_build)


#
# Get the haxelib list for the project and store it 
#
	def get_build_info(self, force=None):

		if(self.build_info_cache != None and force == None):
			return self.build_info_cache

		get_build_info_cmd = self.settings.get('run');
		
		if(get_build_info_cmd == None):
			print("Haxe: Project: Project config for " + settings.get('name') + " has no \"run\" option.")
			sublime.status_message("Project config for " + settings.get('name') + " has no \"run\" option.")
			return

		get_build_info_cmd.append("display")
		get_build_info_cmd.append(self.selected_project)
		get_build_info_cmd.append("cpp")

		out,err = runcmd(get_build_info_cmd)		

		if len(err) != 0:
			print("Haxe: Project: Error in fetching build info")
			sublime.status_message("haxe-build","Error in fetching build info" + str(err))
			return
		else:
			lines = out.splitlines()
			print("haxe: Project: build info " + str(lines))
			self.build_info_cache = lines


		haxelibs = []
		defines = []
		classpaths = []

		for item in self.build_info_cache:
			space_pos = item.find(' ')
			info_type = item[0:space_pos]
			if info_type == "-lib":
				haxelibs.append( item.replace('-lib ', '') )
			if info_type == "-cp":
				classpaths.append( item.replace('-cp ', '') )
			if info_type == "-D":
				defines.append( item.replace('-D ', '') )

		self.project['haxelibs'] = haxelibs
		self.project['classpaths'] = classpaths
		self.project['defines'] = defines

		return self.build_info_cache

#
# Parse and store any found project into a easy to use structure.
#
	def parse_hxml_project(self,path,filename,ext):

		return {"type":ext, "file":filename}

#
# Parse and store any found project into an easy to use structure.
#
	def parse_xml_project(self,path,filename,ext):

		if(self.selected_project == None):
			sublime.active_window().active_view().set_status("haxe-build","No project file selected, cannot guess")
			return

		#make sure we start fresh
		project_xml = { "file":filename+"."+ext, "path": os.path.dirname(self.selected_project), "type":ext, "haxelibs":[], "defines":[], "classpaths":[] }

		#parse the xml file
		f = codecs.open( self.selected_project , "r+", "utf-8" , "ignore" )
		file_contents = f.read()
		tree = etree.fromstring(file_contents)
		
		#iterate
		for node in tree:
			#haxelibs are not parsed, they are requested
			#from the build tools due to the complexity of projects
			if node.tag != "haxelib" and node.tag != "source" and node.tag != "haxedef":
				project_xml[node.tag] = node.attrib

		return project_xml



