# Lever programming language

 ![Logo](doc/logo.png)

[Lever programming language](http://leverlanguage.com) is dynamically typed language designed & programmed by Henri Tuhola.

## Feature list

 * Leverages RPython for rapid language development. Adjustments to design come with lower cost allowing good design choices to appear.
 * Foreign Function Interface which relies on automatically generated C headers. Use of C libraries among dynamically typed code is made simpler than it ever was.
 * Bytecode format inspired by SPIR-V. The format supports quick changes to instruction set, and makes it easy to keep different bytecode related tools updated.
 * Coroutines, and coroutine-enabled event loop, provided by RPython. Crucial tool for writing clean code that may wait asynchronously.
 * Fixed-arity Multimethods. Efficient implementation purposefully incompatible with inheritance. Most operators in lever are defined as multimethods. Doesn't come without drawbacks, but makes lot of things cleaner.
 * Customizable grammars that can be shared between utilities. Made possible with a parsing kernel that copies concepts from [marpa parser](https://jeffreykegler.github.io/Marpa-web-site/). Makes it trivial to provide auxiliary notation for legibility.

## How to try it out

 * Clone / download this repository.
 * Run the `./setup.py` while online and have it verify you got all the packages. (only works on ubuntu and debian)
 * `./setup.py compile` will compile the runtime into `lever` -executable.
 * `./lever` or `./lever sample.lc` lets you try it out.

You may need to install some system packages to run the remaining samples on Linux. On freshly installed Ubuntu I needed libsdl2-dev and libsdl2-image-dev to get the examples running.

## Contribution or Use

If you got excited about something you tried out with lever, you may be interested in forking the project. When you do it via github it will inform me of the forks. I may merge in contributions that increase the quality of the project.

But remember that I'm changing things here, and I change them a lot.

## License

Lever comes with MIT license.

License was chosen in appreciation to PyPy -project.
