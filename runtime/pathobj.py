from space import *
import sys

# Again we have some expectations that other platforms do not suck.
if sys.platform == "win32":
    os_path_separator = u"\\"
else:
    os_path_separator = u"/"

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
@signature(Path)
def copy(path):
    return Path(list(path.pathseq), path.is_absolute, path.label)

@Path.builtin_method
@signature(Path, String)
def push(path, seq):
    newpath = posix_path(seq.string)
    if newpath.is_absolute:
        path.is_absolute = newpath.is_absolute
        path.label = newpath.label
        path.pathseq = newpath.pathseq
        return null
    pathseq_ncat(path.pathseq, newpath.pathseq)
    return null

@Path.instantiator
@signature(String)
def _(obj):
    return posix_path(obj.string)

def posix_path(string, parse_label=True):
    pathseq = string.split(u"/")
    head = pathseq.pop(0)
    if head.count(u":") > 0 and parse_label:
        label, head = head.split(u":", 1)
    else:
        label = u""
    is_absolute = (head == u"" and len(pathseq) > 0)
    return Path(pathseq_ncat([head], pathseq), is_absolute, label)

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

def os_path_string(path):
    return path_string(path, os_path_separator) 

def path_string(path, path_separator):
    if isinstance(path, String):
        path = posix_path(path.string)
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
