Abstract
========

This PEP introduces tag strings for custom, repeatable string processing.
Tag strings are an extension to f-strings, with a custom function -- the "tag"
-- in place of the `f` prefix. This function can then provide rich features
such as safety checks, lazy evaluation, DSLs such as web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages.

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

Intercepting unsafe interpolations, in fact, was the primary motivation for :pep:`501`.

Transformations
---------------

Interpolations might want some very simple transformations. For example,
`flufl.i18n <https://flufli18n.readthedocs.io/en/stable/using.html#substitutions-and-placeholders>`_
has a simple underscore function which can do static and dynamic substitutions.

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

Templating is a subset of general support for working with domain-specific
languages (DSLs). With this PEP, regular Python f-string semantics can be
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
exclamation point:

.. code-block:: python

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
a value should be inserted:

.. code-block:: python

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
type hints:

.. code-block:: python

    from typing import Chunk, Thunk
    def greet(*args: Chunk | Thunk) -> str:
        result = []
        for arg in args:
            match arg:
                case str():  # A chunk is a string, but can be cooked
                    result.append(arg.cooked)
                case getvalue, _, _, _: # A thunk is an interpolation
                    result.append(getvalue().upper())

        return f"{''.join(result)}!"

    name = "World"
    greeting = greet"Hello {name} nice to meet you"
    assert greeting == "Hello WORLD nice to meet you!"

TODO:
- An example that shows conversion and format information
- Show a lazy implementation
- Follow ideas in other languages, especially JS

Specification
=============

In the rest of this specification, ``mytag`` will be used for an arbitrary tag. Example:

.. code-block:: python

    def mytag(*args):
        return args

    trade = 'shrubberies'
    mytag'Did you say "{trade}"?'

Valid tag names
---------------

The tag name can be any **undotted** name that isn't already an existing valid
string or bytes prefix, as seen in the `lexical analysis specification
<https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals>`_,
Therefore these prefixes can't be used as a tag:

.. code-block:: text

    stringprefix: "r" | "u" | "R" | "U" | "f" | "F"
                : | "fr" | "Fr" | "fR" | "FR" | "rf" | "rF" | "Rf" | "RF"

    bytesprefix: "b" | "B" | "br" | "Br" | "bR" | "BR" | "rb" | "rB" | "Rb" | "RB"


Tags must immediately precede the quote mark
--------------------------------------------

As with other string literal prefixes, no whitespace can be between the tag and the
quote mark.

PEP 701
-------

Tag strings support the full syntax of :pep:`701` in that any string literal,
with any quote mark, can be nested in the interpolation. This nesting includes
of course tag strings.

Evaluating tag strings
----------------------

When the tag string is evaluated, the tag must have a binding, or a `NameError`
is raised; and it must be a callable, or a `TypeError` is raised. This behavior
follows from the translation of

.. code-block:: python

    trade = 'shrubberies'
    mytag'Did you say "{trade}"?'

to

.. code-block:: python

    mytag(Chunk(r'Did you say "'), Thunk(lambda: trade, 'trade'), Chunk(r'"?'))

String chunks
-------------

String chunks are internally stored as the source raw strings. In the earlier
example, there are two chunks, ``r'Did you say "'`` and ``r'"?'``. Raw strings
are used because tag strings are meant to target a variety of DSLs, including
like the shell and regexes. Such DSLs have their own specific treatment of
metacharacters, namely the backslash. (This approach follows the usual
convention of using the r-prefix for regexes in Python itself, given that
regexes are their own DSL.)

However, often the "cooked" string is what is needed, by decoding the string as
if it were a standard Python string. Because such decoding is at least somewhat
non-obvious, the tag function will be be called with ``Chunk`` for any string
chunks. ``Chunk`` *is-a* ``str``, but has an additional property, ``cooked`` that
provides this decoding.  The ``Chunk`` type will be available from ``typing``.
In CPython, ``Chunk`` will be implemented in C, but it has this pure Python
equivalent:

.. code-block:: python

    class Chunk(str):
        def __new__(cls, value: str) -> Self:
            chunk = super().__new__(cls, value)
            chunk._cooked = None
            return chunk

        @property
        def cooked(self) -> str:
            """Convert string to bytes then, applying decoding escapes.

            Maintain underlying Unicode codepoints. Uses the same internal code
            path as Python's parser to do the actual decode.
            """
            if self._cooked is None:
                self._cooked = self.encode('utf-8').decode('unicode-escape')
            return self._cooked

Thunk
-----

A thunk is the data structure representing the interpolation information from
the template. The type ``Thunk`` will be made available from ``typing``, with
the following pure-Python semantics:

.. code-block:: python

    from typing import NamedTuple

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None = None
        formatspec: str | None = None

These attributes are as follows:

