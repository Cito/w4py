#!/usr/bin/env python2

"""pystats.py


Reports stats for various aspects of Python source including:

  - number of files
  - number of bytes
  - number of lines
  - number of methods/functions
  - number of classes

You can think of this as a UNIX "wc" on steroids (that also works on any
Python platform).


USAGE

From the command line:

  > cd Webware
  > python bin/pystats.py
  > python bin/pystats.py -h
  > python bin/pystats.py -s


CAVEATS

PyStats doesn't count classes, functions and methods perfectly. It can be
fooled by multiline strings and such. But it's close enough to get an idea
and the odd ball cases don't happen frequently.

Webware includes some third party Python files, which you may or may not
believe should be counted as part of the stats.

Number of bytes is a little low on Windows where \r\n is counted just as \n.

The extensions accepted are hard coded to .py, .psp and .cgi.


MISC

To check the results of pystats, you can use these UNIX commands for comparison:
  > rm -rf WebKit/Cache
  > wc *.py */*.py */*/*.py */*/*.psp */*.cgi


FUTURE

Output numbers with commas.

Option for writing HTML results.

Both this utility and checksrc.py are in need of a ReadPyLines() function that
would be like readlines() but would bastardize the contents of multiline strings
to avoid misunderstandings concerning tabs, spaces, def's, class's etc.
See tabnanny in Py 2.0, it might have the answer or even reusable code.

Some of our code is in common with checksrc.py. One more similar program and it
might be time for an abstract class for these guys.

Provide command line option to change extensions.
"""


import os
import re
import sys


class Stats(dict):

    _statNames = 'files bytes lines funcs classes'.split()

    def __init__(self, data=None):
        if data:
            super(Stats, self).__init__(data)
        else:
            super(Stats, self).__init__()
            for name in self._statNames:
                self[name] = 0

    def __iadd__(self, other):
        for name in self._statNames:
            self[name] += other[name]
        return self

    def copy(self):
        """Return a real copy/duplicate of the receiver.

        This is needed because dict.copy() returns a dict.
        """
        return self.__class__(self)

    def write(self, file=sys.stdout):
        for name in self._statNames:
            file.write('%8d' % self[name])

    @classmethod
    def writeHeaders(cls, nameWidth, file=sys.stdout):
        file.write(' ' * nameWidth)
        for name in cls._statNames:
            file.write('%8s' % name)
        file.write('\n')


class StatsNode(object):

    classDefRE = re.compile(r'^[\t ]*class[\t ]+[\w]+[\t ]*[(:]{1,1}', re.MULTILINE)
    funcDefRE = re.compile(r'^[\t ]*def[\t ]+[\w]+[\t ]*\(', re.MULTILINE)

    def __init__(self, name):
        self._name = name
        self._subNodes = {}  # map directory names to StatsNodes
        self._stats = Stats()  # stats for files just in this dir (no subdirs)
        self._totalStats = None  # stats for all files, recursively in subdirs

    def name(self):
        return self._name

    def computeTotal(self):
        self._totalStats = self._stats.copy()
        for node in self._subNodes.values():
            node.computeTotal()
            self._totalStats += node._totalStats

    def processDir(self, dirName, extensions, recurse=True):
        exceptions = (os.curdir, os.pardir, '.git', '.hg', '.svn')
        names = os.listdir(dirName)
        for name in names:
            if not os.path.isdir(name):
                ext = os.path.splitext(name)[1]
                if ext in extensions:
                    self.processFile(os.path.join(dirName, name), ext)
        if recurse:
            for name in names:
                if name not in exceptions:
                    fullname = os.path.join(dirName, name)
                    if os.path.isdir(fullname):
                        node = self._subNodes[name] = StatsNode(name)
                        node.processDir(fullname, extensions)

    def processFile(self, pathname, ext=None):
        if ext is None:
            ext = os.path.splitext(pathname)[1]
        contents = open(pathname).read()
        stats = self._stats
        stats['bytes'] += len(contents)
        stats['lines'] += contents.count('\n')
        stats['funcs'] += len(self.funcDefRE.findall(contents))
        stats['classes'] += len(self.classDefRE.findall(contents))
        stats['files'] += 1

    def write(self, file=sys.stdout, recurse=True, indent=0, indenter='  '):
        if indent == 0:
            self._stats.writeHeaders(25, file)
        spacer = indenter * indent
        name = self._name.ljust(25-len(spacer))
        file.write(spacer + name)
        self._totalStats.write(file)
        file.write('\n')
        if recurse:
            indent += 1
            for key in sorted(self._subNodes):
                self._subNodes[key].write(file, recurse, indent, indenter)


class PyStats(object):


    ## Init ##

    def __init__(self):
        # Init some attrs
        self._rootNode = StatsNode('.')

        # Set default options
        self.setDirectory('.')
        self.setExtensions(['.py', '.psp', '.cgi'])
        self.setRecurse(True)
        self.setShowSummary(False)


    ## Options ##

    def directory(self):
        return self._directory

    def setDirectory(self, dir):
        """Set the directory that checking starts in."""
        self._directory = dir

    def extensions(self):
        return self._extensions

    def setExtensions(self, exts):
        self._extensions = exts

    def recurse(self):
        return self._recurse

    def setRecurse(self, flag):
        """Set whether or not to recurse into subdirectories."""
        self._recurse = flag

    def showSummary(self):
        return self._showSummary

    def setShowSummary(self, flag):
        self._showSummary = flag


    ## Command line use ##

    def usage(self):
        print '''Usage: %s [options] [startingDir]

    -h --help = help
    -r -R = recurse, do not recurse (default -r)
    -s -S = show summary, do not show summary (default -S)

    Examples:
    > python pystats.py
    > python pystats.py SomeDir
    > python pystats.py -R SomeDir''' % sys.argv[0]

    def main(self, args=sys.argv):
        if self.readArgs(args):
            self.run()

    def readArgs(self, args=sys.argv):
        for arg in args[1:]:
            if arg == '-h' or arg == '--help':
                self.usage()
                return False
            elif arg == '-r':
                self.setRecurse(True)
            elif arg == '-R':
                self.setRecurse(False)
            elif arg == '-s':
                self.setShowSummary(True)
            elif arg == '-S':
                self.setShowSummary(False)
            elif arg[0] == '-':
                self.usage()
                return False
            else:
                self.setDirectory(arg)
        return True


    ## Running ##

    def run(self, file=sys.stdout):
        self._rootNode.processDir(self._directory, self._extensions, self._recurse)
        self._rootNode.computeTotal()
        self.write(file)


    ## Writing ##

    def write(self, file=sys.stdout):
        recurse = not self._showSummary
        self._rootNode.write(file, recurse)


if __name__ == '__main__':
    PyStats().main()
