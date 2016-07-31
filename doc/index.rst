.. Lever documentation master file, created by
   sphinx-quickstart on Mon Nov 16 12:51:43 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Lever's documentation
================================

The sphinx documentation is no longer updated, and it will be removed soon.

IRC community channel
=====================

Lever has a `IRC channel set up for community discussion`_.

.. _IRC channel set up for community discussion: http://webchat.freenode.net/?randomnick=1&channels=%23lever&prompt=1

Contents:

.. toctree::
   :maxdepth: 2

   stdlib

Installing Lever
================

With a small maintainer-base, Lever requires some effort to install&use. It is
easiest to install on debian-based systems such as Ubuntu. 

One time I actually wanted users for Lever. Then I realised I wouldn't do
anything with them. I'm happy as long as I got a good language. If you really
want to use Lever, you got to see some shit first.

If you happen to be a person doing packaging for a distribution, please provide
your contact so that author can assist you out and help keep the packaging
updated and recent.

For nonexpert Windows users there is no support path here. You guys can stop
reading.

Obtain the source code
----------------------

First you have to obtain Lever source code.

Git should be used because it enables quick transmission contributions and
patches. This git command lets you obtain the source::

    git clone https://github.com/cheery/lever

Compiling instructions
----------------------

Compiling takes some time. I have set up some scripts to compile lever. Here's
how to invoke them when you're in the root directory of the project::

    python setup.py compile

On Linux it's easy to check dependencies, so this script won't attempt to proceed
if it cannot find the needed libraries. It won't check for versions though.

Compiling gives you an executable "lever". You can use it to run any of the
examples. Here's how you can run one of the samples::

    ./lever samples/ticktock.lc

Lever attempts to resolve library path to where it is located. This behavior can
be changed by patching Lever.

Languages present in Lever runtime
==================================

Lever uses python for short development scripts and as a bootstrap language for
compiling the bytecode compiler to bytecode.

The runtime is in RPython. It is translated into native machine code and
a JIT compiler.

Lever syntax & grammar
======================

Before lever runs a source listing, it compiles that into instructions so that
virtual machine can load in the program. Instead of having a grammar in itself,
the compiler loads it as an input from the lever.grammar -file.

The lever.grammar is a listing of context-free rules the compiler recognizes.
If you happen to prefer different syntax for some reason, all you need to do is
change the lever.grammar and provide it along your project.

There is a thin layer of tokenizing before the grammar is applied to the input
source listing.

If you have used dynamically typed languages before, and you know what a
context free grammar is, most of this grammar should make sense.

The functions processing each of these rules are in compile.py, and they are
prefixed with post\_.

Blocks
------

Lever files are sequences of statements separated by newline. Each statement
can be evaluated and when done so return a value, these statements are called
blocks, whenever appropriate, increased indentation level can form a block
inside expressions::

    file =>
        empty_list:
        statements

    block => pass(statements): indent statements dedent

    statements =>
        first:           block_statement
        append(lhs rhs): lhs=statements newline rhs=block_statement

Different statements
--------------------

The statement is divided into block-level and ordinary statements. Right now,
expressions are the only ordinary statements::

    block_statement =>
        pass: statement
        return(statement):
            kw_return:"return" statement
        if(statement block otherwise):
            kw_if:"if" statement block otherwise
        while(statement block):
            kw_while:"while" statement block
        local_assign(symbol block_statement):
            symbol assign_op:"=" block_statement
        upvalue_assign(symbol block_statement):
            symbol upvalue_assign_op:":=" block_statement
        setitem(expr idx block_statement):
            expr lb:"[" idx=expr rb:"]" assign_op:"=" block_statement
        setattr(expr symbol block_statement):
            expr dot:"." symbol assign_op:"=" block_statement
        for(symbol statement block):
            kw_for:"for" symbol kw_in:"in" statement block
        import(symbols_list):
            kw_import:"import" symbols_list

    otherwise =>
        done:
        elif(statement block otherwise):
            newline kw_elif:"elif" statement block otherwise
        else(block):
            newline kw_else:"else" block

    statement =>
        pass: expr

Note that on topmost level function, the local_assign assigns a value into
module namespace rather than the local scope.

The upvalue assign -rule can be used to store values into already bound variables.

