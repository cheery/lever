# Next-generation Lever

The type inferencing required me to reconsider the object
system in Lever. Since everything changes due to how your
object system changes this motivated a rewrite.

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

The runtime and prelude contents will be described as they
are written. I committed this for overnight sleep.

### Prelude




 [AttributeGrammar]: https://en.wikipedia.org/wiki/Attribute_grammar
