====================
 Language Reference
====================

Function Calls
==============

Function calls are notated as follows::

    callee(arg0, arg1, ...)

Variadic arguments
------------------

Function calls may obtain an iterable that fills the remaining argument slots.
This kind of variadic function call is notated with three dots::

    remaining_args = [arg2, arg3, arg4]
    callee(arg0, arg1, remainin_args...)

The same three dot notation is used to denote a definition of variadic
function, and you get the excess arguments in a list::

    (arg0, arg1, remaining_args...):
        print(arg0)
        print(arg1)
        for arg in remaining_args
            print(arg)

Optional arguments
------------------

Both builtin and ordinary functions can be called with one or more optional
arguments. The optional arguments are denoted with an assign sign::

    (arg0, opt1=20, opt2=30):

Both optional arguments and variadic arguments can appear in same definition::

    (arg0, opt1=20, args...):

Not passing an optional argument is equivalent to passing a null::

    callee(arg0)
    callee(arg0, null)

The optional expressions are run whenever an optional argument is null. The
optionals are called one after another and they may reference each other.

Too many arguments
------------------

If you call a builtin or FFI function with too many arguments, that will be
intercepted and an exception is raised.

If you call a function written in lever, too many arguments aren't producing an
error. The intent here is that you could pass extra values that every callee may
not need.

Behavior on too many arguments may change in subsequent implementations.

Undefined behavior
------------------

If you define two arguments with same name, it may differ among implementations
what happens. The following function may reference either argument::

    (name, name):
        print(name)

