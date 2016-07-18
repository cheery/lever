# Lever programming language

 ![Logo](doc/logo.png)

[Lever programming language](http://leverlanguage.com) is dynamically typed language designed & programmed by Henri Tuhola. It has capabilities to absorb features from other languages. Otherwise it is very generic purpose programming system with a hint of inclination towards interactive graphics and audio programming.

Lever is meant for writing whole, standalone interactive computer programs that bundle enough lever runtime along to run without other software installed on the system. The bytecode objects provided by Lever compiler can be distributed without the source code. It is optional for end user to compile anything afterwards.

Lever presents a scoped module architecture where individual modules can be plugged in and out and interactively reloaded while the remaining program is running, this can be done from inside or outside the programs. While a module scope is introduced into a directory, it may also introduce a new language that is used to interpret the loaded files.

As computing power and capabilities increase, even very complex computer programs can be written entirely in smoother, simpler to use and more expressive languages. In past these kind of languages were preferred for writing simple scripts. Lever shares a lot with languages such as Python or Javascript. One thing it doesn't share them is the niche. Lever is meant for designing serious software. 

Despite this, the Lever environment has been designed to be maintained by individuals. Design decisions that would require large dedicated teams to maintain them are feverously avoided. It is meant that people can poke features into the source tree when they need those. They may even develop their own languages on top of Lever as they go. Such newly created micro languages can then feature as laboratories for new features and steer the development of the mainline language.

## Feature list

 * Leverages RPython for rapid language development. Adjustments to design come with lower cost allowing good design choices to appear.
 * Foreign Function Interface which relies on automatically generated C headers. Use of C libraries among dynamically typed code is made simpler than it ever was.
 * Bytecode format inspired by SPIR-V. The format supports quick changes to instruction set, and makes it easy to keep different bytecode related tools updated.
 * Coroutines, and coroutine-enabled event loop, provided by RPython. Crucial tool for writing clean code that may wait asynchronously.
 * Fixed-arity Multimethods. Efficient implementation purposefully incompatible with inheritance. Most operators in lever are defined as multimethods. Doesn't come without drawbacks, but makes lot of things cleaner.
 * Customizable grammars that can be shared between utilities. Made possible with a parsing kernel that copies concepts from [marpa parser](https://jeffreykegler.github.io/Marpa-web-site/). Makes it trivial to provide auxiliary notation for legibility.
 * POSIX-compatible path convention that is enforced across platforms: The programmer and configuration files see POSIX-paths while the operating system see an illusion of obeying its rules regarding file paths.

## How to try it out

 * Clone / download this repository.
 * Run the `./setup.py` while online and have it verify you got all the packages. (only works on ubuntu and debian)
 * `./setup.py compile` will compile the runtime into `lever` -executable.
 * `./lever` or `./lever sample.lc` lets you try it out.

You may need to install some system packages to run the remaining samples on Linux. On freshly installed Ubuntu I needed libsdl2-dev and libsdl2-image-dev to get the examples running.

### Compile remarks

Compiling lever from sources can take up to 3GB of memory until it finishes.

If you find out you're memory constrained, you may want to try compile with `./setup.py compile-nojit`. Compiling Lever without JIT will require considerably less memory (500M).

## Contribution or Use

If you got excited about something you tried out with lever, you may be interested in forking the project. When you do it via github it will inform me of the forks. I may merge in contributions that increase the quality of the project.

But remember that I'm changing things here, and I change them a lot.

## License

Lever comes with MIT license.

License was chosen in appreciation to PyPy -project.
