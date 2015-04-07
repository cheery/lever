# I've made damn sure things do not randomly crash elsewhere
# when I change the code somewhere.

# The tests serve a different purpose:
# It's nice to see it immediately when you get things to work.

# You can initiate the tests with either one of the following commands:
# python test.py python main.py
# python test.py ./main-c
import os
import subprocess
import sys

directory = 'tests'
for name in sorted(filter(str.isdigit, os.listdir(directory))):
    path = os.path.join(directory, name)
    print path
    sys.stdout.flush()
    status = subprocess.call(sys.argv[1:] + [path])
    if status != 0:
        print "{} status: {}".format(path, status)
    print
