from rpython.rlib import rfile
from json_loader import read_json_file
from objects.core import *
from objects import core, modules, chaff
from objects import variables
#from context import (
#    CoeffectModuleCell,
#    init_executioncontext,
#    construct_coeffect,
#    w_call_with_coeffects )
import interpreter
import os

def new_entry_point(config):
    base_module = modules.Module()
    for name, obj in variables.items():
        core.set_attribute(base_module,
            core.wrap(name), obj)
    for name, obj in interpreter.variables.items():
        core.set_attribute(base_module,
            core.wrap(name), obj)
    base_module.loaded = True
    rt_mspace = modules.ModuleSpace(String(u"runtime://"), [], None)
    rt_mspace.loaded[u"base"] = base_module
    def entry_point(raw_argv):
        try:
            mspace = modules.ModuleSpace(
                local = String(u'prelude2'),
                env = [base_module],
                loader = w_json_loader,
                parent = rt_mspace)
            module = call(modules.w_import, [mspace, String(u"intro")])
            call(get_attribute(module, String(u"main")), [], 0)
        except OperationError as tb:
            os.write(0, "Traceback (most recent call last):\n")
            for trace_entry in reversed(tb.trace):
                if isinstance(trace_entry, core.BuiltinTraceEntry):
                    src = trace_entry.sourcefile
                    name = trace_entry.name
                    s = "  %s:%d: %s\n" % (src, trace_entry.lno0, name)
                    os.write(0, s)
                elif isinstance(trace_entry, interpreter.SourceLocBuilder):
                    loc, sources = trace_entry.build_loc()
                    col0 = unwrap_int(loc[0])
                    lno0 = unwrap_int(loc[1])
                    col1 = unwrap_int(loc[2])
                    lno1 = unwrap_int(loc[3])
                    srci = unwrap_int(loc[4])
                    src = cast(sources[srci], String).string.encode('utf-8')
                    s = "  %s:%d:\n%s\n" % (src, lno0,
                        format_source_location(col0, lno0, col1, lno1, src))
                    os.write(0, s)
                else:
                    print('  *** UNKNOWN ENTRY ***')
            name = chaff.get_name(tb.error.atom).encode('utf-8')
            if len(tb.error.items) == 0:
                os.write(0, name + "\n")
            else:
                ss = []
                for item in tb.error.items:
                    ss.append(chaff.get_name(item).encode('utf-8'))
                os.write(0, name + "(" + ", ".join(ss) + ")" + "\n")
            return 1
        return 0
    return entry_point

def core_diagnostics(base_module):
    print "CORE DIAGNOSTICS"
    for name in base_module.cells:
        print("VARIABLE %s" % name.encode('utf-8'))
        obj = core.get_attribute(base_module, core.wrap(name))
        prop = core.get_properties(obj)
        if prop is None:
            continue
        docref = prop.get(modules.atom_documentation, None)
        if docref is None:
            print("  ERROR: PROPERTIES BUT NO DOCREF")
            continue
        if isinstance(docref, core.Compound):
            if docref.atom is modules.atom_docref:
                s = docref.items[1]
                if isinstance(s, core.String):
                    print("  documentation name: %s" % s.string.encode('utf-8'))
        print("  HAS PROPERTIES & DOCREF")

#     BasicIO = construct_coeffect([
#         (u"input", False), (u"print", False)], base_module)
#     base_module.assign(u"BasicIO", BasicIO)

#         init_executioncontext({
#             BasicIO: construct_record([
#                 (u"input", False, w_input),
#                 (u"print", False, w_print) ])
#         })
 
# Especially when tired and frustrated, well-formatted information
# can be such a morale boost, that one shouldn't skimp on it.
def format_source_location(col0, lno0, col1, lno1, src):
    try:
        fd = rfile.create_file(src, 'rb')
        try:
            lines = fd.read().splitlines()
        finally:
            fd.close()
    except IOError as io:
        return "    *** %s ***" % os.strerror(io.errno)
    lno0 = min(len(lines), max(0, lno0-1))
    lno1 = min(len(lines), max(0, lno1))
    assert lno0 >= 0 # RPython was unable to check this
    show_lines = lines[lno0:lno1]
    # Indentation is dropped such that the line plants neatly down.
    trim = 0
    for line in show_lines:
        trim = max(trim, len(line))
    for line in show_lines:
        max_trim = len(line) - len(line.lstrip())
        if max_trim != len(line): # Skip blank lines
            trim = min(trim, max_trim)
    assert trim >= 0 # RPython was unable to check this
    show_lines = [line[trim:] for line in show_lines]
    # The trail points out the column location, it is helpful
    # in identifying the source of error.
    if col1 - col0 < 2:
        trail = " "*(col0-trim) + "^"
    else:
        trail = " "*(col0-trim) + "^" + "-"*(col1-col0-2) + "^"
    return "    " + "\n    ".join(show_lines + [trail])

@builtin(1)
def w_json_loader(mspace, name):
    mspace = cast(mspace, modules.ModuleSpace)
    name = cast(name, String).string
    local = cast(mspace.local, String).string
    src = local + u"/" + name + u".lc.json"
    try:
        obj = read_json_file(String(src))
    except OperationError as oe:
        if oe.error.atom is e_IOError:
            raise error(e_ModuleError)
        raise
    env = mspace.env
    script, module = interpreter.read_script(obj,
        {u'import': prefill(modules.w_import, [mspace])}, env, src)
    call(script, [], 0)
    return module
