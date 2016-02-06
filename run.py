#!/usr/bin/env python
"""
    This script is here merely for convenience.
"""
from subprocess import check_call, CalledProcessError
import sys
import os
import platform

try:
    lever_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    files = sys.argv[1:]
    pythonpath = os.path.join(lever_path, 'pypy-4.0.1-src')
    main_py_path = os.path.join(lever_path, 'main.py')
    main_path = os.path.abspath(os.path.join(lever_path, 'lever'))
    if platform.system() == "Windows":
        main_path += ".exe"

    run_compiled = '-i' not in files
    if not run_compiled:
        files.remove('-i')

    os.environ['LEVER_PATH'] = lever_path
    if os.path.isfile(main_path) and run_compiled:
        check_call([main_path] + files)
    elif not os.path.exists(pythonpath):
        print("First, read the README.md, after that run setup.py")
        sys.exit(1)
    else:
        os.environ['PYTHONPATH'] = pythonpath
        check_call(['python', main_py_path] + files)
except CalledProcessError as e:
    sys.exit(e.returncode)
