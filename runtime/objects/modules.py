from rpython.rlib.objectmodel import compute_hash
from core import Object, wrap, builtin, cast
from core import e_NoAttr, e_ModuleAlreadyLoaded
from core import e_ModuleError, e_AlreadySet, e_BugAbstractMethod
from core import call, error
import core

# Documentation references provide naming information and
# tell where to find the documentation for the element.
atom_documentation = core.Atom(0)
atom_docref = core.Atom(2)
atom_docroot = core.Atom(1)

ModuleKind = core.Kind()
class Module(Object):
    static_kind = ModuleKind
    def __init__(self):
        self.cells = {}
        self.loaded = False
        self.docroot = core.Compound(atom_docroot, [self])

@core.method(Module, core.op_eq, outc=1)
def Module_eq(a, b):
    return wrap(a is b)

@core.method(Module, core.op_hash, outc=1)
def Module_hash(a, w_hash):
    return wrap(compute_hash(a))

@core.method(Module, core.atom_dynamic_getattr, outc=1)
def Module_dynamic_getattr(name):
    return core.prefill(w_load_cell, [name])

@core.method(Module, core.atom_dynamic_setattr, outc=1)
def Module_dynamic_setattr(name):
    return core.prefill(w_store_cell, [name])

@builtin(1)
def w_load_cell(w_name, module):
    name = cast(w_name, core.String).string
    module = cast(module, Module)
    cell = module.cells.get(name, None)
    if cell is None:
        raise error(e_NoAttr, w_name)
    return cell.load()

@builtin(0)
def w_store_cell(w_name, module, value):
    name = cast(w_name, core.String).string
    module = cast(module, Module)
    cell = module.cells.get(name, None)
    if isinstance(cell, ConstantModuleCell):
        raise error(e_AlreadySet, w_name)
    if cell is not None:
        cell.store(value)
    if module.loaded:
        raise error(e_ModuleAlreadyLoaded, w_name)
    else:
        module.cells[name] = ConstantModuleCell(value)
        properties = core.get_properties(value)
        if properties is not None:
            doc = properties.get(atom_documentation, None)
            if doc is None:
                properties[atom_documentation] = core.Compound(atom_docref,
                    [module.docroot, w_name])

def bind_cell(module, name, cell):
    cell = module.cells.get(name, None)
    if cell is not None:
        raise error(e_AlreadySet, w_name)
    else:
        module.cells[name] = cell

class ModuleCell:
    def load(self):
        raise error(e_BugAbstractMethod)

    def store(self, value):
        raise error(e_BugAbstractMethod)

class ConstantModuleCell(ModuleCell):
    def __init__(self, val):
        self.val = val

    def load(self):
        return self.val

ModuleSpaceKind = core.Kind()
class ModuleSpace(Object):
    static_kind = ModuleSpaceKind
    def __init__(self, local, env, loader, parent=None):
        self.local = local
        self.env = env
        self.loader = loader
        self.parent = parent
        self.loaded = {}

    def is_closed(self):
        return self.loader is None

@core.method(ModuleSpace, core.op_eq, 1)
def ModuleSpace_eq(a, b):
    return wrap(a is b)

@core.method(ModuleSpace, core.op_hash, 1)
def ModuleSpace_hash(a):
    return wrap(compute_hash(a))

@builtin(1)
def w_import(mspace, w_name):
    mspace = cast(mspace, ModuleSpace)
    name = cast(w_name, core.String).string
    if name in mspace.loaded:
        module = mspace.loaded[name]
        if module is None:
            # disallow recursion. # TODO: Improve errors.
            raise error(e_ModuleError)
        return module
    if mspace.is_closed():
        raise error(e_ModuleError)
    mspace.loaded[name] = None # Ensure recursion is catched.
    try:
        module = call(mspace.loader, [mspace, w_name])
    finally:
        mspace.loaded.pop(name)
    mspace.loaded[name] = module
    return module

variables = {
    u"documentation": atom_documentation,
    u"docref": atom_docref,
    u"docroot": atom_docroot,
    u"ModuleKind": ModuleKind,
    u"ModuleSpaceKind": ModuleSpaceKind,
}
