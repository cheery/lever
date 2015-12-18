.. Lever documentation master file, created by
   sphinx-quickstart on Mon Nov 16 12:51:43 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Lever's documentation
================================

0.5.0 is a draft of the Lever programming language. The documentation is incomplete.

Stable releases will come with complete documentation.

Contents:

.. toctree::
   :maxdepth: 2

   stdlib

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

