from space import *
import module_resolution
import os
import stdlib

# The base environment
module = Module(u'base', {
    u'dict': Dict.interface,
    u'module': Module.interface,
    u'exnihilo': Exnihilo.interface,
    u'object': Object.interface,
    u'list': List.interface,
    u'multimethod': Multimethod.interface,
    u'int': Integer.interface,
    u'bool': Boolean.interface,
    u'str': String.interface,
    u'null': null,
    u'true': true,
    u'false': false,
}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
def class_(argv):
    exnihilo = argv[0]
    parent = Object.interface
    name = String(u"customobject")
    assert 1 <= len(argv) <= 3
    if len(argv) > 1:
        parent = argv[1]
    if len(argv) > 2:
        name = argv[2]
    assert isinstance(exnihilo, Exnihilo)
    assert isinstance(parent, Interface)
    assert isinstance(name, String)
    interface = Interface(parent, name.string)
    interface.methods = exnihilo.cells
    interface.instantiate = CustomObject.interface.instantiate
    return interface

@builtin
@signature(Object)
def interface(obj):
    return get_interface(obj)

@builtin
@signature(Object)
def iter(obj):
    return obj.iter()
  
#  #def pyl_apply(argv):
#  #    N = len(argv) - 1
#  #    assert N >= 1
#  #    args = argv[1:N]
#  #    varg = argv[N]
#  #    assert isinstance(varg, List)
#  #    return argv[0].invoke(args + varg.items)
  
@builtin
@signature(Object, Object)
def getitem(obj, index):
    return obj.getitem(index)

@builtin
@signature(Object, Object, Object)
def setitem(obj, index, value):
    return obj.setitem(index, value)

@builtin
@signature(Object, String)
def getattr(obj, index):
    return obj.getattr(index.string)

@builtin
@signature(Object, String, Object)
def setattr(obj, index, value):
    return obj.setattr(index.string, value)

@builtin
@signature(String)
def ord_(string):
    assert len(string.string) == 1
    return Integer(ord(string.string[0]))

@builtin
@signature(Integer)
def chr_(value):
    return String(unichr(value.value))
  
#def pyl_callattr(argv):
#    assert len(argv) >= 2
#    name = argv[1]
#    assert isinstance(name, String)
#    return argv[0].callattr(name.string, argv[2:len(argv)])

@builtin
def print_(argv):
    space = u''
    out = u""
    for arg in argv:
        if isinstance(arg, String):
            string = arg.string
        else:
            string = arg.repr()
        out += space + string
        space = u' '
    os.write(1, (out + u'\n').encode('utf-8'))
    return null
  
# And and or are macros in the compiler. These are
# convenience functions, likely not often used.
# erm. Actually 'and' function is used by chaining.
@builtin
@signature(Object, Object)
def and_(a, b):
    return boolean(is_true(a) and is_true(b))

@builtin
@signature(Object, Object)
def or_(a, b):
    return boolean(is_true(a) or is_true(b))

@builtin
@signature(Object)
def not_(a):
    return boolean(is_false(a))

coerce = module.setattr_force(u'coerce', Multimethod(2))
@coerce.multimethod_s(Boolean, Boolean)
def _(a, b):
    return List([Integer(int(a.flag)), Integer(int(b.flag))])

@coerce.multimethod_s(Integer, Boolean)
def _(a, b):
    return List([a, Integer(int(b.flag))])

@coerce.multimethod_s(Boolean, Integer)
def _(a, b):
    return List([Integer(int(a.flag)), b])

def arithmetic_multimethod(operation):
    method = Multimethod(2)
    @Builtin
    def default(argv):
        args = coerce.call(argv)
        assert isinstance(args, List)
        return method.call_suppressed(args.contents)
    method.default = default
    @method.multimethod_s(Integer, Integer)
    def _(a, b):
        return Integer(operation(a.value, b.value))
    return method

module.setattr_force(u'+', arithmetic_multimethod(lambda a, b: a + b))
module.setattr_force(u'-', arithmetic_multimethod(lambda a, b: a - b))
module.setattr_force(u'*', arithmetic_multimethod(lambda a, b: a * b))
module.setattr_force(u'/', arithmetic_multimethod(lambda a, b: a / b))
module.setattr_force(u'|', arithmetic_multimethod(lambda a, b: a | b))
module.setattr_force(u'%', arithmetic_multimethod(lambda a, b: a % b))
module.setattr_force(u'&', arithmetic_multimethod(lambda a, b: a & b))
module.setattr_force(u'^', arithmetic_multimethod(lambda a, b: a ^ b))
module.setattr_force(u'<<', arithmetic_multimethod(lambda a, b: a << b))
module.setattr_force(u'>>', arithmetic_multimethod(lambda a, b: a >> b))
module.setattr_force(u'min', arithmetic_multimethod(lambda a, b: min(a, b)))
module.setattr_force(u'max', arithmetic_multimethod(lambda a, b: max(a, b)))

# Not actual implementations of these functions
# All of these will be multimethods
@signature(Integer, Integer)
def cmp_lt(a, b):
    return boolean(a.value < b.value)
module.setattr_force(u'<', Builtin(cmp_lt, u'<'))

@signature(Integer, Integer)
def cmp_gt(a, b):
    return boolean(a.value > b.value)
module.setattr_force(u'>', Builtin(cmp_gt, u'>'))

@signature(Integer, Integer)
def cmp_le(a, b):
    return boolean(a.value <= b.value)
module.setattr_force(u'<=', Builtin(cmp_le, u'<='))

@signature(Integer, Integer)
def cmp_ge(a, b):
    return boolean(a.value >= b.value)
module.setattr_force(u'>=', Builtin(cmp_ge, u'>='))

ne = module.setattr_force(u'!=', Multimethod(2))
@signature(Object, Object)
def ne_default(a, b):
    return boolean(a != b)
ne.default = Builtin(ne_default)

@ne.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value != b.value)

@ne.multimethod_s(String, String)
def _(a, b):
    return boolean(not a.eq(b))

eq = module.setattr_force(u'==', Multimethod(2))
@signature(Object, Object)
def eq_default(a, b):
    return boolean(a == b)
eq.default = Builtin(eq_default)

@eq.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value == b.value)

@eq.multimethod_s(String, String)
def _(a, b):
    return boolean(a.eq(b))

neg = module.setattr_force(u'-expr', Multimethod(1))
@neg.multimethod_s(Integer)
def _(a):
    return Integer(-a.value)

pos = module.setattr_force(u'+expr', Multimethod(1))
@pos.multimethod_s(Integer)
def _(a):
    return Integer(+a.value)

concat = module.setattr_force(u'++', Multimethod(2))
@concat.multimethod_s(String, String)
def _(a, b):
    return String(a.string + b.string)
@concat.multimethod_s(List, List)
def _(a, b):
    return List(a.contents + b.contents)

# Module namespace.
builtin_modules = {}
for py_module in stdlib.import_all_modules():
    builtin_modules[py_module.module.name] = py_module.module

stdlib_modules = {}

@builtin
@signature(String)
def import_(name):
    if name.string in builtin_modules:
        return builtin_modules[name.string]
    if name.string in stdlib_modules:
        return stdlib_modules[name.string]
    app_dir = os.environ.get('LEVER_PATH')
    if app_dir is None:
        app_dir = ''
    path_name = os.path.join(app_dir, "stdlib").decode('utf-8') + u"/" + name.string
    this = Module(name.string, {}, extends=module) # base.module
    module_resolution.load_module(path_name.encode('utf-8'), this)
    stdlib_modules[name.string] = this
    return this
