from space import *
import sys
import platform

module = Module(u'platform', {
    u"name": from_cstring(sys.platform),
    u"arch": from_cstring(platform.machine())
}, frozen=True)
