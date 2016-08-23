from builtin import signature
from interface import Object, null
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

    def clamped(self, start, stop):
        step = space.to_int(self.step)
        if self.start is null:
            if step < 0:
                a = stop - 1 
            else:
                a = start
        else:
            a = space.to_int(self.start)
            a = max(start, min(stop-1, a))
        if self.stop is null:
            if step < 0:
                b = start - 1 
            else:
                b = stop
        else:
            b = space.to_int(self.stop)
            b = max(start-1, min(stop, b))
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
