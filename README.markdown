# Introduction
An Haxe Bundle for [Sublime Text 2](http://www.sublimetext.com/2) and [Sublime Text 3](http://www.sublimetext.com/3)

# Features

 - **Syntax highlighting** for Haxe2 and Haxe3 sources and hxml build files
 - **Haxe compiler auto-completion**, code hints, smart snippets and error highlighting / navigation
 - **[NME](http://www.nme.io/), [openfl](https://github.com/openfl/openfl) and [Flambe](http://getflambe.com) support** with completion, target selection and compilation
 - **Package and classes discovery/suggestion** including classpath (-cp) and haxelib libraries (-lib)
 - **Multiple build management** and automatic generation of hxml files
 - **Haxelib integration** (install / remove / upgrade libs) with -lib autocompletion
 - Code snippets, auto-import, Sublime build system integration
 - **[HScript](http://code.google.com/p/hscript/)**, **[Erazor](https://github.com/ciscoheat/erazor)** and **[HSS](http://ncannasse.fr/projects/hss)** support
 
and more to come :)

# Installation

## Sublime Package Control

The most straight-forward way to install the bundle and to keep it up-to-date 
is through [Package Control](http://wbond.net/sublime_packages/package_control).

## Manual installation

If you want to develop on a forked repo, you can clone it into the *Packages* folder:

### Mac OSX

    cd ~/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone https://github.com/<fork author>/haxe-sublime-bundle.git Haxe

### Linux

    cd ~/.config/sublime-text-2/Packages
    git clone https://github.com/<fork author>/haxe-sublime-bundle.git Haxe

### Windows

Using [git bash](http://code.google.com/p/msysgit/)

    cd /c/Users/<username>/AppData/Roaming/Sublime\ Text\ 2/Packages
    git clone https://github.com/<fork author>/haxe-sublime-bundle.git Haxe

Restart Sublime Text.

## Sublime Text 3

See [How to install Package Control on Sublime Text 3](http://wbond.net/sublime_packages/package_control/installation#ST3).
For manual installation, the folders should be `sublime-text-3` (Linux) or `Sublime\ Text\ 3` (Windows, Mac OSX).

# Usage

 - Open your project directory (where the .hxml or .nmml resides) in Sublime Text, the build file should be detected automatically,
 - Create new types through the sidebar's context menu
 - Edit your classes (check the cool snippets, like 'prop'-Tab)
 - Open parenthesis and comma keys display Haxe type hints in the status bar and inserts smart snippets

### Shortcuts

 - Press **Ctrl+Shift+B** to either select among multiple builds, automatically generate an hxml file if none exist, or edit the build file if only one build exists
 - Press **Ctrl+Enter** to run the current/selected build
 - Press **Ctrl+I** on a qualified class name to shorten it and generate the import statement. Safe to use if the class is already imported.
 - Press **Ctrl+Shift+H** and then : 
      - **Ctrl+Shift+C** to create a new class,
      - **Ctrl+Shift+I** to create a new interface,
      - **Ctrl+Shift+E** to create a new enum,
      - **Ctrl+Shift+T** to create a new typedef
 - Press **Ctrl+Shift+F1** to show documentation on cursor (when previously autocompleted) 

### Settings

 - `haxe_path` : Full path to the Haxe compiler, if not already in your PATH ("/usr/bin/haxe" or "C:\Program Files\Haxe\haxe.exe")
 - `haxe_library_path` : Full path to the standard lib, overriding HAXE_LIBRARY_PATH
 - `haxelib_path` : Full path to Haxelib, if not already in your PATH ("/usr/bin/haxelib" or "C:\Program Files\Haxe\haxelib.exe")
 - `haxe_build_server_mode` (`true` by default) : Uses [compilation server](http://haxe.org/manual/completion#compilation-cache-server) for building. The server is always used for completion, and may be restarted if needed through the command palette.
 - `haxe_smart_snippets` (`true` by default) : Inserts smart snippets based on compiler hints after `(` and `,`

### Targeting NME/openfl

[Haxe NME](http://www.haxenme.org/) is based on a specific `.nmml` file (the `.hxml` is generated) which is supported by this bundle.

To target [openfl](https://github.com/openfl/openfl), use `.xml` instead, like `project.xml`.

 - press **Ctrl+Shift+B** to select a NME target
 - press **Ctrl+Enter** to build and run (regular Sublime Text build system won't work)

### Troubleshooting

 - You'll need a working installation of Haxe (`haxe` and `haxelib`): start by trying to compile your project directly through a terminal.
 - Open the Sublime Text Console (in View menu) to see what's going on.
 - Don't hesitate to [open an issue](https://github.com/clemos/haxe-sublime-bundle/issues) in case anything goes wrong.
 
### Tips & tricks

As this bundle displays code hinting for method calls in the “status bar”, 
you may find it useful to [increase its font-size](http://superuser.com/questions/469161/increase-the-font-size-on-sublime-text-2-status-bar).

# Reviews

[SublimeText Editor Video Tutorial](http://haxe.org/doc/videos/editors/Sublimetext)

[Haxe workflow with Sublime Text 2, Php & nme examples](http://www.aymericlamboley.fr/blog/haxe-workflow-with-sublime-text-2-php-and-nme-examples/)

[Haxe IDE Choices for Mac OS X](http://sambrick.wordpress.com/2012/03/23/haxe-ide-choices-for-mac/)
