#!/usr/bin/env python
import subprocess, os

postfixes = set([".vert", ".tesc", ".tese", ".geom", ".frag", ".comp"])

for infile in os.listdir("."):
    name, ext = os.path.splitext(infile)
    if ext in postfixes:
        outfile = name + ".spv"
        status = subprocess.call(["glslangValidator", "-V",
            infile, "-o", outfile])
        if status != 0:
            break
