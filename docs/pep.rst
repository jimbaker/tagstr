Abstract
========

This PEP introduces tag strings for custom, repeatable string processing. Tag strings
are an extension to f-strings, with a custom function -- the "tag" -- in place of the
`f` prefix. This function can then provide rich features such as safety checks, lazy
evaluation, domain specific languages (DSLs) for web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages.

Relationship With Other PEPs
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

Python f-strings became very popular, very fast. The syntax was simple, convenient, and
interpolated expressions had access to regular scoping rules. However, f-strings have
two main limitations - expressions are eagerly evaluated, and interpolated values
cannot be intercepted. The former means that f-strings cannot be re-used like templates,
and the latter means that how values are interpolated cannot be customized.

Templating in Python is currently achieved using packages like Jinja2 which bring their
own templating languages for generating dynamic content. In addition to being one more
thing to learn, these languages are not nearly as expressive as Python itself. This
means that business logic, which cannot be expressed in the templating language, must be
written in Python instead, spreading the logic across different languages and files.

Likewise, the inability to intercept interpolated values means that they cannot be
sanitized or otherwise transformed before being integrated into the final string. Here,
the convenience of f-strings could be considered a liability. For example, a user
executing a query with `sqlite3 <https://docs.python.org/3/library/sqlite3.html>`__
may be tempted to use an f-string to embed values into their SQL expression instead of
using the ``?`` placeholder and passing the values as a tuple to avoid an
`SQL injection attack <https://en.wikipedia.org/wiki/SQL_injection>`__.

Tag strings address both these problems by extending the f-string syntax to provide
developers access to the string and its interpolated values before they are combined. In
doing so, tag strings may be interpreted in many different ways, opening up the
possibility for DSLs and other custom string processing.

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
- Tag strings represent this interpolation part as a *thunk*
- A thunk is a tuple whose first item is a lambda
- Calling this lambda evaluates the expression using the usual lexical scoping

The ``*args`` list is a sequence of "chunks" and "thunks". A chunk is just a
string. But what is a "thunk"? It's a tuple representing how tag strings
processed the interpolation into a form useful for your tag function. Thunks
are fully described below in `Specification`_.

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

Valid Tag Names
---------------

The tag name can be any **undotted** name that isn't already an existing valid
string or bytes prefix, as seen in the `lexical analysis specification
<https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals>`_,
Therefore these prefixes can't be used as a tag:

.. code-block:: text

    stringprefix: "r" | "u" | "R" | "U" | "f" | "F"
                : | "fr" | "Fr" | "fR" | "FR" | "rf" | "rF" | "Rf" | "RF"

    bytesprefix: "b" | "B" | "br" | "Br" | "bR" | "BR" | "rb" | "rB" | "Rb" | "RB"


Tags Must Immediately Precede the Quote Mark
--------------------------------------------

As with other string literal prefixes, no whitespace can be between the tag and the
quote mark.

PEP 701
-------

Tag strings support the full syntax of :pep:`701` in that any string literal,
with any quote mark, can be nested in the interpolation. This nesting includes
of course tag strings.

Evaluating Tag Strings
----------------------

When the tag string is evaluated, the tag must have a binding, or a `NameError`
is raised; and it must be a callable, or a `TypeError` is raised. This behavior
follows from the de-sugaring of:

.. code-block:: python

    trade = 'shrubberies'
    mytag'Did you say "{trade}"?'

to

.. code-block:: python

    mytag(Chunk(r'Did you say "'), Thunk(lambda: trade, 'trade'), Chunk(r'"?'))

String Chunks
-------------

In the earlier example, there are two string chunks, ``r'Did you say "'`` and
``r'"?'``.

String chunks are internally stored as the source raw strings. Raw strings
are used because tag strings are meant to target a variety of DSLs, such as
the shell and regexes. Such DSLs have their own specific treatment of
metacharacters, namely the backslash. (This approach follows the usual
convention of using the r-prefix for regexes in Python itself, given that
regexes are their own DSL.)

