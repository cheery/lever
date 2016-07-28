from rpython.rlib import rstring
from space import *
import os
import sys

class Prefix(Object):
    pass

class PosixPrefix(Prefix):
    def __init__(self, label, is_absolute):
        self.label = label
        self.is_absolute = is_absolute

    def getattr(self, name):
        if name == u"is_absolute":
            return boolean(self.is_absolute)
        if name == u"label":
            return String(self.label)
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"is_absolute":
            self.is_absolute = is_true(value)
            return null
        if name == u"label":
            if not isinstance(value, String):
                raise OldError(u"label must be a string")
            if value.string.count(u"/") + value.string.count(u":") > 0:
                raise OldError(u"label must not contain '/' or ':'")
            self.label = value.string
            return null
        return Object.setattr(self, name, value)

class URLPrefix(Prefix):
    def __init__(self, protocol, domain):
        self.protocol = protocol
        self.domain = domain

    def getattr(self, name):
        if name == u"protocol":
            return String(self.protocol)
        if name == u"domain":
            return String(self.domain)
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"protocol":
            if not isinstance(value, String):
                raise OldError(u"protocol must be a string")
            if value.string.count(u"/") + value.string.count(u":") > 0:
                raise OldError(u"protocol must not contain '/' or ':'")
            self.label = value.string
            return null
        if name == u"domain":
            if not isinstance(value, String):
                raise OldError(u"domain must be a string")
            if value.string.count(u"/") > 0:
                raise OldError(u"domain must not contain '/'")
            self.label = value.string
            return null
        return Object.setattr(self, name, value)

class Path(Object):
    def __init__(self, prefix, pathseq):
        self.prefix = prefix
        self.pathseq = pathseq

    def getattr(self, name):
        if name == u"basename":
            if len(self.pathseq) == 0:
                return String(u"")
            return String(self.pathseq[-1])
        if name == u"prefix":
            return self.prefix
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"basename":
            if not isinstance(value, String):
                raise OldError(u"basename must be a string")
            if value.string.count(u"/") > 0:
                raise OldError(u"basename must not contain slash character")
            if len(self.pathseq) == 0:
                self.pathseq.append(value.string)
            else:
                self.pathseq[-1] = value.string
            return null
        if name == u"prefix":
            if isinstance(value, Prefix):
                self.prefix = value
            else:
                raise OldError(u"prefix must be a valid prefix object, for now.")
        return Object.setattr(self, name, value)

    def repr(self):
        return u"path(" + String(stringify(self)).repr() + u")"

    def drop_slash(self):
        L = len(self.pathseq)
        if L > 0 and self.pathseq[L-1] == u"":
            self.pathseq.pop()

@Path.method(u"relpath", signature(Path, Object, optional=1))
def Path_relpath(dst, rel):
    if rel:
        rel = abspath(to_path(rel))
    else:
        rel = getcwd()
    if isinstance(rel.prefix, PosixPrefix) and isinstance(dst.prefix, PosixPrefix):
        if dst.prefix.label != rel.prefix.label and dst.prefix.label != u"":
            return dst
        dst = concat(rel, dst)
        C = min(len(dst.pathseq), len(rel.pathseq))
        for i in range(C):
            if dst.pathseq[i] != rel.pathseq[i]:
                C = i
                break
        result = []
        for n in range(C, len(rel.pathseq)):
            result.append(u"..")
        for m in range(C, len(dst.pathseq)):
            result.append(dst.pathseq[m])
        return Path(PosixPrefix(u"", False), result)
    if isinstance(rel.prefix, PosixPrefix) and isinstance(dst.prefix, URLPrefix):
        return dst
    else:
        raise OldError(u"Path_relpath: missing feature, file an issue or implementn")

@Path.builtin_method
@signature(Path, String)
def push(path, seq):
    newpath = parse(seq.string)
    if is_absolute(newpath):
        path.prefix = duplicate_prefix(newpath.prefix)
        path.pathseq = newpath.pathseq
    else:
        pathseq_ncat(path.pathseq, newpath.pathseq)
    return null

