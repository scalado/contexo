Installation prerequisites
==========================
Python
------
Contexo II requires a Python interpreter of version 2.5.x or 2.6.x.
For Windows 64-bit users, a 32-bit version of Python is required.
Mac 64-bit users needs to rebuild pysvn from source to enable pysvn to work correctly.
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

Vista / Windows 7 Notes
-----------------------
To install on Windows 7 and Vista, navigate with explorer to the folder where contexo has been extracted. Right click on install.bat and select "Run as", and further select Administrator.
The installer require writing to some system wide registry keys which Windows UAC does not allow for users.

(optional) git support
----------------------

Contexo version number
======================
Following the 0.8.0 release, the Contexo version number is of the format x.y.z where x.y.z are integers:

x = should be zero.
y = increment means change in the build process.
z = increment means service release, bugfix or performance updates but no change in the build process.