However, often the "cooked" string is what is needed, by decoding the string as
if it were a standard Python string. Because such decoding might be non-obvious,
the tag function will be be called with ``Chunk`` for any string chunks.
``Chunk`` *is-a* ``str``, but has an additional property, ``cooked`` that
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

A thunk is the data structure representing the interpolation from the tag
string. Thunks enable a delayed evaluation model, where the interpolation
expression is computed as needed (if at all); this computation can even be
memoized by the tag function.

In addition, the original text of the interpolation expression is made
available to the tag function. This can be useful for debugging or
metaprogramming.

The type ``Thunk`` will be made available from ``typing``, with
the following pure-Python semantics:

.. code-block:: python

    from typing import NamedTuple

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        expr: str
        conv: Literal['a', 'r', 's'] | None = None
        formatspec: str | None = None

Given this example interpolation:

.. code-block:: python

    mytag'{trade!r:some-formatspec}'

these attributes are as follows:

* ``getvalue`` is the lambda-wrapped expression for the interpolation. Example:
  ``lambda: trade``. (Lambda wrapping results in a zero-arg function.)

* ``expr`` is the *expression text* of the interpolation. Example: ``'trade'``.
  (The lambda wrapping is implied.)

* ``conv`` is the
  `optional conversion <https://docs.python.org/3/library/string.html#format-string-syntax>`_
  to be used by the tag function, one of ``r``, ``s``, and ``a``, corresponding to repr, str,
  and ascii conversions. Note that as with f-strings, no other conversions are supported.
  Example: ``'r'``.

* ``formatspec`` is the optional formatspec string. A formatspec is eagerly
  evaluated if it contains any expressions before being passed to the tag
  function. Example: ``'some-formatspec'``.

In all cases, the tag function determines how to work with the ``Thunk``
attributes.

In the CPython reference implementation, implementing ``Thunk`` in C would
use the equivalent `Struct Sequence Objects
<https://docs.python.org/3/c-api/tuple.html#struct-sequence-objects>`_ (see
such code as `os.stat_result
<https://docs.python.org/3/library/os.html#os.stat_result>`_).

Thunk Expression Evaluation
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

Format Specification
--------------------

The format spec is by default ``None`` if it is not specified in the
tag string's corresponding interpolation.

Because the tag function is completely responsible for processing chunks and
thunks, there is no required interpretation for the format spec and
conversion in a thunk. For example, this is a valid usage:

.. code-block:: python

    html'<div id={id:int}>{content:HTMLNode|str}</div>'

In this case the formatspec for the second thunk is the string
``'HTMLNode|str'``; it is up to the ``html`` tag to do something with the
"format spec" here, if anything.

Tag Function Arguments
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

Function Application
--------------------

Tag strings desugar as follows:

.. code-block:: python

    mytag'Hi, {name}!'

This is equivalent to:

.. code-block:: python

    mytag('Hi, ', (lambda: name, 'name', None, None), '!')

Tag Function Names are in the Same Namespace
--------------------------------------------

Because tag functions are simply callables on a sequence of string chunks and
thunks, it is possible to write code like the following:

.. code-block:: python

    length = len'foo'

In practice, this seems to be a remote corner case. We can readily define
functions that are named ``f``, but in actual usage they are rarely, if ever,
mixed up with a f-string. Similar observations can apply to the use of soft
keywords like ``match`` or ``type``. The same should be true for tag strings.

No Empty String Chunks
----------------------

Alternation between string chunks and thunks is commonly seen, but it depends on
the tag string. String chunks will never have a value that is the empty string:

.. code-block:: python

    mytag'{a}{b}{c}'

...which results in this desugaring:

.. code-block:: python

    mytag(Thunk(lambda: a, 'a'), Thunk(lambda: b, 'b'), Thunk(lambda: c, 'c'))

Likewise:

.. code-block:: python

    mytag''

...results in this desugaring:

.. code-block:: python

    mytag()


Tool Support
============

Annotating Tag Functions
------------------------

Tag functions can be annotated in a number of ways, such as to support an IDE or
a linter for the underlying DSL. For example, both PyCharm and VSCode have specific support
for embedding DSLs:

* PyCharm calls this `language injections
  <https://www.jetbrains.com/help/pycharm/using-language-injections.html>`_.

* VScode calls this `embedded languages
  <https://code.visualstudio.com/api/language-extensions/embedded-languages>`_.

GitHub also uses a `registry of known languages
<https://github.com/github-linguist/linguist/blob/master/lib/linguist/languages.yml>`_,
as part of its Linguist project, which could be potentially leveraged.

 For example, let's define a convention for defining an embedded DSL with
 respect to Linguist. We will use function annotations introduced by :pep:`593`:

.. code-block:: python

    @dataclass
    class Language:
        linguist: str  # standard language name/alias known to GitHub's Linguist
        cooked: bool = True

    type HTML = Annotated[T, 'language': 'HTML', 'registry': 'linguist']

This can then be put together with a DOM class for HTML (this comes from one of
the tag string examples):

.. code-block:: python

    HtmlChildren = list[str, 'HtmlNode']
    HtmlAttributes = dict[str, Any]

    @dataclass
    class HtmlNode:
        tag: str | Callable[..., HtmlNode] = ''
        attributes: HtmlAttributes = field(default_factory=dict)
        children: HtmlChildren = field(default_factory=list)
        ...

Then combine together to indicate that the tag function ``html`` works with an
embedded DSL that supports HTML:

.. code-block:: python

    def html(*args: Chunk | Thunk) -> HTML[HtmlNode]:
        # process any chunks as cooked strings that are HTML fragments,
        # and should be parsed/linted/highlighted accordingly
        ...


Backwards Compatibility
=======================

Security Implications
=====================

The security implications of working with interpolations, with respect to
thunks, are as follows:

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

Common Patterns Seen In Writing Tag Functions
=============================================

Structural Pattern Matching
---------------------------

Iterating over the arguments with structural pattern matching is the expected
best practice for many tag function implementations:

.. code-block:: python

    def tag(*args: str | Thunk) -> Any:
        for arg in args:
            match arg:
                case str():
                    ... # handle each string chunk
                case getvalue, expr, conv, formatspec:
                    ... # handle each interpolation

Recursive Construction
----------------------

FIXME Describe the use of a marker class

Memoizing Parses
-----------------

Consider this tag string:

.. code-block:: python

    html'<li {attrs}>Some todo: {todo}</li>''

Regardless of the expressions ``attrs`` and ``todo``, we would expect that the
static part of the tag string should be parsed the same. So it is possible to
memoize the parse, but only on the strings ``'<li> ''``, ``''>Some todo: ''``,
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

Cooked String Chunks By Default
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

A simple example to show this would be ``r'\.py'`` vs ``'\.py'``. The first
usage would often be used with the ``re`` embedded DSL. However, it's not a
permissible non-raw Python string literal, given that ``\.`` is not a valid
escape in Python source itself.

Given these caveats, providing a cooked string by default is rejected, to avoid
emitting unnecessary warnings on every construction of a ``Chunk`` with an
invalid Python literal string. In addition, it's possible to annotate a tag to
indicate to an IDE or other tool that the source text should be treated as raw
or cooked with respect to Python escapes, as was discussed with tool support.

Cached Values For ``getvalue``
------------------------------

FIXME

Enable Exact Round-Tripping of ``conv`` and ``formatspec``
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

No Dotted Tag Names
------------------

While it is possible to relax the restriction to not use dotted names, much as was
done with decorators, this usage seems unnecessary and is thus rejected.

No Implicit String Concatenation
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

FIXME include contributors to this repo, including commenters on issues

Copyright
=========

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