* ``getvalue`` is the lambda-wrapped expression of the interpolation, ``lambda:
  name``.

* ``raw`` is the *expression text* of the interpolation, ``'name'``. Note that
  an alternative and possibly better name for this attribute could be ``text``.

* ``conv`` is the optional conversion used, one of ``r``, ``s``, and ``a``,
   corresponding to repr, str, and ascii conversions. Note that as with
   f-strings, no other conversions are supported.

* ``formatspec`` is the optional formatspec. A formatspec is eagerly evaluated
   if it contains any expressions before being passed to the tag function. The
   interpretation of the ``formatspec`` is according to the tag function.

FIXME decide if ``raw`` or ``text`` is a better attribute name.

In the CPython reference implementation, implementing ``Thunk`` in C would
use the equivalent `Struct Sequence Objects
<https://docs.python.org/3/c-api/tuple.html#struct-sequence-objects>`_ (see
such code as `os.stat_result
<https://docs.python.org/3/library/os.html#os.stat_result>`_).

Thunk expression evaluation
---------------------------

Expression evaluation for thunks is the same as in :pep:`498`, except that all
expressions are always implicitly wrapped with a ``lambda``::

    The expressions that are extracted from the string are evaluated in the context
    where the tag string appeared. This means the expression has full access to its
    lexical scope, including local and global variables. Any valid Python expression
    can be used, including function and method calls.

This means that the lambda wrapping here uses the usual lexical scoping. As with
f-strings, there's no need to use ``locals()``, ``globals()``, or frame
introspection with ``sys._getframe`` to evaluate the interpolation.

The code of the expression text, ``'trade'``, is available, which means there is
no need to use ``inspect.getsource``, or otherwise parse the source code to get
this expression text.

Format specification
--------------------

The format spec is by default ``None`` if it is not specified in the
corresponding interpolation in the tag string.

Because the tag function is completely responsible for processing chunks and
thunks, there is no required interpretation for the format spec and
conversion in a thunk. For example, this is a valid usage:

.. code-block:: python

    html'<div id={id:int}>{content:HTMLNode|str}</div>'

In this case the formatspec for the second thunk is the string
``'HTMLNode|str'``; it is up to the ``html`` tag to do something with the
"format spec" here, if anything.

Tag function arguments
----------------------

The tag function has the following signature:

.. code-block:: python
    def mytag(*args: Chunk | Thunk) -> Any:
        ...

This corresponds to the following protocol:

.. code-block:: python

    class Tag(Protocol):
        def __call__(self, *args: Chunk | Thunk) -> Any:
            ...

Because of subclassing, the signature for ``mytag`` can of course be widened to
the following, at the cost of losing some type specificity:

.. code-block:: python

    def mytag(*args: str | tuple) -> Any:
        ...

Function application
--------------------

Tag strings desugar as follows:

.. code-block:: python

    mytag'Hi, {name}!'

is equivalent to

.. code-block:: python

    mytag('Hi, ', (lambda: name, 'name', None, None), '!')

Tag names are part of the same namespace
----------------------------------------

Because tag functions are simply callables on a sequence of strings and thunks,
it is possible to write code like the following:

.. code-block:: python

    length = len'foo'

In practice, this seems to be a remote corner case. We can readily define
functions that are named ``f``, but in actual usage they are rarely, if ever,
mixed up with a f-string. Similar observations can apply to the use of soft
keywords like ``match`` or ``type``. The same should be true for tag strings.

No empty string chunks
----------------------

Alternation between string chunks and thunks is commonly seen, but it depends on
the tag string, because string chunks will never have a value that is the empty
string. For example:

.. code-block:: python

    mytag'{a}{b}{c}'

results in:

.. code-block:: python

    mytag(Thunk(lambda: a, 'a'), Thunk(lambda: b, 'b'), Thunk(lambda: c, 'c'))

Likewise

.. code-block:: python

    mytag''

results in this evaluation:

.. code-block:: python

    mytag()


Tool Support
============

Annotating tag functions
------------------------

Tag functions can be annotated in a number of ways, such as to support an IDE or
a linter for the underlying DSL. For example:

.. code-block:: python

    from dataclasses import dataclass, field
    from typing import Chunk, Thunk

    @dataclass
    class Language:
        mimetype: str  # standard language name
        raw: bool  # whether the string will be used as-is (raw) or cooked by decoding

    HtmlChildren = list[str, 'HtmlNode']
    HtmlAttributes = dict[str, Any]

    @dataclass
    class HtmlNode:
        tag: str | Callable[..., HtmlNode] = ''
        attributes: HtmlAttributes = field(default_factory=dict)
        children: HtmlChildren = field(default_factory=list)
    ...

    type HTML = Annotated[T, Language(mimetype='text/html', raw=False)]

    def html(*args: Chunk | Thunk) -> HTML[HtmlNode]:
        # process any chunks as cooked strings
        ...


