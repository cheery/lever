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

# On linux the system checks whether the tools required to build it respond.
# Then it checks whether the system has the required C libraries to have
# a chance of successful build.

# When there's a chance that the thing actually builds, it downloads and extracts
# pypy sources. PyPy changes often and the newer versions introduce nice improvements
# so an attempt has been made to keep up with the version changes.

# There's no need to compile pypy itself. We run rpython with python 2.7
# Presence of python 2.7 is not being checked, because if you can run this script,
# as described on the README, you should have python 2.x installed on your system.

# It's been 7 years after 2.7 has been released, and pretty much the libraries listed
# are stabilized, so I don't expect to have trouble with versions.
# Maybe it happens some day... On someone's computer. That he doesn't have recent enough
# versions of these libraries.
pypy_src_url = 'https://bitbucket.org/pypy/pypy/downloads/pypy2-v5.6.0-src'
pypy_src_dir = 'pypy2-v5.6.0-src'

# These are listed in "Building PyPy from Source":
#                     http://doc.pypy.org/en/latest/build.html
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

# On windows, you're going to need Visual studio 9.0 and you need to
# know how to use it. (You might obtain it by checking for "visual studio for python 2.7")
# Having frequent releases start to seem relevant, so I may have to setup a build computer that
# automates it. Maybe some day...
def windows_main():
    if not os.path.exists(pypy_src_dir):
        url = urlopen(pypy_src_url + '.zip')
        zipfile = ZipFile(StringIO(url.read()))
        zipfile.extractall()
        print("Note that building from source for windows isn't frequent.")
        print("Experienced computer operator is required after this point.")
    compiling_commands()

def compiling_commands():
    os.environ['PYTHONPATH'] = pypy_src_dir
    rpython_bin = os.path.join(pypy_src_dir, 'rpython', 'bin', 'rpython')
    if len(sys.argv) > 1 and sys.argv[1] == 'pypy-compile-debug':
        check_call(['pypy', rpython_bin] + "--translation-jit --gc=incminimark --opt=2 --lldebug runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'pypy-compile':
        check_call(['pypy', rpython_bin] + "--translation-jit --gc=incminimark --opt=2 runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-debug':
        check_call(['python', rpython_bin] + "--translation-jit --gc=incminimark --opt=2 --lldebug runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'compile':
        check_call(['python', rpython_bin] + "--translation-jit --gc=incminimark --opt=2 runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-debug-nojit':
        check_call(['python', rpython_bin] + "--gc=incminimark --opt=2 --lldebug runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-nojit':
        check_call(['python', rpython_bin] + "--gc=incminimark runtime/goal_standalone.py".split(' '))
        compile_libraries(preserve_cache=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-lib':
        compile_libraries()
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-lib-all':
        compile_libraries(preserve_cache=False)
# It was tried once.. Plans are to pick it up when PyPy STM improves.
#    if len(sys.argv) > 1 and sys.argv[1] == 'compile-stm':
#        os.environ['PYTHONPATH'] = "pypy-stm"
#        check_call("python pypy-stm/rpython/bin/rpython --translation-jit --opt=2 --stm main.py".split(' '))

def compile_libraries(preserve_cache=True):
    from compiler import compile
    print("Compiling libraries for lever")
    for dirname, subdirs, files in os.walk("lib"):
        for name in files:
            if name.endswith(".lc"):
                lc_name = os.path.join(dirname, name)
                cb_name = re.sub(".lc$", ".lc.cb", lc_name)
                # Compiling the whole `lib/` is not needed during development.
                # Chances are it will take whole lot of time eventually.
                # Trouble-free parsing isn't free.
                if preserve_cache and (os.path.isfile(cb_name)
                        and os.path.getmtime(cb_name) >= os.path.getmtime(lc_name)):
                    continue
                try:
                    compile.compile_file(cb_name, lc_name)
                except Exception as e:
                    print("{}:{}".format(lc_name, e))

#--continuation --gc=incminimark --gcrootfinder=shadowstack --opt=2

#def is_env_64bit():
#    return platform.machine().endswith('64')

def linux_troubleshoot(item):
    print("Dependencies to compile or run:")
    print(' '.join(command_depends + library_depends))
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
