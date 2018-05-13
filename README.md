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

## Project contents

Every file in the repository written by a person has been
written for reading. Most of the internals are documented
along the code in the comments.

`setup.py` is the utility script for the project. It
provides tools to build the runtime for the language.

`runtime/` contains every file used for building the
runtime. These are python scripts mostly, but a proper
binary runtime is produced.

`build/` directory will be generated when build environment
is configured. This directory will contain all the
dependencies needed for building and processing the contents.

`prelude/` contains source code written in the language.
These files have to be precompiled before the runtime is
capable of loading source code programs on its own.

`lever-0.10.0.grammar` is an
[Attribute grammar][AttributeGrammar] that specifies every
syntactically valid construct in the language. Every tool in
the project references this file for parsing Lever code.

### Runtime

`runtime/goal_standalone.py` configures the RPython to
compile Lever.

`runtime/intro.py` describes how the runtime is built and
which steps are taken before any user program is executed,
also tells how the process is terminated.

`runtime/objects/` defines the type and object system. All
datatypes that are accessible from the `base` -module are
described here along their operations.

### Runtime objects

`runtime/objects/__init__.py` collects runtime objects
together into a single module that can be imported.

`runtime/objects/common.py` constructs the foundations for
the type and object space.

### Prelude

 TODO: Object system has to be there before we are ready to
 run prelude.


 [AttributeGrammar]: https://en.wikipedia.org/wiki/Attribute_grammar