@Path.builtin_method
@signature(Path)
def get_os_path(path):
    return String(os_stringify(path))

@Path.method(u"to_string", signature(Path))
def Path_to_string(path):
    return String(stringify(path))

@Path.instantiator
@signature(Object)
def _(obj):
    if isinstance(obj, String):
        return parse(obj.string)
    elif isinstance(obj, Path):
        return duplicate(obj)
    raise OldError(u"path() expected string or path object.")

@PosixPrefix.instantiator
def _(argv):
    obj = PosixPrefix(u"", False)
    if len(argv) >= 1:
        obj.setattr(u"label", argv[0])
    if len(argv) >= 2:
        obj.setattr(u"is_absolute", argv[1])
    return obj

@URLPrefix.instantiator
def _(argv):
    obj = URLPrefix(u"", u"")
    if len(argv) >= 1:
        obj.setattr(u"domain", argv[0])
    if len(argv) >= 2:
        obj.setattr(u"protocol", argv[1])
    return obj

# The following generic path parsing function handles both unix and nt paths along URLs.
def parse(string, nt=False):
    prefix = None
    pathseq = []
    buf = []
    state = 0
    ch = u""
    for ch in string:
        slash = (ch == u"/" or (nt and ch == u"\\"))
        # state == 0: {label, protocol, name}
        if state == 0: 
            if slash:
                state = 4 # Potential absolute path.
            elif ch == u":":
                state = 2 # there is a label in the buffer.
            else:
                buf.append(ch)
                state = 1
        # state == 1: {label, protocol, name}
        elif state == 1:
            if slash:
                name, buf = u''.join(buf), []
                pathseq.append(name)
                prefix = PosixPrefix(u"", False)
                state = 8 # ordinary path.
            elif ch == u":":
                state = 2 # there is a label in the buffer.
            else:
                buf.append(ch)
        # state == 2: labelled {label, name}
        elif state == 2:
            if slash:
                state = 4 # Potential absolute path.
            else:
                label, buf = u''.join(buf), []
                prefix = PosixPrefix(label, is_absolute=False)
                state = 8 # ordinary path.
                buf.append(ch)
        # state == 4: potential absolute path {label, protocol}
        #             backslash, nt-absolute or nt-UNC path. {protocol}
        elif state == 4:
            if slash:
                protocol, buf = u''.join(buf), []
                prefix = URLPrefix(protocol, u"")
                if ch == u"/": # ensure nobody makes getcwd return backslashed URLs.
                    nt = False  # and that backslashes aren't interpreted in URLs.
                state = 6 # Starts collecting domain segment.
            else:
                label, buf = u''.join(buf), []
                prefix = PosixPrefix(label, is_absolute=True)
                state = 8 # ordinary path.
                buf.append(ch)
        # state == 6: URL or nt-UNC {domain}
        elif state == 6:
            if slash and isinstance(prefix, URLPrefix):
                domain, buf = u''.join(buf), []
                prefix.domain = domain
                state = 8 # ordinary path.
            elif slash:
                raise OldError(u"path parser state corruption")
            else:
                buf.append(ch)
        # state == 8: uniform path. {name}
        elif state == 8:
            if slash:
                name, buf = u''.join(buf), []
                pathseq.append(name)
                state = 8 # ordinary path.
            else:
                buf.append(ch)
        else:
            raise OldError(u"path parser state corruption")
    if state == 0:
        prefix = PosixPrefix(u"", is_absolute=False)
    elif state == 1:
        prefix = PosixPrefix(u"", is_absolute=False)
        pathseq.append(u''.join(buf))
    elif state == 2:
        label, buf = u''.join(buf), []
        prefix = PosixPrefix(label, is_absolute=False)
    elif state == 4:
        label, buf = u''.join(buf), []
        prefix = PosixPrefix(label, is_absolute=True)
        pathseq.append(u''.join(buf))
    elif state == 6 and isinstance(prefix, URLPrefix):
        domain, buf = u''.join(buf), []
        prefix.domain = domain
    elif state == 8 and isinstance(prefix, Prefix):
        pathseq.append(u''.join(buf))
    else:
        raise OldError(u"path parser state corruption")
    return Path(prefix, pathseq_ncat([], pathseq))