I have also not entirely decided how variable lookup should happen. Right now,
lookup happens from local scope, if there is a preceding dominating control
flow block that does local_assign into that variable. This is a cornel case and
the behavior may change, though.

Expressions
-----------

Expressions are some of the few things that might be easier to describe with
precedence table. For now, you can take a thumb of rule that the rule appearing
lower in this subsequent listing will take higher precedence:: 

    expr =>
        expr3
        or(expr3 expr): expr3 kw_or:"or" expr

    expr3 =>
        expr5
        and(expr5 expr3): expr5 kw_and:"and" expr3

    expr5 =>
        expr8
        not(expr8): kw_not:"not" expr8

    expr8 =>
        expr10
        in(l r): l=expr10 kw_in:"in" r=expr10
        not_in(l r): l=expr10 kw_not:"not" kw_in:"in" r=expr10
        binary: expr10 lt:"<" expr10
        binary: expr10 gt:">" expr10
        binary: expr10 eq:"==" expr10
        binary: expr10 ne:"!=" expr10
        binary: expr10 le:"<=" expr10
        binary: expr10 ge:">=" expr10

    expr10 =>
        expr20
        binary: expr10 bitwise_or:"|" expr20

    expr20 =>
        expr30
        binary: expr20 bitwise_xor:"^" expr30

    expr30 =>
        expr50
        binary: expr30 bitwise_and:"&" expr50

    expr50 =>
        expr100
        binary: expr50 bitwise_shl:"<<" expr100
        binary: expr50 bitwise_shr:">>" expr100

    expr100 =>
        expr200
        binary: expr100 concat:"++" expr200
        binary: expr100 plus:"+" expr200
        binary: expr100 minus:"-" expr200

    expr200 =>
        prefix
        binary: expr200 star:"*" prefix
        binary: expr200 slash:"/" prefix
        binary: expr200 percent:"%" prefix

    prefix =>
        postfix
        prefix: plus:"+" postfix
        prefix: minus:"-" postfix

    postfix =>
        term
        call(postfix arguments):
            postfix lp:"(" arguments rp:")"
        getitem(postfix expr):
            postfix lb:"[" expr rb:"]"
        getattr(postfix symbol):
            postfix dot:"." symbol

    arguments =>
        empty_list:
        arguments1
        pass(arguments1): arguments1 comma:","

    arguments1 =>
        first: expr
        append(lst expr): lst=arguments1 comma:"," expr

Terms
-----

These are the current terms understood by the language::

    term =>
        lookup:          symbol
        int:             int
        hex:             hex
        float:           float
        string:          string
        pass(expr):      lp:"(" expr rp:")"
        list(arguments): lb:"[" arguments rb:"]"
        function(bindings block):
            lp:"(" bindings rp:")" colon:":" block
        dict(pairs): lc:"{" pairs rc:"}"
        lookup(escaped_keyword): lc:"{" escaped_keyword rc:"}"
        lookup(string): percent:"%" string

    bindings =>
        empty_list:
        bindings1
        pass(bindings1): bindings1 comma:","

    bindings1 =>
        first: symbol
        append(lst symbol): lst=bindings1 comma:"," symbol

    pairs =>
        empty_list:
        pairs1
        pass(pairs1): pairs1 comma:","

    pairs1 =>
        first: pair
        append(lst pair): lst=pairs1 comma:"," pair

    pair => tuple(k v): k=expr colon:":" v=expr

    escaped_keyword =>
        pass: kw_import:"import"
        pass: kw_and:"and"
        pass: kw_or:"or"
        pass: kw_not:"not"

    symbols_list =>
        first: symbol
        append(lst symbol): lst=symbols_list comma:"," symbol

Lever base module
=================

.. class:: dict([iterable])

   Dictionary is a hash table that maps keys to values.

.. class:: module()

   Modules are hierarchical name->value -tables. They can be reset and reloaded.

.. class:: exnihilo()

   Produces 'from scratch' -objects that can be filled with anything you wish.

.. class:: object()

   Base interface for all interfaces.

.. class:: list()

   Lists represent sequences of values.

.. class:: multimethod(arity)

   Multimethods represent bundles of functions of fixed arity. Programmer can insert
   more of functions into a multimethod at any time.

   During invocation multimethods calls interface() for every argument they get. The
   result is used to determine the function to call. If the value is missing in the
   table, the default -method is called. If there's no default method, then an error
   is raised.

