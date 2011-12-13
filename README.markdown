# Introduction
Basic haXe Bundle for [Sublime Text 2](http://www.sublimetext.com/2)

# Features

 - **Syntax highlighting** for haxe sources, hxml build files and hss
 - **HaXe compiler completion**, code hints and error highlighting
 - **Package and classes discovery/completion** supporting hxml classpath (-cp) and haxelib libraries (-lib)
 - Automatic generation of hxml files, multiple build/hxml management, and -lib autocompletion based on haxelib
 - Code snippets, auto-import, NME support, Sublime build system integration
 
and more to come :)

# Installation
## Mac OSX
    cd /Users/<username>/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
## Linux
    cd ~/.config/sublime-text-2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
## Windows
    (Using git bash http://code.google.com/p/msysgit/)
    cd /c/Users/<username>/AppData/Roaming/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe

Restart Sublime Text 2

# Troubleshooting

On Ubuntu, you'll probably need to install package python2.6

    sudo apt-get install python2.6

SublimeCodeIntel seems to conflict with the plugin, hiding the completion list after pressing '.'. You can use [Package Control](http://wbond.net/sublime_packages/package_control) to disable this plugin when I don't need it.

# Usage

 - open your project's directory (where the .hxml or .nmml resides) in Sublime Text, the build file should be detected automatically,
 - edit your classes (check the cool snippets, like 'prop'-Tab)
 - press Ctrl+Enter to build
 - open the console (View > Show Console) for more details about errors & stuff

# Targeting NME

[haxe NME](http://www.haxenme.org/) is based on a specific .nmml file (the .hxml is generated). **Code completion works automatically**, as a CPP target. 
If you really need Flash API completion you can create a dummy .hxml with:

    -swf dummy.swf 
    -lib nme 
    -cp src

To build your project you still have to call *nme* from the command line.

# Generator(s)

 - select or just place your cursor on a qualified class name and press Ctrl+I to shorten it and generate the import statement. Safe to use if the class is already imported.
