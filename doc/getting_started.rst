Getting started
===============

This guide assumes you're using Windows. It loosely applies to other
systems too, though.

The best way to get started with Lever is to download an archive and
extract it. [coming] Extract the archive to location that is easy to
access, for example C:\lever\ 

You need to know how to use command line on windows. Enough to change
into a directory and execute a command::

    cd C:\lever\
    lever.exe samples\sdl2_hello.lc

If the command runs, you have a working lever install. Next you need a
text editor to edit the files and bit of time to learn lever.

Significant Whitespace
======================

When writing lever with a text editor of your choice, you may end up
with a problem that the code looks correct but it doesn't compile. The
most likely problem is that you've mixed up tabs and spaces.

In the text file tab [key 9] and space [key 32] are exactly of same
width, so when lever parses the file, it sees that every character
is of same width.

There's no convention in how wide a tab character is. Some editors treat
it as 4 characters, other treat as 8 characters. There's no generic good
rule to interpret it. Therefore the lever compiler gets confused when
you pass it lines that mix these different kind of spaces.

This is the most common counterargument to avoid layout sensitive
syntax and discard an otherwise comprehension improving feature.

Fortunately there several are ways to avoid the problem entirely:

 I. Most text editors can show visible symbol on tab character,
    so you recognize when you've insterted a tab character.

 I. Some text editors can be set up to replace tab character with
    spaces, while you type them, so the text file always contains
    only one kind of spaces.

 I. Use a text editor that has mode for writing lever. So far there
    are none of those.

Although lever can handle tab characters, I would approve if everyone
kept their lever source files free of tab characters.

A tip for working with indentation
----------------------------------

Later working with indented languages, you may find it frustrating
that you have to add or remove spaces in front of every line.

Most text editors that have been meant for programming have a tool to
change indentation level. It's good idea to learn how to trigger this
command in your editor.
