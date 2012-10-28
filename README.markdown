# Introduction
An Haxe Bundle for [Sublime Text 2](http://www.sublimetext.com/2)

# Features

 - **Syntax highlighting** for haxe sources, hxml build files and hss
 - **Haxe compiler completion**, code hints and error highlighting
 - **Package and classes discovery/completion** supporting hxml classpath (-cp) and haxelib libraries (-lib)
 - **NME completion, target selection and compilation**
 - Automatic generation of hxml files, multiple build/hxml management, and -lib autocompletion based on haxelib
 - Haxelib integration (haxelib install)
 - Code snippets, auto-import, Sublime build system integration
 - [Erazor](https://github.com/ciscoheat/erazor) and [HSS](http://ncannasse.fr/projects/hss) support
 
and more to come :)

# Installation

### Sublime Package Control
The bundle is available through [Package Control](http://wbond.net/sublime_packages/package_control)

### Mac OSX
    cd /Users/<username>/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
### Linux
    cd ~/.config/sublime-text-2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
### Windows
    (Using git bash http://code.google.com/p/msysgit/)
    cd /c/Users/<username>/AppData/Roaming/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe

Restart Sublime Text 2

# Usage

 - Open your project's directory (where the .hxml or .nmml resides) in Sublime Text, the build file should be detected automatically,
 - Create new types through the sidebar's context menu
 - Edit your classes (check the cool snippets, like 'prop'-Tab)
 - Completion is triggered either automatically by dot and colon keys, or manually by Ctrl+Space.
 - Open parenthesis and comma keys display haxe type hints in the status bar

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

### Targeting NME

[haxe NME](http://www.haxenme.org/) is based on a specific .nmml file (the .hxml is generated) which is supported by this bundle.

 - press **Ctrl+Shift+B** to select a NME target
 - press **Ctrl+Enter** to build and run (regular Sublime Text build system won't work)

# Reviews

[SublimeText Editor Video Tutorial](http://haxe.org/doc/videos/editors/Sublimetext)

[Haxe workflow with Sublime Text 2, Php & nme examples](http://www.aymericlamboley.fr/blog/haxe-workflow-with-sublime-text-2-php-and-nme-examples/)

[Haxe IDE Choices for Mac OS X](http://sambrick.wordpress.com/2012/03/23/haxe-ide-choices-for-mac/)