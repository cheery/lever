from rpython.rlib.listsort import make_timsort_class
from rpython.rlib import jit
from common import *

def construct_record_type(fields):
    sorter = FieldSort(fields, len(fields))
    sorter.sort()
    map = EMPTY_MAP
    for name, mutable in sorter.list:
        if map.getindex(name) != -1:
            raise error(e_TypeError())
        map = map.new_map_with_additional_attribute(name, mutable)
    return RecordInterface(map)

def construct_record(fields):
    t_fields = []
    for name, mutable, value in fields:
        t_fields.append((name, mutable))
    face = construct_record_type(t_fields)
    record_val = [null for i in range(len(fields))]
    for name, mutable, value in fields:
        record_val[face.map.getindex(name)] = value
    return Record(face, record_val)

class RecordInterface(Interface):
    def __init__(self, map):
        self.map = map

    def getattr(self, name):
        index = self.map.getindex(name)
        if index == -1:
            raise error(e_TypeError())
        return prefill(w_r_index_get, [fresh_integer(index)])

    def setattr(self, name):
        index = self.map.getindex(name)
        if index == -1 or not self.map.is_mutable_field(name):
            raise error(e_TypeError())
        return prefill(w_r_index_set, [fresh_integer(index)])

class Record(Object):
    interface = None
    def __init__(self, record_face, record_val):
        self.record_face = record_face
        self.record_val = record_val

    def face(self):
        return self.record_face

@builtin()
def w_r_index_get(index, record):
    i = cast(index, Integer).toint()
    record = cast(record, Record)
    return record.record_val[i]

@builtin()
def w_r_index_set(index, record, value):
    i = cast(index, Integer).toint()
    record = cast(record, Record)
    record.record_val[i] = value

TimSort = make_timsort_class()

class FieldSort(TimSort):
    def lt(self, a, b):
        return a[0] < b[0]

class Map(object):
    def __init__(self):
        self.indexes = {}
        self.mutables = {}
        self.other_maps = {}

    @jit.elidable
    def getindex(self, name):
        return self.indexes.get(name, -1)

    @jit.elidable
    def is_mutable_field(self, name):
        return name in self.mutables

    @jit.elidable
    def new_map_with_additional_attribute(self, name, mutable):
        if (name, mutable) not in self.other_maps:
            newmap = Map()
            newmap.indexes.update(self.indexes)
            newmap.indexes[name] = len(self.indexes)
            newmap.mutables.update(self.mutables)
            self.other_maps[(name, mutable)] = newmap
            if mutable:
                newmap.mutables[name] = None
        return self.other_maps[(name, mutable)]

EMPTY_MAP = Map()
