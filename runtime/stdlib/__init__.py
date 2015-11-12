import pkgutil
import sys
import os

def import_all_modules():
    for importer, name, ispkg in pkgutil.iter_modules(__path__):
        fullname = '%s.%s' % (__name__, name)
        if fullname in sys.modules:
            yield sys.modules[fullname]
        else:
            yield importer.find_module(name).load_module(fullname)
