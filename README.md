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

Every single usecase here features functionality. Every snippet of code runs in the interpreter and works as advertised.

### Make 'BEGIN', 'END' denote a block, syntax absorption, rapid language development usecase

Trends, fashions, fads. They are very real at programming world, and many old languages are unable to follow along. Or then they follow along dragging everyone into it at once, and we get Python3 async/await -keywords. 
Rare are the days when there comes a new insight to programming that require changes into language grammar, but those days do happen at times. They could happen more often. 

If you're used to not being able to change the grammar of your programming language, the following may offend you:

    block =>
        {"BEGIN" statements "END"}
        {"BEGIN" statements %newline "END"}

If you add this into the `lever-0.8.0.grammar`, the following code will compile and run:

    hello = (foo): BEGIN
    if foo.endswith("3") BEGIN
    print("foo", foo)
    END
    else BEGIN print("baa", foo) END
    END

    hello("123-c-432")
    hello("423-b-213")
    hello("423-b-212")

There's some rationale to showing this with `BEGIN` and `END` rather than {}. The braces are reserved for dictionaries in lever-0.8.0. The lowcase words 'begin' and 'end' are in use at lib/vr.lc and lib/vulkan.lc. Since the grammar in lever directory is used by all of the compilers we have, changing it can cause ambiguities or change the meaning of the library modules.

Thanks to use of context free grammar, if you don't remove any existing rules, then doing `./setup.py compile-lib-all` will reveal where the new rules introduce ambiguities.

Due to the existing rules being still in place, you may notice every variation of BEGIN and END is not recognized. For example if you add BEGIN to new line or indent it, it will most likely produce a syntax error. This happens due to how lever language recognizes indentation.

Source files are parsed from left to right and there's an indenter before the parsing engine. If the indenter notes it could insert one of "indent", "dedent" or "newline" tokens, it will first check whether the parser anticipates for one. If it does, it will insert one into the stream.

Practically you could copy the grammar into your own directory and hack it to your preferences or (hopefully) practical needs. It would allow infinite customizability into the syntax. Some short adjustments would have to be done to lever runtime to allow it.

It doesn't look that horrible if you accept that programming languages are merely user interfaces for humans and then treat them as such.

The features allowing this usecase makes the development of Lever very fast. It is very low stress operation to introduce new syntactic rules when you need them. You might like to change the grammar files to accomodate for disabilities, port old code or just troll your coding companions.

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

## How to setup your development environment

First of all you need a good text editor for writing lever code. Avoid wordpad and notepad, they aren't good for this. Here are some you could try:

 * Visual Studio Code - Easily available on Windows and Linux.
 * GEdit              - Easily available on Linux.
 * Vim                - used by author, has steep learning curve. You can look, but it may be better to use either one of the above ones at first time.

As Lever is indented language (and please don't change the grammar to make it otherwise), you want to expand tabs with spaces to avoid syntax errors due to mixed tabs&spaces. Preferable amount of spaces to insert instead of a tab is 4 spaces.

Most text editors meant for programming have a command to change indentation level of multiple lines at once. Relevant Vim commands to do this are 'Vjk<' and 'Vjk>'. On Visual Studio Code you can select the text and then press tab key to indent, or shift+tab to dedent. It's good idea to learn how to trigger this command in your editor.

### Visual Studio Code adjustments

You should get yourself the [https://github.com/cheery/vscode-lever](vscode-lever) extension if you are going to use visual studio code. There are few guides on the [lever's website](http://leverlanguage.com/) to get started with it.

You can install this extension in VSCode by pressing CTRL+P paste the following command and press 'enter':

    ext install vscode-lever

### GEdit adjustments

In `Edit > Preferences` you should find a GUI that holds several options.

In the `View` -tab I propose you will set "Display line numbers" and "Display right margin at column 80" on. Those settings help you find the lines with errors on them, and help you measure when you should break a line into many.

In the `Editor` -tab you should set "Tab width 4" and "Insert spaces instead of tabs"

### Vim adjustments

You may like correct syntax colors on Vim. To do that, retrieve them from http://github.com/cheery/vim-lever

There's nice package manager for vim that lets you keep your plugins and syntax files updated called [vim-pathogen](https://github.com/tpope/vim-pathogen)

These files were earlier in this repository. If you had installed these files
with symbolic links, you may want to clear those away from
`.vim/ftdetect/lever.vim` and `.vim/syntax/lever.vim`.

To configure vim to expand tabs:

    set expandtab
    set tabstop=4
    set shiftwidth=4

You may set them to your `.vimrc` -file, or type them when you start:

### On Windows

TODO: setup a system that builds win32 runtime binaries on weekly basis after new commitsand uploads them.

The latest win32 release is ancient, so you have to compile yourself new one from the master -branch. To do that you need Visual Studio 2008 C++ compiler.

Once you have successfully compiled, you can run win32_dist.py to get yourself a fresh binary distribution. Start writing your code into app/ -directory.

TODO: provide some way to update win32 binaries.

### On Linux

TODO: Deployment help to deploying on Steam could be nice.

Most Linux package managers cannot keep up in pace with something that updates on weekly basis. Fortunately setting up yourself Lever development environment on Linux isn't difficult.

You may resolve it many ways, but the easiest is probably writing this kind of a script, call it 'lever':

    #!/bin/bash
    export LEVER_PATH=/home/cheery/.local/lever
    exec $LEVER_PATH/lever $*

Rewrite the /home/cheery/.local/lever to point on wherever your lever repository is. Then put the script into some directory that is in your $PATH, eg. into ~/.local/bin that is an user script directory on many linux distributions.

When you git-clone the repository properly, you can do this to update your lever:

    git pull origin master && ./setup.py compile

Once you have done this, you can create a new directory and write the script 'main.lc' there. Then you can test your app by running this inside your directory:

    lever main.lc

## Contribution or Use

Because it is so fast to come up with new features, much of Lever development is demand driven. You may discover features that should be implemented by the runtime, or by a lever library.

When that happens, you have two options:

 * Implement the feature yourself. Make a pull request to not having to maintain your own version.
 * Write an user story, article or feature proposal. Send it to my email or file an issue in github.

Lever IRC channel: irc.freenode.net#lever [webchat link](http://webchat.freenode.net/?randomnick=1&channels=%23lever&prompt=1)

### Project coordination

I have clear vision on Lever and I'd like to have some coordination over lever development. To coordinate I will use STRATEGY and TACTIC -tags in the source code. Finding them you can discover long term goals of the lever and the worksites, as well as the current activity taking place. Here's an example of what you might face:

    STRATEGY: Provide installation & upgrade methods in "flip-a-switch" -style.
        restricts release of 1.0.0
    TACTIC: Provide downloadable win32 binary.
    TACTIC: Plow the way out for SteamOS distributions.
    STRATEGY: Implement documentation system
        restricts release of 0.10.0
    TACTIC: Form something like a text processor. Bit like TeX
        Reuse the TeX syntax that has proven to be work?
        Support conditional inclusion of notes into docs.
        Put todo! messages dump into the console during docs compiling.
        Provide support to inject details from reference manual into the
        runtime.
    STRATEGY: Make the MVP documentation for Lever.
    TACTIC: Provide a detailed plan for lever learners.
        restricts release of 0.9.0

Long term mission of Lever is to prove the large scale viability of dynamic languages, and to evolve to remain as an always fresh programming environment.

I review all the code that is supposed to get into the mainline repository of lever, this is currently: http://github.com/cheery/lever

## License

Lever comes with MIT license.

License was chosen in appreciation to PyPy -project.
