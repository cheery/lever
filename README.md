# Next-generation Lever

The rewrite improves on...

 * type inferencing
 * computer algebra
 * documentation/structure

Object system is changed to provide subtyping type inference
and provide more invariants for the system to function.
 
Behavior of operators and coercion is changed to provide
computer algebra utilities that are easier to configure and
use.

Documentation is partially implemented with comments and
XML-formatted files along the source code. Inspired by
literal programming.

## Build instructions

Before building you should check that
[prerequisites for building PyPy][pypybuild]
are satisfied by your build environment.

Run the following commands within this directory:

```
./setup.py dependencies
./setup.py compile
```

The first program fetches any dependency that is not usually
present in the system. The last command does the
translation and produces an executable `lever2`.

Bootstrapping of the language is not complete, so to go
further you would have to take the master branch of lever,
compile that too and then run..

```
lever bootstrapper/main.lc
./lever2
```

Author expects that nobody proceeds to do so anytime soon.
There is enough in building just one system.

## Project contents

Every file in the repository written by a person has been
written for reading. Most of the internals are documented
along the code in the comments.

`setup.py` is the utility script for the project. It
provides tools to build the runtime for the language.

`doc/` has documentation that would not form otherwise.

`runtime/` contains every file used for building the
runtime. These are python scripts mostly, but a proper
binary runtime is produced.

`build/` directory will be generated when build environment
is configured. This directory will contain all the
dependencies needed for building and processing the contents.

`prelude/` contains source code written in the language.
These files have to be precompiled before the runtime is
capable of loading source code programs on its own.

`bootstrapper/` contains a bootstrapper written in Lever
0.9.0. Running it precompiles the `prelude/`.

`lever-0.10.0.grammar` is an
[Attribute grammar][AttributeGrammar] that specifies every
syntactically valid construct in the language. Every tool in
the project references this file for parsing Lever code.

`samples/` has some programs written in Lever.

### Documentation

`doc/technical_overview.text` does a quick rundown through the
main features of the language. It is written for programmers
that want to know about Lever.

### Runtime

`runtime/goal_standalone.py` configures the RPython to
compile Lever.

`runtime/intro.py` describes how the runtime is built and
which steps are taken before any user program is executed,
also tells how the process is terminated.

`runtime/objects/` defines the type and object system. All
datatypes that are accessible from the `base` -module are
described here along their operations.

`runtime/interpreter.py` provides an interpreter for
evaluating code. Functions and function-like objects are
defined.

`runtime/json_loader.py` provides a json-loader used to
bootstrap.

`runtime/context.py` describes the execution context that
the programs require.

### Runtime objects

`runtime/objects/__init__.py` collects runtime objects
together into a single module that can be imported.

`runtime/objects/common.py` constructs the foundations for
the type and object space.

`runtime/objects/booleans.py` has methods for booleans.

`runtime/objects/integers.py` has methods for integers.

`runtime/objects/strings.py` has methods for strings.

`runtime/objects/lists.py` has methods for lists.

`runtime/objects/sets.py` has methods for sets.

`runtime/objects/dicts.py` has methods for dictionaries.

`runtime/objects/records.py` has methods for records.

### Bootstrapper

`bootstrapper/main.lc` is the entry point for the compiler.
It sources the grammar from `lever-0.10-0.grammar` and
uses it to parse the `prelude/`, and produce the precompiled
files into the same directory.

### Prelude

`prelude/intro.lc` has the steps the runtime takes to
prepare for compiling and running proper programs.

### Sample programs

`samples/small/fibonacci_and_factorial.lc` recursive variations
of fibonacci and factorial.

`samples/small/simple_generator.lc` shows how generators work.

`samples/small/three_valued_logic.lc` defines a new datatype.

`samples/small/eight_queens.lc` enumerates solutions to 8 queens puzzle.

## Unfinished tasks

 THE NEXT TASK: ??

Consider what the behavior should be for 'binary_operator'
and 'get_coercion_function_type'...

Add immutable constructs, but provide them such that they don't cause
much ado. (operation for setattr as key, for example.)

