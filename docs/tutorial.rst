Tutorial
========

Imagine: A fictional company has a standard way to do greetings. For this, it
created a tag function to properly format greetings  according to its standards.

Simple Tag Function
===================

We start with a tag function ``greet`` that's used as a prefix:

.. literalinclude:: ../src/tagstr/greeting.py
    :start-at: def greet
    :end-at: return f

If it looks like the ``f-`` in f-strings -- correct! You can then use this tag
function as a "tag" on a string:

.. testsetup::

    from tagstr.greeting import greet

.. doctest::

    >>> print(greet"Hello")
    HELLO!

In the ``greet`` function -- a *tag* function -- we see the first step into
tag strings. You're given an ``*args`` sequence for all the parts in the
string being tagged. We see how this PEP tokenizes/processes the string
being tagged, into datastructures to be easily handled.

We then see a usage -- a tagged string in ``main`` with ``greet"Hello"``. This
"tags" the ``Hello`` string with the function ``greet``.

Interpolation
=============

That example showed the basics but had no dynamicism in it. f-strings make
it easy to insert variables and expressions with extra instructions. We
call these *interpolations*. Let's see a super-simple example:

.. literalinclude:: ../src/tagstr/greeting.py
    :start-at: def greet2
    :end-at: return f

The second argument is the ``{name}`` part, represented as a tuple. The
tuple's first argument is a callable that evaluates *in the scope* where the
tag string happened. Calling it yields the value, thus by convention we call
this ``getvalue``.

.. testsetup::

    from tagstr.greeting import greet2

This time, we'll tag a string that inserts a variable:

.. doctest::

    >>> name = "World"
    >>> print(greet2"Hello {name}")
    Hello WORLD!

Flexible Args
=============

Our greeting now expects a string followed by a single interpolation. But
f-strings can have all kinds of things mixed in, even nested f-strings.
Let's teach our greeting to handle an arbitrary list of strings and
interpolations.

In fact, let's start adopting the jargon used in this proposal:

- *Chunks* are segments that are static strings
- *Thunks* are the structure representing an interpolation
- The *args* are thus an arbitrary sequence of chunks and thunks, intermixed

Here's the code to generalize args:

.. literalinclude:: ../src/tagstr/greeting.py
    :start-at: def greet3
    :end-at: return f

It uses Python 3.10 structural pattern matching to analyze each segment and
determine "chunks" and "thunks".

.. testsetup::

    from tagstr.greeting import greet3

.. doctest::

    >>> print(greet3"Hello {name} nice to meet you")  # name is still World
    Hello WORLD nice to meet you!

Thunks
======

We just said interpolations were represented by "thunks". Let's look at them
more carefully and see what they have to offer, while adding some typing.

A thunk is a tuple with this shape:

.. literalinclude:: ../src/tagstr/__init__.py
    :start-at: class Thunk
    :end-at: format_spec

Let's add some typing information to our greet function.
We'll

More
====

- Deferred
- Non-string