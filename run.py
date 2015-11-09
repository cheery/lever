#!/usr/bin/env python
"""
    The pyllisp isn't mature enough to host its own compiler script.
    This script helps out to operate python-written compiler.
"""
from subprocess import check_call, CalledProcessError
import sys
import os

try:
    if not os.path.exists('pypy-2.6.0-src'):
        print("First, read the README.md, after that run setup.py")
        sys.exit(1)

    os.environ['PYTHONPATH'] = "pypy-2.6.0-src"

    files = sys.argv[1:]

    run_compiled = '-i' not in files
    if not run_compiled:
        files.remove('-i')

    check_call(['python', 'compile.py'] + files)
    lic_files = [name + '.lic' for name in files]

    if os.path.isfile('main-c') and run_compiled:
        check_call(['./main-c'] + lic_files)
    else:
        check_call(['python', 'main.py'] + lic_files)
except CalledProcessError as e:
    pass
