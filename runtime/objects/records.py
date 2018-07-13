from rpython.rlib.listsort import make_timsort_class
from core import *

@builtin(1)
def w_RecordConstructor(fields):
    args = []
    items = []
    mutables = {}
    for item in iterate(fields):
        item = cast(item, String).string
        if item.startswith(u"!"):
            item = item[1:]
            mutables[item] = None
        args.append(item)
        items.append(item)
    sorter = FieldSort(items, len(items))
    sorter.sort()
    indices = {}
    index = 0
    for item in items:
        indices[item] = index
        index += 1
    argi = [indices[arg] for arg in args]
    return RecordConstructor(argi, indices, mutables)

RecordConstructorKind = Kind()
class RecordConstructor(Object):
    static_kind = RecordConstructorKind
    def __init__(self, argi, indices, mutables):
        self.argi = argi
        self.indices = indices
        self.mutables = mutables

def Constructor_call(rcons, args):
    rcons = cast(rcons, RecordConstructor)
    ritems = [None] * len(args)
    if len(args) != len(rcons.argi):
        raise error(e_TypeError)
    for i in range(len(args)):
        ritems[rcons.argi[i]] = args[i]
    if len(rcons.mutables) > 0:
        return [MutableRecord(rcons, ritems)]
    else:
        return [ImmutableRecord(rcons, ritems)]
RecordConstructorKind.properties[op_call] = BuiltinPortal(Constructor_call)

RecordKind = Kind()
class ImmutableRecord(Object):
    static_kind = RecordKind
    def __init__(self, rcons, ritems):
        self.rcons = rcons
        self.ritems = ritems

class MutableRecord(Object):
    static_kind = RecordKind
    def __init__(self, rcons, ritems):
        self.rcons = rcons
        self.ritems = ritems

TimSort = make_timsort_class()

class FieldSort(TimSort):
    def lt(self, a, b):
        return a[0] < b[0]

@method(RecordKind, op_eq, 1)
def Record_eq(a, b):
    if isinstance(a, MutableRecord) and isinstance(b, MutableRecord):
        return wrap(a is b)
    a = cast(a, ImmutableRecord)
    b = cast(b, ImmutableRecord)
    if a.rcons.indices.keys() != b.rcons.indices.keys():
        return false
    if len(a.items) != len(b.items):
        return false
    for i in range(len(a.items)):
        if not eq_fn(a.items[i], b.items[i]):
            return false
    return true

@method(RecordKind, op_hash, 1)
def Record_hash(a):
    if isinstance(a, MutableRecord):
        return wrap(compute_hash(a))
    a = cast(a, ImmutableRecord)
    mult = 1000003
    x = 0x345678
    z = len(a.items)
    for item in a.items:
        y = unwrap_int(call(op_hash, [item]))
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return wrap(intmask(x))

@method(RecordKind, atom_dynamic_getattr, outc=1)
def Record_dynamic_getattr(name):
    return prefill(w_load_item, [name])

@method(RecordKind, atom_dynamic_setattr, outc=1)
def Record_dynamic_setattr(name):
    return prefill(w_store_item, [name])

@builtin(1)
def w_load_item(w_name, record):
    name = cast(w_name, String).string
    if isinstance(record, MutableRecord):
        index = record.rcons.indices.get(name, -1)
        if index >= 0:
            return record.ritems[index]
    else:
        record = cast(record, ImmutableRecord)
        index = record.rcons.indices.get(name, -1)
        if index >= 0:
            return record.ritems[index]
    raise error(e_NoAttr, w_name)

@builtin(0)
def w_store_item(w_name, record, value):
    name = cast(w_name, String).string
    if isinstance(record, ImmutableRecord):
        raise error(e_TypeError)
    record = cast(record, MutableRecord)
    index = record.rcons.indices.get(name, -1)
    if index >= 0 and name in record.rcons.mutables:
        record.ritems[index] = value
    else:
        raise error(e_NoAttr)

variables = {
    "RecordConstructor": w_RecordConstructor,
    "RecordKind": RecordKind,
}
