# Lever programming language

 ![Logo](doc/logo.png)

[Lever programming language](http://leverlanguage.com) is dynamically typed language designed & programmed by Henri Tuhola. It has capabilities to absorb features from other languages. Otherwise it is very generic purpose programming system with a hint of inclination towards interactive graphics and audio programming.

Lever used to be a study piece. Then it started gaining useful features. I realised it could be something worthwhile if worked on.

Lever is meant for writing whole, standalone interactive computer programs that bundle enough lever runtime along to run without other software installed on the system. The bytecode objects provided by Lever compiler can be distributed without the source code. It is optional for end user to compile anything afterwards.

Lever presents a scoped module architecture where individual modules can be plugged in and out and interactively reloaded while the remaining program is running, this can be done from inside or outside the programs. While a module scope is introduced into a directory, it may also introduce a new language that is used to interpret the loaded files.

As computing power and capabilities increase, even very complex computer programs can be written entirely in smoother, simpler to use and more expressive languages. In past these kind of languages were preferred for writing simple scripts. Lever shares a lot with languages such as Python or Javascript. One thing it doesn't share them is the niche. Lever is meant for designing serious software.

Absorption of language features is possible because it is possible to add new rules into the grammar and into the compiler, or remove existing ones if they are not used. The newly gained language can be then either built into custom distribution or attached into a scope when running an ordinary distribution. More ways to extend the language in less invasive ways are also on planning stage.

Advantages of Python to lever is that it's perfectly good for writing scripts. It doesn't change often, it's coming along nearly every Linux distribution. But this turn around fast if you consider to do interactive graphics intensive desktop apps on Python.

Lever has most basic vector arithmetic supported by the runtime and there is hardly competiting implementations because the one in runtime will be very good and supported. And there's intent to have excellent graphics libraries embedded into the lever runtime in the future. Your vector algebra will be as clear as if copied from an algebra book.

Some graphical demos already run on lever: Here's a program from samples/gl_top/main.lc that runs an animated blender-imported on top on of a table. Requires OpenGL4:

 ![./lever samples/gl_top/main.lc](marketing/gl_top_screenshot.png)

Although javascript runs everywhere, writing it is sheer torture of capable souls. Every callback pyramid/promise forest/async keyword crowds your mind and slows down development to snail pace. And even if you manage to figure out some nice way to avoid asynchronous code, you will find yourself writing those glMatrix operations in assembly notation. They feel like a fortran blast from past, and most of us are not that retro that we write and maintain algebra expressions in assembly style.

Clean slate under lever allowed its eventloop to combine with continuations, turning into a complete rethought of how to write code that waits for events. Async lever code is as simple to work with as what sync code is.

Lever doesn't have a global module space like Python has. Instead you can create scopes for modules and chain them together. Once the work has been finished in Lever's module resolution, it'll be a 10-liner to create a plugin system that isn't a hack.

Despite this, the Lever environment has been designed to be maintained by individuals. Design decisions that would require large dedicated teams to maintain them are feverously avoided. It is meant that people can poke features into the source tree when they need those. They may even develop their own languages on top of Lever as they go. Such newly created micro languages can then feature as laboratories for new features and steer the development of the mainline language.

Python3 is so stable that it didn't provide that many improvements over Python2 to make the breaking worthwhile. If you are looking for something more volatile but better, something like explodes in your hands, you may like to look into Lever.

Works on Windows if not blown.

## Feature list

 * Leverages RPython for rapid language development. Adjustments to design come with lower cost allowing good design choices to appear.
 * Foreign Function Interface which relies on automatically generated C headers. Use of C libraries among dynamically typed code is made simpler than it ever was.
 * Bytecode format inspired by SPIR-V. The format supports quick changes to instruction set, and makes it easy to keep different bytecode related tools updated.
 * Coroutines, and coroutine-enabled event loop, provided by RPython. Crucial tool for writing clean code that may wait asynchronously.
 * Module resolution scopes.
 * Fixed-arity Multimethods. Efficient implementation purposefully incompatible with inheritance. Most operators in lever are defined as multimethods. Doesn't come without drawbacks, but makes lot of things cleaner.
 * Customizable grammars that can be shared between utilities. Made possible with a parsing kernel that copies concepts from [marpa parser](https://jeffreykegler.github.io/Marpa-web-site/). Makes it trivial to provide auxiliary notation for legibility.
 * POSIX-compatible path convention that is enforced across platforms: The programmer and configuration files see POSIX-paths while the operating system see an illusion of obeying its rules regarding file paths.
 * Vector and quaternion arithmetic in runtime that can be optimized.

## Use cases

TODO, also may want to sprinkle some (already running) code examples into introduction to immediately prove some claims.


### Console - modules, compiler, bytecode usecase

Although it is surrounded by syntax, "import" is just a function in your module. The result is you can do weird parlour tricks by importing from other modules.

Python tried to dictate and force me to not change default environment of a script. It was one of those decisions that drove me to design my own language that would not have this handicap.

Lever console is something that is not implemented in the runtime. It's an application present in app/main.lc. Here you have a shortened version of that program:

    import base, compiler

    console = :module("console", base)
        dir = getcwd()
        name = "console"
        %"import" = Import(dir,
            ModuleScope(dir, %"import".scope.parent))

    while true
        string = input(">> ")
        code = compiler.read_string(string)
        print(repr(load(code)(console)))

As shown above, the code is explicitly compiled, explicitly loaded and the environment where it runs is explicitly created and passed in. You can absolutely replace one or all of these pieces with your own.

Like a firearm, you can disassemble Lever's way to load code and then assemble it back up. And like with firearms, you bear the consequences of using the power it provides. I admit the whole lever is just a tool. It leaves the moral decisions to whoever uses it.

### Collision checking between shapes - Custom multimethods usecase

Lever has fixed-arity multimethods that resolve to a value to call in place of a multimethod. If no match is made, you will observe a call to .default -value.

Lever multimethods do not obey inheritance rules. They also may start to accumulate methods if you reload modules. It is very easy to reason about their behavior though.

I figured out how awesome they are at implementing operators such as "+", "-" and so on. And thought, if you don't do some stupid things they really shine at what they are good at.

To showcase multimethods, I got this collision checking between different kinds of shapes:

    collides = multimethod(2)

    collides[[Sphere, Sphere]] = (sphere1, sphere2):
        d = sphere1.pos - sphere2.pos
        r = sphere1.r + sphere2.r
        return r*r <= dot(d, d)

    collides[[Sphere, Plane]] = (sphere, plane):
        d = dot(plane.normal, sphere.pos) - plane.d
        return sphere.radius <= d

    # Parallel planes do not collide
    collides[[Plane, Plane]] = (plane1, plane2):
        return abs(dot(plane1.normal, plane2.normal)) != 1.0

    collides.default = (a, b):
        return collides.call_suppressed(b, a)
        # If an exception is added to catch suppress here, you could introduce
        # some behavior even after an attempted default call failed.
        # See 'Contribution or Use'

Here I think it's perfect, because you don't do anything with inheritance when you have geometric shapes. Also, these different shapes tend to be really well-defined. So you can live-reload every method here until you get it correct.

Why would you want collision checkers like these? Well, since Unity3D doesn't have them, there's very good chance all physics engines do not expose the collision checking functions they have. Therefore you're going very dry if you wanted to check whether there's space for something before you instantiate it into the scene! You might have to implement these yourself. In that case multimethods might be something to consider.

### Script-relative resource loading - POSIX-path object usecase

In most languages, when I've had resources associated with scripts it's been complicated to refer to those files.

Relative references should be something even simplest applications should handle right. Lever makes it easy. Every module loaded gets 'dir' -variable which tells the current directory where the script was loaded from:

    import fs

    text = fs.read_file(dir ++ "greeting_message.txt")
    print(text)

Below you see how it'd change if you wanted your assets into an adjacent directory:

    assets = dir ++ "../assets"
    text = fs.read_file(assets ++ "greeting_message.txt")

The system is forwards compatible to reading from servers and from zipfiles.

### Distance between two lines - vector arithmetic usecase

Vectors, matrices and quaternions are ubiquitous in graphics applications.

But so far I've seen them implemented by third party libraries. But it's not common for different programs to use the same library. It makes it difficult to share code and graphic data between programs.

To Lever I took the semantics from GLSL -language because they were fairly good. Most of the functionality is implemented as multimethods to allow extension.

I care that the language I should use works for solving geometry problems.

Line to line distance is quite simple thing to calculate, but it should give a glimpse of how clean vector arithmetic can be in Lever:

    line_line_distance = (p, q):
        u = p[1] - p[0]
        v = q[1] - q[0]
        c = q[0] - p[0]
        d = cross(u, v)
        return abs(dot(c, d)) / d

    line_line_nearest = (p, q):
        u = p[1] - p[0]
        v = q[1] - q[0]
        c = q[0] - p[0]

        a = dot(u, u)
        b = dot(u, v)
        c = dot(v, v)
        d = dot(u, c)
        e = dot(v, c)

        div = a*c - b*b
        if div == 0.0 # lines are parallel or either one is degenerate
            return :exnihilo()
                s = 0.0
                if b > c
                    t = d/b
                else
                    t = e/c
        return :exnihilo()
            s = (b*e - c*d) / div
            t = (a*e - b*d) / div

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

Because it is so fast to come up with new features, much of Lever development is demand driven. You may discover features that should be implemented by the runtime, or by a lever library.

When that happens, you have two options:

 * Implement the feature yourself. Make a pull request to not having to maintain your own version.
 * Write an user story, article or feature proposal. Send it to my email or file an issue in github.

## License

Lever comes with MIT license.

License was chosen in appreciation to PyPy -project.
