# Next-generation Lever

Note: At the moment this project does not run properly. I uploaded
intermediary results of the new VM. The new frontend is slightly unstable
and differs from the previous one.

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

`bootstrapper.lc` contains a bootstrapper written in Lever
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

 THE NEXT TASK: Broad stage of type inference.

 Remove the 'Note' when things are working ok.

 It's a depth first search, with markers to close cyclic
 clauses.

 It can be done in single flush if the designer is careful.

 TODO: Write some IR loading code into prelude.

 TODO: Restore the remaining functionality.

 TODO: Implement some binary format for binary data,
       and try serialization.

 TODO: Add documentation reference building into modules.

 TODO: Re-implement coeffects.

 TODO: Ensure the datatypes are implemented well. This may require that
       we have some type inference with them already.

 TODO: adjust the grammar to handle `f((x): x*2)`
       the last expression in a call can be a
       closure or a generator.

 TODO: Reconsider how condition block should work if the
 variable does not appear in all evaluation paths and we
 are at the module level.

 Add read and write indexers.

 https://srfi.schemers.org/srfi-41/srfi-41.html -like behavior has been
 implemented, but it should be probably documented somewhere.

 TODO: Create stringbuilders.

 TODO: When interesting and useful software appears at the
       prelude/intro.lc as result of testing. Put them into
       samples/

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
