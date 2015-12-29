.. Lever documentation master file, created by
   sphinx-quickstart on Mon Nov 16 12:51:43 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Lever's documentation
================================

0.5.0 is a draft of the Lever programming language. The documentation is incomplete.

Stable releases will come with complete documentation. For most things not described here, I advice you to `join the irc channel set up for the community`_.

.. _join the irc channel set up for the community: http://webchat.freenode.net/?randomnick=1&channels=%23lever&prompt=1

Contents:

.. toctree::
   :maxdepth: 2

   stdlib

Compiling Instructions
======================

There are some things that may need explicit platform support and I'll be busy coding
the first programs in the language. Therefore I only promise that Linux version runs.

At maximum there will be a release for the SteamOS, so you have to compile this
yourself. If you happen to be a person doing packaging for a distribution, please
provide your contact info so that I can assist you out and help keep the packaging
updated effortlessly.

Fortunately the compiling will only take few minutes and it's easy. I have set up a
script to compile lever. Here's how to invoke it from a terminal::

    cd path/to/lever
    python setup.py compile

If you're on debian based system, it prompts to install what you need to compile it.
Otherwise you are adviced to provide the missing dependencies yourself. The script
won't attempt to proceed if it cannot find the needed libraries.

The compiling results with the executable. For now the run.py -script can be
used to run any of the examples. Here's how to run one of the samples::

    python run.py samples/ticktock.lc



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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

