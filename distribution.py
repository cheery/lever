"""
    This script creates a distribution for lever
"""
import os, shutil, sys, zipfile
if not os.path.exists("lever.exe"):
    print("Need something to distribute first. Run setup.py compile on win32")
    sys.exit(1)
mtime = os.path.getmtime("lever.exe")
# I do not want to release stale distribution.
for root, dirs, fils in os.walk("evaluator"):
    for fil in fils:
        mtime = min(mtime, os.path.getmtime(os.path.join(root, fil)))
for root, dirs, fils in os.walk("space"):
    for fil in fils:
        mtime = min(mtime, os.path.getmtime(os.path.join(root, fil)))
for root, dirs, fils in os.walk("runtime"):
    for fil in fils:
        mtime = min(mtime, os.path.getmtime(os.path.join(root, fil)))
if mtime > os.path.getmtime("lever.exe"):
    print("Stale executable, re-run setup.py compile on win32")
    sys.exit(1)
VERSION = open("VERSION").read().strip()
archive = 'lever-{}.zip'.format(VERSION)
zf = zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED)
def include(path, to=None):
    to = path if to is None else to
    assert not os.path.isabs(path)
    zf.write(path, os.path.join("lever", to))
def include_dir(dirname):
    for root, dirs, fils in os.walk(dirname):
        for fil in fils:
            include(os.path.join(root, fil))
def include_contents(dirname):
    for root, dirs, fils in os.walk(dirname):
        for fil in fils:
            path = os.path.join(root, fil)
            include(path, os.path.relpath(path, dirname))

include("lever.exe")
include("lever.grammar")
include("VERSION")
include_dir("app")
include_dir("lib")
include_dir("evaluator")
include_dir("compiler")
include("compile.py")
include_dir("samples")
include_dir("headers")
include("LICENSE.md", "LICENSE.lever.txt")
include_contents("win32_extras")

zf.close()
print os.path.abspath(archive)
