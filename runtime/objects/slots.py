from common import *

class Slot(Object):
    interface = InterfaceParametric([BIV])
    def __init__(self, slot_val):
        self.slot_val = slot_val

@method(Slot.interface, op_getslot)
def Slot_getslot(slot):
    slot = cast(slot, Slot)
    return slot.slot_val

@method(Slot.interface, op_setslot)
def Slot_setslot(slot, value):
    slot = cast(slot, Slot)
    slot.slot_val = value
