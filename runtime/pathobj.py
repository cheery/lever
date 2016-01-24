from space import *
import os
import sys
import operators

# Again we have some expectations that other platforms do not suck.
# TODO: read NT path conventions.
if sys.platform == "win32":
    #os_path_separator = u"\\"
    os_path_decode = lambda string: string.replace(u"\\", u"/").replace(u"^", u"\\")
    os_path_encode = lambda string: string.replace(u"\\", u"^").replace(u"/", u"\\")
else:
    #os_path_separator = u"/"
    os_path_decode = lambda string: string
    os_path_encode = lambda string: string

class Path(Object):
    def __init__(self, pathseq, is_absolute, label):
        self.pathseq = pathseq
        self.is_absolute = is_absolute
        self.label = label

    def getattr(self, name):
        if name == u"basename":
            if len(self.pathseq) == 0:
                return String(u"")
            return String(self.pathseq[-1])
        if name == u"is_absolute":
            return boolean(self.is_absolute)
        if name == u"label":
            return String(self.label)
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"basename":
            if not isinstance(value, String):
                raise Error(u"basename must be a string")
            if value.string.count(u"/") > 0:
                raise Error(u"basename must not contain slash character")
            if len(self.pathseq) == 0:
                self.pathseq.append(value.string)
            else:
                self.pathseq[-1] = value.string
            return null
        if name == u"is_absolute":
            self.is_absolute = is_true(value)
            return null
        if name == u"label":
            if not isinstance(value, String):
                raise Error(u"label must be a string")
            self.label = value.string
            return null
        return Object.setattr(self, name, value)

    def repr(self):
        return u"path(" + String(path_string(self, u"/")).repr() + u")"

@Path.builtin_method
@signature(Path, String)
def push(path, seq):
    newpath = parse_path(seq.string)
    if newpath.is_absolute:
        path.is_absolute = newpath.is_absolute
        path.label = newpath.label
        path.pathseq = newpath.pathseq
        return null
    pathseq_ncat(path.pathseq, newpath.pathseq)
    return null

@Path.builtin_method
@signature(Path)
def get_os_path(path):
    return String(os_path_string(path))

@Path.instantiator
@signature(Object)
def _(obj):
    if isinstance(obj, String):
        return parse_path(obj.string)
    elif isinstance(obj, Path):
        return Path(list(obj.pathseq), obj.is_absolute, obj.label)
    raise Error(u"path() expected string or path object.")

def pathseq_ncat(pathseq, tail):
    if len(pathseq) > 0 and pathseq[-1] == u"":
        pathseq.pop()
    slash = False
    for name in tail:
        if name == u"" or name == u".":
            slash = True
            continue
        if name == u".." and len(pathseq) > 0 and pathseq[-1] != u"..":
            pathseq.pop()
        else:
            pathseq.append(name)
    if slash:
        pathseq.append(u"")
    return pathseq

def os_parse_path(string):
    return parse_path(os_path_decode(string))

def os_path_string(path):
    return os_path_encode(path_string(path))

def getcwd():
    return os_parse_path(os.getcwd().decode('utf-8'))

# parse posix path.
def parse_path(string, parse_label=True):
    pathseq = string.split(u"/")
    head = pathseq.pop(0)
    if head.count(u":") > 0 and parse_label:
        label, head = head.split(u":", 1)
    else:
        label = u""
    is_absolute = (head == u"" and len(pathseq) > 0)
    return Path(pathseq_ncat([head], pathseq), is_absolute, label)

def path_string(path, path_separator=u"/"):
    if isinstance(path, String):
        path = parse_path(path.string)
    if not isinstance(path, Path):
        raise Error(u"expected a path object")
    if path.is_absolute:
        string = path_separator + path_separator.join(path.pathseq)
    else:
        if len(path.pathseq) == 0 or path.pathseq[0].count(u":") > 0:
            string = path_separator.join([u"."] + path.pathseq)
        else:
            string = path_separator.join(path.pathseq)
        if path.label != u"":
            string = path.label + u":" + string
    return string

@operators.concat.multimethod_s(String, Path)
def _(a, b):
    return path_op_concat(parse_path(a.string), b)

@operators.concat.multimethod_s(Path, String)
def _(a, b):
    return path_op_concat(a, parse_path(b.string))

@operators.concat.multimethod_s(Path, Path)
def path_op_concat(a, b):
    if b.is_absolute:
        return Path(list(b.pathseq), b.is_absolute, b.label)
    pathseq = pathseq_ncat(list(a.pathseq), b.pathseq)
    return Path(pathseq, a.is_absolute, a.label)

