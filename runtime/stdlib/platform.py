from space import *
import sys

module = Module(u'platform', {
    u"name": from_cstring(sys.platform),
}, frozen=True)
