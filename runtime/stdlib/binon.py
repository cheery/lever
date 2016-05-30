from bon import open_file
from space import *

module = Module(u'binon', {
    u"read_file": Builtin(
        signature(Object)(open_file),
        u"read_file"),
}, frozen=True)
