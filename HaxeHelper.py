import sys, sublime, sublime_plugin
import subprocess, time
import os, signal

from subprocess import Popen, PIPE
from datetime import datetime

import threading
import traceback
import shlex
 

try:
  STARTUP_INFO = subprocess.STARTUPINFO()
  STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
  STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
    STARTUP_INFO = None
    
try :
    stexec = __import__("exec")
    ExecCommand = stexec.ExecCommand
    AsyncProcess = stexec.AsyncProcess 
except ImportError as e :
    import Default
    stexec = getattr( Default , "exec" )
    ExecCommand = stexec.ExecCommand
    AsyncProcess = stexec.AsyncProcess
    unicode = str #dirty...

def runcmd( args, input=None ):
    try:
        if int(sublime.version()) >= 3000 :
            p = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=STARTUP_INFO)
        else:
            p = Popen([a.encode(sys.getfilesystemencoding()) for a in args], stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=STARTUP_INFO)
        if isinstance(input, unicode) :
            input = input.encode('utf-8')
        out, err = p.communicate(input=input)
        return (out.decode('utf-8') if out else '', err.decode('utf-8') if err else '')
    except (OSError, ValueError) as e:
        err = u'Error while running %s: %s' % (args[0], e)
        if int(sublime.version()) >= 3000 :
            return ("",err)
        else:
            return ("", err.decode('utf-8'))

def show_quick_panel(_window, options, done, flags=0, sel_index=0, on_highlighted=None):
    sublime.set_timeout(lambda: _window.show_quick_panel(options, done, flags, sel_index, on_highlighted), 10)


 
class runcmd_async(object):
    """
    Enables to run subprocess commands in a different thread with TIMEOUT option.
 
    Based on jcollado's solution:
    http://stackoverflow.com/questions/1191374/subprocess-with-timeout/4825933#4825933
    """
    command = None
    process = None
    status = None
    output, error = '', ''
 
    def __init__(self, command):
        if isinstance(command, str):
            command = shlex.split(command)
        self.command = command
 
    def run(self, timeout=None, **kwargs):
        """ Run a command then return: (status, output, error). """
        def target(**kwargs):
            try:
                self.process = subprocess.Popen(self.command, **kwargs)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode
            except:
                self.error = traceback.format_exc()
                self.status = -1
        # default stdout and stderr
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
        # thread
        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
        return self.status, self.output, self.error