Backwards Compatibility
=======================

Security Implications
=====================

The security implications of working with interpolations, with respect to
thunks, are as follows::

1. Scope lookup is the same as f-strings (lexical scope). This model has been
   shown to work well in practice.

2. Tag functions can ensure that any interpolations are done in a safe fashion,
   including respecting the context in the target DSL.

Performance Impact
==================

- Faster than getting frames
- Opportunities for speedups

How To Teach This
=================

Common patterns seen in writing tag functions
=============================================

Structural pattern matching
---------------------------

Iterating over the arguments with structural pattern matching is the expected
best practice for many tag function implementations:

.. code-block:: python

    def tag(*args: str | Thunk) -> Any:
        for arg in args:
            match arg:
                case str():
                    ... # handle each string chunk
                case getvalue, raw, conv, format:
                    ... # handle each interpolation

Recursive construction
----------------------

FIXME Describe the use of a marker class

Memoizing parses
-----------------

Consider this tag string:

.. code-block:: python

    html'<li {attrs}>Some todo: {todo}</li>''

Regardless of the expressions ``attrs`` and ``todo``, we would expect that the
static part of the tag string should be parsed the same. So it is possible to
memoize the parse only on the strings ``'<li> ''``, ``''>Some todo: ''``,
``'</li>''``:

.. code-block:: python

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

Reference Implementation
========================

Rejected Ideas
==============

Cooked string chunks by default
-------------------------------

This approach of cooked vs raw is somewhat similar to what is done in tagged
template literals in JavaScript, although its `convention
<https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#raw_strings>`_
is that strings are by
default cooked, with ``raw`` available as an attribute.

However, the decoder for ``unicode-escape``, as of 3.6, returns a
``DeprecationWarning``, if the `escapes are not valid for a Python literal
string
<https://docs.python.org/dev/whatsnew/3.6.html#deprecated-python-behavior>`.

Additionally if the string is not raw, as of 3.12, this becomes a
``SyntaxWarning`` if it's in Python source text; see `this issue
<https://github.com/python/cpython/issues/98401>`_.

A simple example to show this would be ``r'\.py'`` vs ``'\.py'``; the first
usage would often be used with the ``re`` embedded DSL, but it's not a
permissible non-raw Python string literal, given that ``\.`` is not a valid
escape in Python source itself.

Given these caveats, providing a cooked string by default is rejected, to avoid
emitting unnecessary warnings on every construction of a ``Chunk`` with an
invalid Python literal string. In addition, it's possible to annotate a tag to
indicate to an IDE or other tool that the source text should be treated as raw
or cooked with respect to Python escapes, as was discussed with tool support.

Cached values for ``getvalue``
------------------------------

FIXME

Enable exact round-tripping of ``conv`` and ``formatspec``
----------------------------------------------------------

There are two limitations with respect to exactly round-tripping to the original
source text.

First, the ``formatspec`` can be arbitrarily nested:

.. code-block:: python

    mytag'{x:{a{b{c}}}}'

In this PEP and corresponding reference implementation, the formatspec
is eagerly evaluated to set the ``formatspec`` in the thunk, thereby losing the
original expressions.

Secondly, ``mytag'{expr=}'`` is parsed to being the same as
``mytag'expr={expr}``', as implemented in the issue `Add = to f-strings for
easier debugging <https://github.com/python/cpython/issues/80998>`_.

While it would be feasible to preserve round-tripping in every usage, this would
require an extra flag ``equals`` to support, for example, ``{x=}``, and a
recursive ``Thunk`` definition for ``formatspec``. The following is roughly the
pure Python equivalent of this type, including preserving the sequence
unpacking (as used in case statements):

.. code-block:: python

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None = None
        formatspec: str | None | tuple[str | Thunk, ...] = None
        equals: bool = False

        def __len__(self):
            return 4

        def __iter__(self):
            return iter((self.getvalue, self.raw, self.conv, self.formatspec))

However, the additional complexity to support exact round-tripping seems
unnecessary and is thus rejected.

No dotted tag names
------------------

While it is possible to relax the restriction to not use dotted names, much as was
done with decorators, this usage seems unnecessary and is thus rejected.

No implicit string concatenation
--------------------------------

Implicit tag string concatenation isn't supported, which is `unlike other string literals
<https://docs.python.org/3/reference/lexical_analysis.html#string-literal-concatenation>`_.

The expectation is that triple quoting is sufficient. If implicit string
concatenation is supported, results from tag evaluations would need to
support the ``+`` operator with ``__add__`` and ``__radd__``.

Because tag strings target embedded DSLs, this complexity introduces other
issues, such as determining appropriate separators. This seems unnecessarily
complicated and is thus rejected.

Acknowledgements
================

FIXME

Copyright
=========

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
