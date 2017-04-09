# VK_KHX_external_memory sample program

Some cornels have been cut here, but despite that this
program can provide some approximate idea on how to use
these new extensions. 

It does not provide semaphore/fence syncronization that
would be required in the between, and it probably
excessively uses an image pipeline barrier, but it can be
seen to work.

You could write a desktop on top of Lever, we can thank
Vulkan for it.

This sample only works on Linux, but only because it has not
been ported for Windows.

The program has been divided to the client.lc and server.lc.
The server.lc is started first, it starts the client.lc as a
subprocess, giving it a pipe as fourth stream above the
standard stdin/stdout/stderr streams. The client initiates
and sends an image to draw for the server.
