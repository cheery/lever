from core import *

@builtin(1)
def w_slot(value):
    return Slot(value)

SlotKind = Kind()
class Slot(Object):
    static_kind = SlotKind
    def __init__(self, value):
        self.value = value

@method(Slot, op_getslot, 1)
def Slot_getslot(slot):
    slot = cast(slot, Slot)
    return slot.value

@method(Slot, op_setslot, 0)
def Slot_setslot(slot, value):
    slot = cast(slot, Slot)
    slot.value = value

@method(Slot, op_copy, 1)
def Slot_copy(slot):
    slot = cast(slot, Slot)
    return Slot(slot.value)

@method(Slot, op_eq, 1)
def Slot_eq(a, b):
    a = cast(a, Slot)
    b = cast(b, Slot)
    return wrap(a is b)

@method(Slot, op_hash, 1)
def Slot_hash(a, w_hash):
    a = cast(a, Slot)
    return wrap(compute_hash(a))

variables = {
    u"SlotKind": SlotKind,
    u"slot": w_slot,
}
