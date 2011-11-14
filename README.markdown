# Introduction
Basic haXe Bundle for Sublime Text 2(http://www.sublimetext.com/2)

# Installation
## Mac OSX
    cd /Users/<username>/Library/Application\ Support/Sublime\ Text\ 2/Packages
    git clone git://github.com/sagework/haxe-sublime2-bundle.git HaXe
## Linux
    cd ~/.config/sublime-text-2/Packages
    git clone git://github.com/sagework/haxe-sublime2-bundle.git HaXe
## Windows
    TODO
    
Restart Sublime Text 2

# Troubleshooting
On my Ubuntu, the plugin seemed to complain about pyexpat. I had to link my local python2.6 to Sublime's lib directory:

    ln -s /usr/lib/python2.6 [Sublime dir]/lib/

