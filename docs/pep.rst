Abstract
========

This PEP introduces tag strings for custom, repeatable string processing.
Tag strings are an extension to f-strings, with a custom function -- the "tag"
-- in place of the `f` prefix. This function can then provide rich features
such as safety checks, lazy evaluation, DSLs such as web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages.

Motivation
==========

Python f-strings became very popular, very fast. The syntax was easy and
convenient while the interpolation name references had access to regular
scoping rules. In short: f-strings feel like Python.

With years of f-string adoption in place, more can be considered.

Eager vs. Lazy
--------------

In Python, fstrings are eagerly evaluated. That is, the interpolations are
evaluated immediately. This prevents f-string re-use: for example, imported
from a common module and when logging. Questions regarding this `come up
frequently <https://stackoverflow.com/questions/71189844/can-i-delay-evaluation-of-the-python-expressions-in-my-f-string>`_.

Unsafe Interpolations
---------------------

Because interpolations are eagerly evaluated, developers can't conveniently
intercept values to check for unsafe practices.

For example: running a string that executes a line in the shell. Those
interpolation values should be run through ``shlex.quote``. As a related
example: SQL injection attacks, also known as the
`Bobby Tables problem <https://xkcd.com/327/>`_.

Interception unsafe interpolations, in fact, was the primary motivation for :pep:501.

Web Templating and DSLs
-----------------------

Python has a long history with web templating, with many popular packages,
most prominently `Jinja2 <https://pypi.org/project/Jinja2/>`_. Some might
prefer a more Pythonic approach, such as f-strings, but these are missing
many features common for HTML templating:

- Sanitized strings
- Rich support for HTML attributes
- Sub-templates such as macros, components, and layouts
- Helpers such as piping into filters
- Innovate new ideas such as virtual DOMs

Returning to the current templating approach has some downsides:

- Non-Pythonic syntax
- Alternative scoping rules and syntax for sharing/importing
- Unable to use common Python tooling (linting, formatting, typing)

Templating is a subset of general support for building domain-specific
languages (DSL). With this, regular Python f-string semantics can be
passed to another function for postprocessing into new, specific semantics.

As DSLs become an alternative to templating, the combination can be powerful.
For example, Markdown and reStructured Text "files" can be a combination of
text, processing, and interpolation logic. This idea is popularized in the
`MDX project <https://mdxjs.com>`_.

Extra Processing
----------------

When functions can be combined with strings and interpolation, the door opens
for custom and innovative extra processing. As an example, memoization and
transparent caching.

Proposal
========

This PEP proposes customizable prefixes for f-strings. These f-strings then
become a "tag string": an f-string with a "tag function." The tag function is
a callable which is given a sequence of arguments for the parsed tokens in
the string.

Here's a very simple example. Imagine we want a certain kind of string with
some custom business policies. For example, uppercase the value and add an
exclamation point::

    def greet(*args):
        """Uppercase and add exclamation"""
        salutation = args[0].upper()
        return f"{salutation}!"

    greeting = greet"Hello"  # Use the custom "tag" on the string
    assert greeting == "HELLO!"

The beginnings of tag strings appear:

- ``greet"Hello"`` is an f-string, but with a ``greet`` prefix instead of ``f``
- This ``greet`` prefix is a callable, in this case, the ``greet`` function
- The function is passed a sequence of values
- The first value is just a string
- ``greet`` performs a simple operation and returns a string

With this in place, let's introduce an interpolation. That is, a place where
a value should be inserted::

    def greet(*args):
        salutation = args[0].strip()
        # Second arg is a "thunk" named tuple for the interpolation.
        getvalue = args[1][0]
        recipient = getvalue().upper()
        return f"{salutation} {recipient}!"

    name = "World"
    greeting = greet"Hello {name}"
    assert greeting == "Hello WORLD!"

The f-string interpolation of ``{name}`` leads to the new machinery in tag
strings:

- `args[0]` is still the string, this time with a trailing space
- `args[1]` is an interpolation expression -- the ``{name}`` part
- Tag strings represent this interpolation part as a *thunk* (detailed below)
- A thunk is a tuple whose first item is a lambda
- Calling this lambda evaluates the expression using the usual lexical scoping

The ``*args`` list is a sequence of "chunks" and "thunks". A chunk is just a
string. But what is a "thunk"? It's a tuple representing how tag strings
processed the interpolation into a form useful for your tag function. Thunks
are fully described below in ``Specification``. TODO proper rst link

