#!/usr/bin/env python
"""
    This script should help you out at setting up environment for pyllisp.
    If you run this script without arguments, it will just setup the environment.
    Run it with 'compile' -argument, eg. "./setup.py compile" and it also compiles
    the pyllisp. Though that will take some time to finish.
    If you're in hurry, just run "./setup.py"
"""
from subprocess import call, check_call
import platform
import re
import sys
import glob
import os

cmd_depends = "pkg-config gcc make bzip2".split(' ')
depends = "libffi zlib sqlite3 ncurses expat libssl".split(' ')

devnull = open(os.devnull, 'w')
def main():
    for cmd in cmd_depends:
        if call([cmd, '--version'], stdout=devnull, stderr=devnull) != 0:
            return troubleshoot(cmd)
    for dependency in depends:
        if call(['pkg-config', '--exists', dependency]) != 0:
            return troubleshoot(dependency)
    download_and_extract('pypy-4.0.1-src', 'https://bitbucket.org/pypy/pypy/downloads/pypy-4.0.1-src.tar.bz2')
    if len(sys.argv) > 1 and sys.argv[1] == 'compile':
        os.environ['PYTHONPATH'] = "pypy-4.0.1-src"
        check_call("python pypy-4.0.1-src/rpython/bin/rpython --translation-jit --gc=incminimark --opt=2 main.py".split(' '))
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-stm':
        os.environ['PYTHONPATH'] = "pypy-stm"
        check_call("python pypy-stm/rpython/bin/rpython --translation-jit --opt=2 --stm main.py".split(' '))
    if len(sys.argv) > 1 and sys.argv[1] == 'compile-nojit':
        os.environ['PYTHONPATH'] = "pypy-4.0.1-src"
        check_call("python pypy-4.0.1-src/rpython/bin/rpython --gc=incminimark main.py".split(' '))

#--continuation --gc=incminimark --gcrootfinder=shadowstack --opt=2

def is_env_64bit():
    return platform.machine().endswith('64')

def troubleshoot(item):
    print("Lever dependencies to compile or run:")
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

def download_and_extract(target, archive):
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
#
#def download_and_extract_old(target, archive):
#    if not os.path.exists(target):
#        if len(glob.glob(archive)) == 0:
#            check_call("wget http://buildbot.pypy.org/nightly/trunk/{}".format(archive).split(' '))
#        check_call(["tar", "-xf", archive])
#        dirs = filter(os.path.isdir, glob.glob('pypy-c-jit-*'))
#        assert len(dirs) == 1, "found more than 1 directory matching 'pypy-c-jit-', not sure what to do."
#        os.rename(dirs[0], target)

if __name__=='__main__': main()
