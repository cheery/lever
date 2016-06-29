#!/usr/bin/env python2
"""
    This script should help setting up environment for lever.
    Run it without arguments, and it just setups the environment.
    Run it with 'compile' -argument, eg. "./setup.py compile" and it compiles.

    Compiling takes some time to finish.
"""
from subprocess import call, check_call
from urllib import urlopen
from StringIO import StringIO
from zipfile import ZipFile
import platform
import re
import sys
import glob
import os

pypy_src_url = 'https://bitbucket.org/pypy/pypy/downloads/pypy2-v5.3.1-src'
pypy_src_dir = 'pypy2-v5.3.1-src'

command_depends = "pkg-config gcc make bzip2".split(' ')
library_depends = "libffi zlib sqlite3 ncurses expat libssl".split(' ')

devnull = open(os.devnull, 'w')
def linux_main():
    for cmd in command_depends:
        if call([cmd, '--version'], stdout=devnull, stderr=devnull) != 0:
            return linux_troubleshoot(cmd)
    for dependency in library_depends:
        if call(['pkg-config', '--exists', dependency]) != 0:
            return linux_troubleshoot(dependency)
    linux_download_and_extract(pypy_src_dir, pypy_src_url + '.tar.bz2')
    compiling_commands()

def windows_main():
    if not os.path.exists(pypy_src_dir):
        url = urlopen(pypy_src_url + '.zip')
        zipfile = ZipFile(StringIO(url.read()))
        zipfile.extractall()
        print("Note that windows support for lever is nonstardard low-quality.")
        print("Experienced computer operator is required after this point.")
    compiling_commands()

def compiling_commands():
    os.environ['PYTHONPATH'] = pypy_src_dir
    rpython_bin = os.path.join(pypy_src_dir, 'rpython', 'bin', 'rpython')
    if len(sys.argv) > 1 and sys.argv[1] == 'compile':
        check_call(['python', rpython_bin] + "--translation-jit --gc=incminimark --opt=2 runtime/goal_standalone.py".split(' '))
        compile_libraries()
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-nojit':
        check_call(['python', rpython_bin] + "--gc=incminimark runtime/goal_standalone.py".split(' '))
        compile_libraries()
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-lib':
        compile_libraries()
#    if len(sys.argv) > 1 and sys.argv[1] == 'compile-stm':
#        os.environ['PYTHONPATH'] = "pypy-stm"
#        check_call("python pypy-stm/rpython/bin/rpython --translation-jit --opt=2 --stm main.py".split(' '))

def compile_libraries():
    from compiler import compile
    print("Compiling libraries for lever")
    for dirname, subdirs, files in os.walk("lib"):
        for name in files:
            if name.endswith(".lc"):
                lc_name = os.path.join(dirname, name)
                cb_name = re.sub(".lc$", ".lc.cb", lc_name)
                try:
                    compile.compile_file(cb_name, lc_name)
                except Exception as e:
                    print("{}:{}".format(lc_name, e))

#--continuation --gc=incminimark --gcrootfinder=shadowstack --opt=2

#def is_env_64bit():
#    return platform.machine().endswith('64')

def linux_troubleshoot(item):
    print("Dependencies to compile or run:")
    print(' '.join(cmd_depends + depends))
    print()
    print("{} is missing".format(item))
    if re.search("ubuntu|debian", platform.platform(), re.IGNORECASE):
        print("Ubuntu/debian detected, trying to install")
        check_call(['sudo', 'apt-get', 'install'] +
            "gcc make libffi-dev pkg-config libz-dev libbz2-dev".split(' ') +
            "libsqlite3-dev libncurses-dev libexpat1-dev libssl-dev".split(' '))
        print("Re-attempt")
        main()
    else:
        sys.exit(1)

def linux_download_and_extract(target, archive):
    if not os.path.exists(target):
        if len(glob.glob(target + '.tar.bz2')) == 0:
            check_call(['wget', archive])
        check_call(["tar", "-xf", target + '.tar.bz2'])

# Well this was not really needed, but it might be needed later on.
#if is_env_64bit():
#    target = 'pypy-c-jit64'
#    archive = 'pypy-c-jit-latest-linux64.tar.bz2'
#else:
#    target = 'pypy-c-jit'
#    archive = 'pypy-c-jit-latest-linux.tar.bz2'

if __name__=='__main__':
    system = platform.system()
    if system == "Linux":
        linux_main()
    elif system == "Windows":
        windows_main()
    else:
        assert False, "no setup script for {}".format(system)
