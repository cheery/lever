import os

def new_entry_point(config):
    def entry_point(raw_argv):
        os.write(0, "hello\n")
        return 0
    return entry_point
