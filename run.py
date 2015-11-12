#!/usr/bin/env python
"""
    This script is here merely for convenience.
"""
from subprocess import check_call, CalledProcessError
import sys
import os

try:

    files = sys.argv[1:]

    run_compiled = '-i' not in files
    if not run_compiled:
        files.remove('-i')

    if os.path.isfile('main-c') and run_compiled:
        check_call(['./main-c'] + files)
    elif not os.path.exists('pypy-4.0.0-src'):
        print("First, read the README.md, after that run setup.py")
        sys.exit(1)
    else:
        os.environ['PYTHONPATH'] = "pypy-4.0.0-src"
        check_call(['python', 'main.py'] + files)
except CalledProcessError as e:
    sys.exit(e.returncode)
