from space import *
import sys
import weakref

class Ref(Object):
    def __init__(self, obj):
        self.ref = weakref.ref(obj)

    def call(self, argv):
        link = self.ref()
        return null if link is None else link

@Ref.instantiator2(signature(Object))
def Ref_init(obj):
    return Ref(obj)

module = Module(u'weakref', {
    u"ref": Ref.interface,
}, frozen=True)
