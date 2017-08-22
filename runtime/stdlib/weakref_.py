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

@operators.eq.multimethod_s(Ref, Ref)
def Ref_eq(a, b):
    a_val = a.ref()
    b_val = b.ref()

    if a_val is None and b_val is None:
        return boolean(a.ref is b.ref)
    return operators.eq.call([a_val, b_val])

module = Module(u'weakref', {
    u"ref": Ref.interface,
}, frozen=True)
