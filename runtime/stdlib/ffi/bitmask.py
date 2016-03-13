from simple import Type
from space import *

class Bitmask(Type):
    #__slots__ = ["basetype", "parametric", "size", "align", "constants", "multichoice"]
    #__attrs__ = ["basetype", "parametric", "size", "align", "constants", "multichoice"]
    def __init__(self, basetype, constants, multichoice):
        assert isinstance(basetype, Type)
        self.basetype = basetype
        self.parameter = basetype.parameter
        self.size = basetype.size
        self.align = basetype.align
        self.constants = constants
        self.multichoice = multichoice

    def cast_to_ffitype(self):
        return self.basetype.cast_to_ffitype()

    # TODO: add method_signature for this situation?
    def call(self, argv):
        return bitmask_call([self] + argv)

    def load(self, offset, copy):
        value = self.basetype.load(offset, copy)
        if isinstance(value, Integer):
            return BitmaskValue(self, value.value)
        return value

    def store(self, pool, offset, value):
        value = Integer(to_bitmask_digit(self, value))
        return self.basetype.store(pool, offset, value)

@signature(Bitmask, Object)
def bitmask_call(self, value):
    return BitmaskValue(self, to_bitmask_digit(self, value))

class BitmaskValue(Object):
    __slots__ = ["bitmask", "value"]
    __attrs__ = ["bitmask", "value"]
    def __init__(self, bitmask, value):
        self.bitmask = bitmask
        self.value = value

    def getattr(self, name):
        if name == u"value":
            return Integer(self.value)
        value = to_constant(self.bitmask, name)
        if self.bitmask.multichoice:
            return boolean(self.value & value == value)
        else:
            return boolean(self.value == value)

    def repr(self):
        seq = []
        if self.bitmask.multichoice:
            cover = 0
            for name, mask in self.bitmask.constants.iteritems():
                if self.value & mask == mask:
                    seq.append(String(name))
                    cover |= mask
            weirdbits = self.value ^ cover
            if weirdbits != 0:
                seq.append(Integer(weirdbits))
            return List(seq).repr()
        else:
            for name, mask in self.bitmask.constants.iteritems():
                if mask == self.value:
                    return String(name).repr()
            return Integer(self.value).repr()

def to_bitmask_digit(bitmask, value):
    if isinstance(value, String):
        return to_constant(bitmask, value.string)
    elif isinstance(value, BitmaskValue) and value.bitmask is bitmask:
        return value.value
    elif isinstance(value, Integer):
        return value.value
    elif bitmask.multichoice:
        mask = 0
        it = value.iter()
        try:
            while True:
                item = it.callattr(u"next", [])
                if isinstance(item, String):
                    mask |= to_constant(bitmask, item.string)
                elif isinstance(item, Integer):
                    mask |= item.value
                elif isinstance(item, BitmaskValue) and item.bitmask is bitmask:
                    mask |= item.value
                else:
                    raise unwind(LTypeError(u"enum cannot handle: " + item.repr()))
        except StopIteration as _:
            pass
        return mask
    else:
        raise unwind(LTypeError(u"enum cannot handle: " + value.repr()))

def to_constant(bitmask, string):
    try:
        return bitmask.constants[string]
    except KeyError as _:
        raise unwind(LKeyError(bitmask, String(string)))
