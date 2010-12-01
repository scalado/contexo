Installation prerequisites
==========================
Python
------
Contexo II requires Python version 2.5 or later but not the 3.x series.
Problems have been encountered with the Python 2.7 series, please do not use these releases until noted otherwise.
http://www.python.org/download/

pysvn
-----
A python binding to svn. You should get the version matching the version of
your python as well as the svn version your other svn clients use.
The versions should agree up to the first minor number.
E.g. if you use Windows, svn (or tortoisesvn) version 1.6.x and python 2.6, get
py26-pysvn-svn165-1.7.1-1233.exe.
http://pysvn.tigris.org/project_downloads.html

A compiler
----------
Some examples are Gcc, Visual Studio Express (cl.exe), RealView.
Without a compiler Contexo cannot build projects!

(only on windows) pywin32
-------------------------
Python binding to win32api. Its version should match your Python.
http://sourceforge.net/projects/pywin32/files/

(optional) git support
----------------------

Contexo version number
======================
Following the 0.8.0 release, the Contexo version number is of the format x.y.z where x.y.z are integers:

x = should be zero.
y = increment means change in the build process.
z = increment means service release, bugfix or performance updates but no change in the build process.