Tune pattern matchers usable without case construct.

 TODO: The technical documentation should describe how the
       forms end up evaluated.

 TODO: Start exploring the buildup of the inferencer.

 TODO: Consider writing a sample program that uses the whole palette
       of methods that are available for strings.

    a < b
    a == b
    a ++ b
    a.count(b)
    a.endswith(b)
    a in b
    a.is_alpha()
    a.is_digit(base=10)
    a.is_lower()
    a.is_space()
    a.is_upper()
    a.length
    a.lower()
    a.replace(x,y)
    a.rsplit(sep, maxsplit=n)
    a.split(sep, maxsplit=n)
    a.startswith(b)
    a.upper()
    a[x]
    hash(a)
    iter(a)
    a.ljust(width, fillchar=' ')
    a.rjust(width, fillchar=' ')

 TODO: The same for dicts:

    a.length
    a in b
    iter(a) -> produces pairs
    copy(a)
    a.get(key, default)
    a.pop(key)
    a[key] (setitem and getitem)
    a.keys()
    a.items()
    a.values()
    a.update(iterable)

 TODO: the same for lists:

    a == b
    a ++ b
    a in b
    a[b] (setitem)
    a.extend(iterable)
    a.insert(index, obj)
    a.remove(obj)
    a.count(obj)
    a.reverse()
    a.sort(fcmp=cmp)

 TODO: the same for sets

    a.length
    a in b
    iter(a)
    a == b
    copy(a)
    a.clear()
    a.add(b)
    a.update(iterable)
    a.intersection_update(iterable)
    a.difference_update(iterable)
    a.symmetric_difference_update(iterable)
    a.discard(b)
    a.remove(item)
    a.pop()
    a.is_disjoint(iterable)
    a.is_subset(iterable)
    a.is_superset(iterable)
    a.union(iterable), a | b
    a.intersection(iterable), a & b
    a.difference(iterable), a - b
    a.symmetric_difference(iterable), xor(a, b)

 TODO: Consider similar sample programs for lists, dicts, sets, slots.

 TODO: Split lists/sets/dicts properly into immutable/mutable
       constructs.

 TODO: Implement some binary format for binary data,
       and try serialization.

 TODO: Exception handler is a bit like pattern matcher.

 TODO: Add documentation reference building into modules.

 TODO: If module load fails due to module not present, mark the
       item not present and try again from higher scope.

 TODO: Add direct conversions between types.

 TODO: Add slot syntax for record fields.

 TODO: Resume and correct the solve_scope in bootstrapper/main.lc
       Also make the BindCoeffect work correctly with mutable fields.

 TODO: Ensure the datatypes are implemented well. This may require that
       we have some type inference with them already.

 TODO: adjust the grammar to handle `f((x): x*2)`
       the last expression in a call can be a
       closure or a generator.

 TODO: Reconsider how condition block should work if the
 variable does not appear in all evaluation paths and we
 are at the module level.

 Add read and write indexers.

 TODO: https://srfi.schemers.org/srfi-41/srfi-41.html

 TODO: Create stringbuilders.

 TODO: If the case clause contains assignment into same local variable in a
       group, I'd like to create an implicit check that the value extracted
       into that slot is the same.
       Or alternatively would like to disallow that.

 (Now condition block may set the value into a module,
 whereas since assuming repeat may not occur at all, the
 repeat block does assign things locally because we know it
 won't always set it.)

 TODO: When interesting and useful software appears at the
       prelude/intro.lc as result of testing. Put them into
       samples/

 TODO: Write a program that checks variance in an object
 (best effort, false positives).

 TODO: The coercion&conversion subsystem needs to be added
 soon, but it's not clear how to extend it in.
 
 TODO: Lifting between base types and some parametric structures.

 TODO: Implement optionals and variadics to interpreter and
 compiler.

 TODO: read_script should resolve the relative source paths.

 TODO: doc/technical_overview.text is not finished.

 TODO: Create a step-by-step tutorial for beginners that walks
 through the language and teaches to program with it. Add
 interactive 'modules' that allow to test yourself.

 TODO: Implement rationals

Notable things there is in the previous version, not present here yet.

 * full exception handling (full except/finally)
 * libuv bindings systemwide.
 * continuations
 * logging utilities
 * path objects
 * uint8arrays
 * slices
 * vector arithmetic
 * math utilities
 * floats/doubles
 * various math constants
 * naming based on location in a module
 * vmprofiler support
 * networking lib
 * zlib library
 * mman, memory management utility for installing machine code.
 * json library
 * JIT-optimized bytecode interpreter
 * weak references library (not needed as much this time)
 * C API header library
 * C FFI library
 * process spawning library
 * async io through libuv

 * A heap of interesting and useful libraries written in the language
   that may need to be converted.

 [AttributeGrammar]: https://en.wikipedia.org/wiki/Attribute_grammar
 [pypybuild]: http://doc.pypy.org/en/latest/build.html