Here is a more generalized version using structural pattern matching and
type hints::

    from taglib import Thunk  # Should be in typing
    def greet(*args: str | Thunk) -> str:
        result = []
        for arg in args:
            match arg:
                case str():  # This is a chunk...just a string
                    result.append(arg)
                case getvalue, _, _, _: # This is a thunk...an interpolation
                    result.append(getvalue().upper())

        return f"{''.join(result)}!"

    name = "World"
    greeting = greet"Hello {name} nice to meet you"
    assert greeting == "Hello WORLD nice to meet you!"

- An example that shows conversion and format information
- Show a lazy implementation
- Follow ideas in other languages, especially JS

Specification
=============

In the rest of this specification, ``mytag`` will be used for an arbitrary tag.

Grammar
-------

The tag name can be any **undotted** name that isn't already an existing valid
string or bytes prefix, as seen in the `lexical analysis specification
<https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals>`_:

.. code-block:: text

    stringprefix: "r" | "u" | "R" | "U" | "f" | "F"
                : | "fr" | "Fr" | "fR" | "FR" | "rf" | "rF" | "Rf" | "RF"

    bytesprefix: "b" | "B" | "br" | "Br" | "bR" | "BR" | "rb" | "rB" | "Rb" | "RB"

As with other string literals, no whitespace can be between the tag and the
quote mark.

.. note::

    The restriction to use undotted names can be relaxed to dotted names in the
    future, if there is a compelling usage.

No string concatenation
-----------------------

Tag string concatenation isn't supported, which is `unlike other string literals
<https://docs.python.org/3/reference/lexical_analysis.html#string-literal-concatenation>`_.

.. note::

    The expectation is that triple quoting is sufficient. If string
    concatenation is supported, results from tag evaluations would need to
    support the ``+`` operator with ``__add__`` and ``__radd__``.

Example
-------

.. code-block:: python

    name = 'Knights Who Say "Ni!"'
    obj = mytag'Hi, {name}!'


String fragments
----------------

Raw strings

Thunk
-----

A thunk is the data structure representing the interpolation information from
the template. In the example above, the thunk is equivalent to the following
named tuple::

    lambda: name, 'name', None, None

The lambda wrapping here, ``lambda: name``, uses the usual lexical scoping. As
with f-strings, there's no need to use ``locals()``, ``globals()``, or frame
introspection with ``sys._getframe`` to evaluate the interpolation.

The code of the expression source is , ``'name'`` is available, which means there is no need to
use ``inspect.getsource``, or otherwise parse the source code to get this expression source.

The conversion and format spec are both ``None``.

In this example, ``mytag`` is evaluated as follows::

    mytag(r'Hi, ', (lambda: name, 'name', None, None), r', welcome back!')

