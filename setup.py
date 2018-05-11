#!/usr/bin/env python2
"""
    This script should help setting up the environment for Lever.
    Run ./setup dependencies, and it setups the environment.
    Run ./setup compile, and it compiles.
    Compiling takes some time to finish.
"""
from StringIO import StringIO
from subprocess import call, check_call
from urllib import urlopen
from zipfile import ZipFile
from hashlib import sha256
import argparse, json, os, sys

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd = subparsers.add_parser('dependencies',
        help="Fetch or build dependencies for building runtime")
    cmd.set_defaults(func=dependencies)

    cmd = subparsers.add_parser('compile',
        help="Compile the lever runtime")
    cmd.set_defaults(func=compile_lever)
    cmd.add_argument("--lldebug", action="store_true",
        help="Produce debugging information")
    cmd.add_argument("--use-pypy", action="store_true",
        help="Use pypy for compiling")

    # TODO: Provide remaining helpers for maintaining the project.

    args = parser.parse_args()
    return args.func(args)

pypy_src_url = 'https://bitbucket.org/pypy/pypy/downloads/pypy2-v5.10.0-src'
pypy_src_sha256 = '89304eb886f84b5c65f3f4079445ef018cdb9a6e59ef4ed2095d37248a3fefcc'
# The project depends on RPython in PyPy branch.
# Everything needed for building this project
# is stored in the build/ subdirectory.
def dependencies(args):
    mkdirs('build')
    config = config_read()

    # You may place a custom pypy into build/pypy directory.
    if os.path.exists(os.path.join('build', 'pypy')):
        pypy_src_dir = os.path.join('build', 'pypy')
    else:
        pypy_src_dir = os.path.join('build',
            os.path.basename(pypy_src_url))
        if not os.path.exists(pypy_src_dir):
            download_and_extract('build', pypy_src_url + ".zip",
                pypy_src_sha256) 

    config['env']['PYTHONPATH'] = pypy_src_dir
    config['rpython_bin'] = os.path.join(pypy_src_dir,
        'rpython', 'bin', 'rpython')

    # TODO: insert the remaining troubleshoot/prebuild handling.

    config_write(config)
    return 0

# RPython script, usually in rpython/bin/rpython, is run with the
# runtime/goal_standalone.py
# This causes the runtime/goal_standalone.py to load and evaluate.
def compile_lever(args):
    config = config_read()
    rpython_bin = config.get('rpython_bin')
    if rpython_bin is None:
        print("error: build environment has not been properly setup")
        return 1

    build_flags = []
    #if not args.nojit:
    #    build_flags.append('--translation-jit')
    #build_flags.append('--gc=incminimark')
    #build_flags.append('--opt=2')
    if args.lldebug:
        build_flags.append('--lldebug')
    
    if args.use_pypy:
        cmd = 'pypy'
    else:
        cmd = 'python'
    check_call([cmd, rpython_bin] + build_flags
        + ["runtime/goal_standalone.py"])

# There's a build-time configuration file in build/config.json
# It contains some variables you may change to adjust your build.
def config_read():
    if os.path.exists('build/config.json'):
        with open('build/config.json') as fd:
            return json.load(fd)
    else:
        return {
            'env': {},
        }

def config_write(config):
    with open('build/config.json', 'w') as fd:
        json.dump(config, fd)

# For now, the build script fetches the latest PyPy source package
# to retrieve the RPython translator.
def download_and_extract(target, archive, checksum):
    print('downloading {}'.format(archive))
    tmp_file = os.path.join(target, os.path.basename(archive))
    url = urlopen(archive)
    length = int(url.info()['Content-Length'])
    bstep = length // 9
    with open(tmp_file, 'wb') as fd:
        for i in range(0, length // bstep + 1):
            data = url.read(bstep)
            fd.write(data)
            print ('_'*i) + '@' + ('_'*(9-i)) + (" {}MB".format(length//1000000) if i==0 else '')
    # Some of this is overcomplicated and was written for fun, but I actually
    # wanted to go into details here. Store the file so that a checksum could
    # be calculated. The checksums provide a much-needed failure if the url
    # contents change silently.
    m = sha256()
    with open(tmp_file, 'rb') as fd:
        m.update(fd.read())
    file_checksum = m.hexdigest()
    assert file_checksum == checksum, (
        "file checksum check failed\nfile: {}\nhash: {}".format(
            file_checksum, checksum))
    print 'extracting the package to directory: {}'.format(target)
    with open(tmp_file, 'rb') as fd:
        zipfile = ZipFile(fd)
        zipfile.extractall(path=target)

def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

if __name__=="__main__":
    sys.exit(main())
