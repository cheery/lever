#!/usr/bin/env python2
"""
    This script runs lever interpreted.

    Meant for debugging lever.
"""
from glob import glob

from subprocess import check_call, CalledProcessError
import sys
import os
import platform

lever_path = os.path.dirname(os.path.realpath(sys.argv[0]))
try:
    pythonpath = sorted(glob("pypy-*-src"))[-1]
except IndexError as _:
    print("First, read the README.md, after that run setup.py")
    sys.exit(1)
main_py_path = os.path.join(lever_path, 'main.py')
os.environ['PYTHONPATH'] = pythonpath
try:
    check_call(['python', main_py_path] + sys.argv[1:])
except CalledProcessError as e:
    sys.exit(e.returncode)
