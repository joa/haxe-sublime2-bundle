# Introduction
An Haxe Bundle for [Sublime Text 2](http://www.sublimetext.com/2)

# Features

 - **Syntax highlighting** for Haxe sources, hxml build files and hss
 - **Haxe compiler completion**, code hints and error highlighting
 - **Package and classes discovery/completion** supporting hxml classpath (-cp) and haxelib libraries (-lib)
 - **NME completion, target selection and compilation**
 - **Multiple build/hxml management** and automatic generation of hxml files
 - **Haxelib integration** (install / remove libs) with -lib autocompletion
 - Code snippets, auto-import, Sublime build system integration
 - **[HScript](http://code.google.com/p/hscript/)**, **[Erazor](https://github.com/ciscoheat/erazor)** and **[HSS](http://ncannasse.fr/projects/hss)** support
 
and more to come :)

# Installation

## Sublime Package Control

The most straight-forward way to install the bundle and to keep it up-to-date 
is through [Package Control](http://wbond.net/sublime_packages/package_control).

## Manual installation

### Mac OSX

    cd ~/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git Haxe

### Linux

    cd ~/.config/sublime-text-2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git Haxe

### Windows

Using git bash http://code.google.com/p/msysgit/

    cd /c/Users/<username>/AppData/Roaming/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git Haxe

Restart Sublime Text 2

# Usage

 - Open your project's directory (where the .hxml or .nmml resides) in Sublime Text, the build file should be detected automatically,
 - Create new types through the sidebar's context menu
 - Edit your classes (check the cool snippets, like 'prop'-Tab)
 - Completion is triggered either automatically by dot and colon keys, or manually by Ctrl+Space.
 - Open parenthesis and comma keys display Haxe type hints in the status bar

### Shortcuts

 - Press **Ctrl+Shift+B** to either automatically generate an hxml file if none exist, edit the build file if only one build exists or select among multiple builds (--next)
 - Press **Ctrl+Enter** to run the current/selected build
 - Press **Ctrl+I** on a qualified class name to shorten it and generate the import statement. Safe to use if the class is already imported.
 - Press **Ctrl+Shift+L** to install a library via haxelib
 - Press **Ctrl+Shift+H** and then : 
      - **Ctrl+Shift+C** to create a new class,
      - **Ctrl+Shift+I** to create a new interface,
      - **Ctrl+Shift+E** to create a new enum,
      - **Ctrl+Shift+T** to create a new typedef

### Settings

 - `haxe_path` : Full path to the Haxe compiler, if not already in your PATH ("/usr/bin/haxe" or "C:\Program Files\Haxe\haxe.exe")
 - `haxe_library_path` : Full path to the standard lib, overriding HAXE_LIBRARY_PATH
 - `haxe_build_server_mode` (`true` by default) : Uses [compilation server](http://haxe.org/manual/completion#compilation-cache-server) for building. The server is always used for completion, and may be restarted if needed through the command palette.

### Targeting NME

[Haxe NME](http://www.haxenme.org/) is based on a specific .nmml file (the .hxml is generated) which is supported by this bundle.

 - press **Ctrl+Shift+B** to select a NME target
 - press **Ctrl+Enter** to build and run (regular Sublime Text build system won't work)

### Tips & tricks

As this bundle displays code hinting for method calls in the “status bar”, 
you may find it useful to [increase its font-size](http://superuser.com/questions/469161/increase-the-font-size-on-sublime-text-2-status-bar).

# Reviews

[SublimeText Editor Video Tutorial](http://haxe.org/doc/videos/editors/Sublimetext)

[Haxe workflow with Sublime Text 2, Php & nme examples](http://www.aymericlamboley.fr/blog/haxe-workflow-with-sublime-text-2-php-and-nme-examples/)

[Haxe IDE Choices for Mac OS X](http://sambrick.wordpress.com/2012/03/23/haxe-ide-choices-for-mac/)