.. note::

    In the CPython reference implementation, this would presumably use the equivalent
    `Struct Sequence Objects <https://docs.python.org/3/c-api/tuple.html#struct-sequence-objects>`_
    (as done with for example `os.stat_result <https://docs.python.org/3/library/os.html#os.stat_result)>`_.
    A suitable importable type will be made available from ``typing``.

Expression evaluation
---------------------

Expression evaluation is the same as in :pep:`498`, except that all expressions
are always implicitly wrapped with a ``lambda``::

    The expressions that are extracted from the string are evaluated in the context
    where the tag string appeared. This means the expression has full access to its
    lexical scope, including local and global variables. Any valid Python expression
    can be used, including function and method calls.

Function application
--------------------

These are equivalent ways of applying the tag function:

.. code-block:: python

    mytag'Hi, {name}!'

and:

.. code-block:: python

    mytag('Hi, ', (lambda: name, 'name', None, None), '!')

.. note::

    Because tag functions are simply callables on a sequence of strings and thunks,
    it is possible to write code like the following:

    .. code-block:: python

        length = len'foo'

    In practice, this seems to be a remote corner case. We can readily define
    functions that are named ``f``, but in actual usage they are rarely, if
    ever, mixed up with a f-string. Similar observations can apply to the use of
    soft keywords. The same should be true for tag strings.

The evaluation of the tag string looks up the callable that is bound to the tag
name. This is called the tag function, and it supports this signature:

.. code-block:: python

    mytag(*args: str | Thunk):
        ...

The type of tag functions in general is:

.. code-block:: python

    class Tag(Protocol):
        def __call__(self, *args: str | Thunk) -> Any:
            ...

Interpolations and thunks
-------------------------

TODO: this needs to be changed in the reference implementation/discussed in
issues, specifically bikeshedding.

A **thunk** encodes the interpolation. Its type is the equivalent of the
following:

.. code-block:: python

    from typing import NamedTuple

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None
        formatspec: str | None

Let's assume we are working with the following tag string:

.. code-block:: python

    name = "First O'Last"
    title = 'President & CEO'

    dom = html"""
    <div>Hi, {name}, you have {amount:formatspec}
    """

Then the following holds for the two thunks TODO complete this example:

* ``getvalue`` is the lambda-wrapped expression of the interpolation, ``lambda: name``.
* ``raw`` is the **expression text** of the interpolation, ``'name'``
* ``conv`` is the optional conversion used, one of ``r``, ``s``, and ``a``,
   corresponding to repr, str, and ascii conversions.
* ``formatspec`` is the optional formatspec. A formatspec is eagerly evaluated
   if it contains any expressions before passing to the tag function.


Tag functions
-------------

Type signature for tag functions:

.. code-block:: python

    def tag(*args: str | Thunk) -> Any:
        ...

This has the equivalent type of:

.. code-block:: python

    Callable[[str | Thunk, ...], Any]

Roundtripping limitations
-------------------------

There are two limitations with respect to roundtripping to the exact original
raw text.

First, the ``formatspec`` can be arbitrarily nested:

.. code-block:: python

    mytag'{x:{a{b{c}}}}'

However, in this PEP and corresponding reference implementation, the formatspec
is eagerly evaluated to get the ``formatspec`` in the thunk.

Secondly, ``mytag'{expr=}'`` is parsed to being the same as
``mytag'expr={expr}``', as implemented in the issue `Add = to f-strings for
easier debugging <https://github.com/python/cpython/issues/80998>`_.

While it would be feasible to preserve roundtripping in every usage, this would
require an extra flag ``equals`` to support, for example, ``{x=}``, and a
recursive ``Thunk`` definition for ``formatspec``. The following is roughly the
pure Python equivalent of this type, including preserving the sequence
unpacking:

.. code-block:: python

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None
        formatspec: str | None | tuple[str | Thunk, ...]
        equals: bool = False

        def __len__(self):
            return 4

        def __iter__(self):
            return iter((self.getvalue, self.raw, self.conv, self.formatspec))

However, this additional complexity seems unnecessary and is thus rejected.



Tool Support
============

Backwards Compatibility
=======================

Security Implications
=====================

Performance Impact
==================

- Faster than getting frames
- Opportunities for speedups

How To Teach This
=================

Common patterns seen in writing tag functions
=============================================

Recursive construction
----------------------

Some type of marker class

Structural pattern matching
---------------------------

Iterating over the arguments with structural pattern matching is the expected
best practice for many tag function implementations::

    def tag(*args: str | Thunk) -> Any:
        for arg in args:
            match arg:
                case str():
                    ... # handle each string fragment
                case getvalue, raw, conv, format:
                    ... # handle each interpolation

This can then be nested, to support recursive construction::

    TODO

Decoding raw strings
--------------------

One possible implementation::

    def decode_raw(*args: str | Thunk) -> Iterator[str | Thunk]:
        for arg in args:
            match arg:
                case str():
                    yield arg.encode('utf-8').decode('unicode-escape')
                case _:
                    yield arg

In a nutshell: for each string, encode as bytes in UTF-8 format, then decoded
back as a string, applying any escapes, while maintaining the underlying Unicode
codepoints. There may be a better way, but this conversion uses the same
internal code path as Python's parser.

Memoizing parses
-----------------

Consider this tag string::

    html"<li {attrs}>Some todo: {todo}</li>"

Regardless of the expressions ``attrs`` and ``todo``, we would expect that the
static part of the tag string should be parsed the same. So it is possible to
memoize the parse only on the strings ``'<li> ''``, ``''>Some todo: ''``,
``'</li>''``::

    def memoization_key(*args: str | Thunk) -> tuple[str...]:
        return tuple(arg for arg in args if isinstance(arg, str))

Such tag functions can memoize as follows:

1. Compute the memoization key.
2. Check in the cache if there's an existing parsed templated for that
   memoization key.
3. If not, parse, keeping tracking of interpolation points.
4. Apply interpolations to parsed template.

TODO need to actually write this - there's an example of how to do this for
writing an ``html`` tag in the companion tutorial PEP.

Examples
========

- Link to longer examples in the repo

Relationship with Other PEPs
============================

Python introduced f-strings in Python 3.6 with :pep:`498`. The grammar was
then formalized in :pep:`701` which also lifted some restrictions. This PEP
is based off of PEP 701.

At nearly the same time PEP 498 arrived, :pep:`501` was written to provide
"i-strings" -- that is, "interpolation template strings". The PEP was
deferred pending further experience with f-strings. Work on this PEP was
resumed by a different author in Mar 2023, introducing "t-strings" as template
literal strings, and built atop PEP 701.

The authors of this PEP consider tag strings as a generalization of the
updated work in PEP 501.

Reference Implementation
========================

Rejected Ideas
==============

Acknowledgements
================

Copyright
=========