@operators.concat.multimethod_s(String, Path)
def _(a, b):
    return concat(parse(a.string), b)

@operators.concat.multimethod_s(Path, String)
def _(a, b):
    return concat(a, parse(b.string))

@operators.concat.multimethod_s(Path, Path)
def concat(a, b):
    if is_absolute(b):
        return Path(duplicate_prefix(b.prefix), list(b.pathseq))
    pathseq = pathseq_ncat(list(a.pathseq), b.pathseq)
    return Path(duplicate_prefix(a.prefix), pathseq)

def pathseq_ncat(pathseq, tail):
    if len(pathseq) > 0 and pathseq[-1] == u"":
        pathseq.pop()
    slash = False
    for name in tail:
        slash = False
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

def is_absolute(pathobj):
    prefix = pathobj.prefix
    if isinstance(prefix, PosixPrefix):
        return prefix.is_absolute
    return True

def duplicate(path):
    return Path(duplicate_prefix(path.prefix), list(path.pathseq))

def duplicate_prefix(prefix):
    if isinstance(prefix, PosixPrefix):
        return PosixPrefix(prefix.label, prefix.is_absolute)
    if isinstance(prefix, URLPrefix):
        return URLPrefix(prefix.protocol, prefix.domain)
    assert False, "corruption"

def stringify(path, nt=False):
    if isinstance(path, String):
        path = parse(path.string)
    if not isinstance(path, Path):
        raise OldError(u"expected a path object")
    prefix = path.prefix
    if isinstance(prefix, URLPrefix):
        string = prefix.protocol
        if len(string) > 0:
            string += u":"
        if nt and string == u"":
            string += ur"\\" + prefix.domain + u"\\" 
        else:
            string += ur"//" + prefix.domain
            if len(path.pathseq) > 0:
                string += u"/"
        string += stringify_pathseq(path.pathseq, nt)
        return rstring.assert_str0(string)
    elif isinstance(prefix, PosixPrefix):
        if prefix.is_absolute:
            string = stringify_pathseq([u""] + path.pathseq, nt)
        elif len(path.pathseq) > 0 and path.pathseq[0].count(u":") > 0:
            string = stringify_pathseq([u"."] + path.pathseq, nt)
        else:
            string = stringify_pathseq(path.pathseq, nt)
        if string == u"":
            string = u"."
        if prefix.label != u"":
            string = prefix.label + u":" + string
        return rstring.assert_str0(string)
    else:
        raise OldError(u"custom prefix passed to stringification [corruption]")

def stringify_pathseq(pathseq, nt=False):
    if nt:
        for name in pathseq:
            if name.count(u"\\") > 0:
                raise OldError(ur"nt_stringify cannot stringify file/directory names that contain '\\'")
        return u"\\".join(pathseq)
    return u"/".join(pathseq)

def getcwd():
    return os_parse(os.getcwd().decode('utf-8'))

def chdir(path):
    os.chdir(os_stringify(path).encode('utf-8'))

@cast_for(Path)
def to_path(obj):
    if isinstance(obj, String):
        return parse(obj.string)
    elif isinstance(obj, Path):
        return obj
    else:
        raise OldError(u"expected path")

def directory(path):
    path = duplicate(path)
    path.drop_slash()
    if len(path.pathseq) == 0:
        raise OldError(u"cannot take directory(), too short path")
    path.pathseq.pop()
    return path

def abspath(path):
    if is_absolute(path):
        return path
    return concat(getcwd(), path)

# nt stands for "non-technology"
nt_parse = lambda string: parse(string, nt=True)
nt_stringify = lambda path: stringify(path, nt=True)

if sys.platform == "win32":
    os_parse = nt_parse
    os_stringify = nt_stringify
else:
    os_parse = parse
    os_stringify = stringify
