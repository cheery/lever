from builtin import signature
from interface import Object, null
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rarithmetic import intmask
import space

class Slice(Object):
    _immutable_fields_ = ['start', 'stop', 'step']
    __slots__ = ['start', 'stop', 'step']

    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step

    def getattr(self, name):
        if name == u'start':
            return self.start
        if name == u'stop':
            return self.stop
        if name == u'step':
            return self.step
        return Object.getattr(self, name)

    def hash(self):
        mult = 1000003
        x = 0x345678
        z = 3
        for y in [self.start.hash(), self.stop.hash(), self.step.hash()]:
            x = (x ^ y) * mult
            z -= 1
            mult += 82520 + z + z
        x += 97531
        return intmask(x)

    def eq(self, other): # TODO: improve this?
        import operators
        return space.is_true(operators.eq.call([self, other]))

    def iter(self):
        if self.stop is null:
            start = space.to_int(self.start)
            step = space.to_int(self.step)
            return SliceStep(start, step)
        else:
            start = space.to_int(self.start)
            stop = space.to_int(self.stop)
            step = space.to_int(self.step)
            return SliceRange(start, stop, step) 

    def clamped(self, low, high):
        step = space.to_int(self.step)
        if self.start is null:
            if step < 0:
                a = high
            else:
                a = low
        else:
            if step < 0:
                a = space.to_int(self.start)
                a = max(low-1, min(high, a))
            else:
                a = space.to_int(self.start)
                a = max(low, min(high+1, a))
        if self.stop is null:
            if step < 0:
                b = low - 1
            else:
                b = high + 1
        else:
            b = space.to_int(self.stop)
            b = max(low-1, min(high+1, b))
        return (a, b, step)

@Slice.instantiator2(signature(Object, Object, Object, optional=1))
def Slice_inst(start, stop, step):
    if step is None:
        step = space.Integer(1)
    return Slice(start, stop, step)

class SliceRange(Object):
    def __init__(self, start, stop, step):
        self.current = start
        self.stop = stop
        self.step = step
        self.sign = +1 if step >= 0 else -1

    def iter(self):
        return self

@SliceRange.method(u"next", signature(SliceRange))
def SliceRange_next(self):
    if self.current*self.sign < self.stop*self.sign:
        i = self.current
        self.current += self.step
        return space.Integer(i)
    raise StopIteration()

class SliceStep(Object):
    def __init__(self, start, step):
        self.current = start
        self.step = step

    def iter(self):
        return self

@SliceStep.method(u"next", signature(SliceStep))
def SliceStep_next(self):
    i = self.current
    self.current += self.step
    return space.Integer(i)
