from rpython.rlib import unroll
from rpython.rtyper.lltypesystem import rffi
from interface import Object, null
import space
import inspect
import os

class Builtin(Object):
    _immutable_fields_ = ['func']
    def __init__(self, func, name=None, doc=null, spec=None, source_location=None):
        self.func = func
        self.name = name if name is not None else func.__name__.decode('utf-8')
        self.doc = doc
        if source_location is None:
            self.source_location = get_source_location(func)
        else:
            self.source_location = source_location
        if spec is None:
            self.spec = get_spec(func)
        else:
            self.spec = spec

    def call(self, argv):
        return self.func(argv)

    def getattr(self, name):
        if name == u"doc":
            return self.doc
        elif name == u"loc":
            source, start_lno, stop_lno = self.source_location
            obj = space.Exnihilo()
            obj.setattr(u"source", space.String(source))
            start = space.Exnihilo()
            start.setattr(u"col", null)
            start.setattr(u"lno", space.Integer(start_lno))
            obj.setattr(u"start",  start)
            stop = space.Exnihilo()
            stop.setattr(u"col", null)
            stop.setattr(u"lno", space.Integer(stop_lno))
            obj.setattr(u"stop", stop)
            return obj
        elif name == u"spec":
            argc, optional, variadic, varnames, argtypes = self.spec
            varnames = [space.String(name.decode('utf-8')) for name in varnames]
            spec = space.Exnihilo()
            spec.setattr(u'argc', space.Integer(rffi.r_long(argc)))
            spec.setattr(u'optional', space.Integer(rffi.r_long(optional)))
            spec.setattr(u'is_variadic', space.boolean(variadic))
            spec.setattr(u'varnames', space.List(list(varnames)))
            if argtypes is not None:
                spec.setattr(u'argtypes', space.List(list(argtypes)))
            else:
                spec.setattr(u'argtypes', space.null)
            return spec
        else:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"doc":
            self.doc = value
            return value
        else:
            return Object.setattr(self, name, value)

    def listattr(self):
        listing = Object.listattr(self)
        listing.append(space.String(u"doc"))
        listing.append(space.String(u"loc"))
        listing.append(space.String(u"spec"))
        return listing
    
    def repr(self):
        import naming #TODO: Consider options here.
        doc = self.doc
        if isinstance(doc, naming.DocRef):
            name = naming.get_name(self)
            if name is not None:
                return u"<" + name + u" in " + doc.module.repr() + u">"
        return u"<builtin %s>" % self.name

# Turns out signature would have been much better
# if it had allowed optional and variadic arguments too.
# So I changed it to allow that.
def signature(*argtypes, **keywords):
    topc = argc = len(argtypes)
    argc -= keywords.get("optional", 0)
    variadic = keywords.get("variadic", False)
    argi = unroll.unrolling_iterable(range(argc))
    argj = unroll.unrolling_iterable(range(argc, topc))
    def signature_decorator(func):
        def fancy_frame(argv):
            args = ()
            L = len(argv)
            if L < argc or (L > topc and not variadic):
                raise space.unwind(space.LCallError(argc, topc, variadic, L))
            for i in argi:
                arg = argv[i]
                if isinstance(arg, argtypes[i]):
                    args += (arg,)
                else:
                    args += (space.cast(arg, argtypes[i], u"arg:%d"%i),)
            for j in argj:
                if j < L:
                    arg = argv[j]
                    if arg is null:
                        arg = None
                    elif not isinstance(arg, argtypes[j]):
                        arg = space.cast(arg, argtypes[j], u"arg:%d"%j)
                else:
                    arg = None
                args += (arg,)
            if variadic:
                args += (argv[min(topc, L):],)
            return func(*args)
        fancy_frame.__name__ = func.__name__
        spec_table[fancy_frame] = spec_table[func] = (argc, topc-argc, variadic,
            list(inspect.getargspec(func)[0]), 
            [t.interface for t in argtypes])
        source_table[fancy_frame] = source_table[func] = get_source_location(func)
        return fancy_frame
    return signature_decorator

def get_spec(func):
    return spec_table.get(func,
        (0, 0, True, ['argv'], None))

def get_source_location(func):
    if func in source_table:
        return source_table[func]
    filename = inspect.getsourcefile(func)
    source = os.path.join("builtin:/", os.path.relpath(filename, "runtime")).decode('utf-8')
    lines, firstline = inspect.getsourcelines(func)
    return source, firstline, firstline+len(lines)

spec_table = {}
source_table = {}
