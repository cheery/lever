Standard library
================


api
---

.. function:: open(name, [get_proc_address])

   Searches for .json -notated C headers at 
   $(LEVER_PATH)/headers/{name}

   If those are found, it invokes FFI to open a shared
   library that corresponds to the headers. Or uses the
   function you supplied to it to retrieve C-FFI handles
   to annotate.

   The resulting object overloads +getattr, so you can
   treat your newly instantiated C-bindings as a module.

ffi
---

.. class:: wrap(cname, ctype)

   Associates a c-type with a name. It is used to denote
   whether a differently named symbol should be fetched, in
   the library -interface.

.. class:: library(path, [apispec]) 

   The path must be a string denoting the location of the
   library in the system. The apispec may be a function
   that is called with the name whenever getattr(name) is
   called. It returns a ctype or wrap -object to indicate
   what the library should do.

.. class:: handle

   Cannot be instantiated yourself. Represents a handle
   into a C symbol.

.. function:: cast(obj, ctype)

   Converts the c-type of a c-object.

.. function:: sizeof(ctype, [a])

   Returns the size of the ctype. If the ctype is parametric
   it returns the size of ctype[a], otherwise it returns
   the size of array of ctype of that size.

.. function:: malloc(ctype, [a])

   Where the sizeof returns the size of the type, this thing
   returns a c-object of that size.

   The c-object created with this method must be deallocated.

.. function:: free(cobject)

   Deallocates the memory of mallocated c-object.

.. function:: automem(ctype, [a])
   
   Allocates a chunk of memory that is automatically
   deallocated when the object is being lost. Be aware that
   this method can be used to create flanging pointers.
   
   Please keep the object around as long as the memory is
   used.

Additionally there are some other C ffi objects that are not
described here but should be. I approve contributions and reviews!