.. class:: greenlet(arguments...)

   Conceptually greenlets represent a body of work you can stop for a moment while
   you do a different task. Note that you are always in a greenlet. You can always
   put the current task to sleep, or switch to the eventloop to run a different task.

   Greenlet represents a call frame that can be suspended. The arguments describe a
   function to call and it can be left blank. In that case the switching has to pass
   a function that is called inside the greenlet.

   The greenlet.parent describes where the call returns once it finishes.

   greenlet.switch(arguments...) suspends the current greenlet and switches to the
   targeted greenlet. If the greenlet hasn't started yet, the given arguments are
   concatenated to the initial arguments. If the greenlet is suspended, the arguments
   are compacted into a value and returned in the target greenlet.

.. function:: getcurrent()

   Returns the currently running greenlet.

.. function:: schedule(arguments...)

   Schedule is similar to the greenlet -command, except that it queues the greenlet
   and sets it to return into the eventloop when it finishes. It returns the
   newly created greenlet.

.. function:: sleep(duration, [function])

   The sleep performs two functions. It can be used to suspend the current greenlet,
   queue it after duration of seconds pass.

   If you pass it a function or greenlet, it will convert it into a greenlet and
   adds it to the event queue after the duration passes.

.. class:: int()

   An integer. Merely used to identify integers. No other interests.

.. class:: bool()

   Boolean. Merely used to identify booleans and to convert values into booleans.

.. class:: str()

   Represents strings. Strings are immutable.

.. class:: path(posixpath)

   Represents file paths. Note that irrespective of the OS, lever expects you
   to provide POSIX compatible paths.

   Paths have mutable attributes "is_absolute", "basename", "label". There is also
   .push(path) -method to help in-place modify the path.

   To pass path to FFI, the path object has "get_os_path" -method to convert
   the path into system path.

.. data:: null

   Represents nonexistence of value.

.. data:: true

   Represents a true value.

.. data:: false

   Represents a false value.

.. function:: {import}(name)

   Imports a function.

.. function:: interface(object)

   Retrieve the interface of an object.

.. function:: iter(object)

   Retrieve an iterator. Invokes the +iter from the interface table.

.. function:: getitem(object, index)

   Equivalent to object[index]. Presented as a convenience. Invokes the +getitem from
   the interface table.

.. function:: setitem(object, index, value)

   Equivalent to object[index] = value. Presented as a convenience. Invokes the +setitem
   from the interface table.

.. function:: getattr(object, name)

   Retrieves attribute from an object.

.. function:: setattr(object, name, value)

   Sets an attribute from an object.

.. function:: ord(character)

   Returns integer representing the unicode point of the character.

.. function:: chr(integer)

   Returns a character that corresponds to the integer.

.. function:: print(values...)

   Prints the given values, with space between them.

.. function:: {and}(a, b)
   
   A convenience function that does a and b without conditional chaining rules.

.. function:: {or}(a, b)

   A convenience function that does a or b without conditional chaining rules.

.. function:: {not}(a)

   A convenience function that inverses a truth value.

.. method:: coerce(a, b)

   A Base multimethod for converting two value into values that pair arithmetically.
   Coercion is used when the values cannot be found from the usual multimethod table
   and when the exact pairing cannot be found. 

.. method:: {+}, {-}, {*}, {/}, {|}, {%}, {&}, {^}, {<<}, {>>}, min, max

   Standard arithmetic methods.

.. method:: {<}, {>}, {<=}, {>=}, {!=}, {==}

   Stardard comparative methods.

.. method:: {-expr}, {+expr}

   Multimethods for negative and positive prefix.

.. method:: {++}

   Concatenation multimethod. Implemented on lists and strings.

.. function:: getcwd()

   Returns a path object denoting the current path. Note that this object is
   converted once, so if you have unusual path that doesn't follow posix
   conventions, the lever getcwd may give a incorrect path.

   Note that both getcwd() and chdir(path) may eventually move into fs -module.

.. function:: chdir(path)

   Changes the current directory.

   Note that both getcwd() and chdir(path) may eventually move into fs -module.

Contributing to Lever
=====================

Contributing to Documentation
-----------------------------

The Lever documentation sits in doc/ subdirectory. The following commands will
update the documentation so you can preview your changes::

    cd doc/
    make publish

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

