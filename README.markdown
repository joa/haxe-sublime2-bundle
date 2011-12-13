# Introduction
Basic haXe Bundle for [Sublime Text 2](http://www.sublimetext.com/2)

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

 - On my Ubuntu, the plugin seemed to complain about pyexpat. I had to link my local python2.6 to Sublime's lib directory:

        ln -s /usr/lib/python2.6 [Sublime dir]/lib/

 - On my Mac, SublimeCodeIntel conflicts with the plugin, hiding the completion list after pressing '.'. I'm using [Package Control](http://wbond.net/sublime_packages/package_control) to disable this plugin when I don't need it.

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
