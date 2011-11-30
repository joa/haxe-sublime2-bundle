# Introduction
Basic haXe Bundle for Sublime Text 2 (http://www.sublimetext.com/2)

# Installation
## Mac OSX
    cd /Users/<username>/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
## Linux
    cd ~/.config/sublime-text-2/Packages
    git clone git://github.com/<fork author>/haxe-sublime2-bundle.git HaXe
## Windows
    TODO

Restart Sublime Text 2

# Troubleshooting

 - On my Ubuntu, the plugin seemed to complain about pyexpat. I had to link my local python2.6 to Sublime's lib directory:

        ln -s /usr/lib/python2.6 [Sublime dir]/lib/

 - On my Mac, SublimeCodeIntel conflicts with the plugin, hiding the completion list after pressing '.'.

# Usage

 - open your project's build file (.hxml) to configure code completion
 - edit your classes (check the cool snippets, like 'prop'-Tab)
 - press Ctrl+Enter to build
 - open the console (View > Show Console) for more details about errors & stuff

# Generator(s)

 - select or just place your cursor on a qualified class name and press Ctrl+I to generate the import statement

