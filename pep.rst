Abstract
========

Introduce tag strings and tag functions.

Motivation
==========

Working with templates is a common need in Python programs. Popular packages
include Jinja, which supports general purpose templating, and Django Templates,
which specifically support HTML. However, such templates use their own
minilanguages and rules for resolving interpolations.

Also popular for templating are f-strings. For producing formatted strings, they
work well. Interpolations in f-strings support standard Python expressions with
names resolved according to lexical scope. This combines well with other Python
code, which makes it easy to reason about what happens. (In constrast, templating
approaches that work by using dynamic scope via `sys._getframe` result in corner
cases around the use of nested functions and related constructs like
comprehensions.)

But for more general templating use, using f-strings can be problematic.
Consider this example:

.. code-block:: python

    brothers = 'Click & Clack'
    s = f'<div>Hi, {brothers}!/>'

When the expression ``brothers`` is interpolated into HTML text, the use of the
ampersand needs to be appropriately quoted, namely with ``&amp;``. There is of
course an existing solution in the stdlib:

.. code-block:: python

    from html import escape

    s = f'<div>Hi, {escape(brothers)}!/>'

But this solution requires always tracking any text that requires such escaping,
including unsanitized, possibly malicious input (eg "Bobby Tables" attacks).
There are numerous Q&A on StackOverflow discussing inappropriate usage of
f-strings, such as generating code for HTML, shell, and SQL. Often the advice
is, use a package like SQLAlchemy. (FIXME: battle tested, but what if one needs
to write their own package?)

 (FIXME: add some supporting citations for the above paragraph.)

This is because f-strings are unaware of the context of their templating, among
other limitations.

This PEP proposes an alternative approach, **tag strings**, which generalize
f-strings. Tag strings are directly inspired by the use of tagged template
literals]() in JavaScript. Tag strings enable the authoring and use of arbitrary
undotted name prefixes (except those already reserved in Python), which we call
**tags**.

Parsing.

In particular, we have the following generalization::

* a f-string is a sequence of strings (possibly raw, with the ``fr`` prefix) and
  interpolations (including format specification and conversions, such as ``!r``
  for ``repr``). This sequence is **implicitly evaluated** by concatenating
  these parts, and it results in a string.

* a tag string is a sequence of **raw** strings and **thunks**, which generalize
  such interpolations. This sequence is implicitly evaluated by calling the
  **tag function** bound to the tag name and which can return **any value**.

This generalization means that tag strings can support a wide range of use
cases, including HTML, SQL, lazy f-strings, and shell commands.

Example tag usage - html
========================

Let's look at a starting example, where we will look at how to use an ``html``
tag:

.. code-block:: python

    from my_htmllib import html

    brothers = 'Click & Clack'
    dom = html'<div>Hi, {brothers}!/>'

Importantly, ``html`` is a name bound to a tag function, as imported from
``my_htmllib`` (with normal import semantics). Tag functions are responsible for
parsing the tag string and working with any interpolations; they can return any
value.

Given tag strings, it's possibe to write code like the following:

.. code-block:: python

    from my_htmllib import html, DOM

    def title(report: str, props: dict[str, Any], styling: dict[str, Any]) -> DOM:
        return html'<div {props} style={styling}>Report: {report}</div>'

    report = 'Profit & Loss'  # arbitrary, so need to interpolate properly
    styling = {'color': 'blue'}  # for a CSS style tag, special interpolation required
    props = {FIXME, but include a boolean element}
    dom = title(report, props, styling)

Example boolean:

.. code-block:: html

    <input type='checkbox' checked id={id}/>

See https://html.spec.whatwg.org/, specifically https://html.spec.whatwg.org/#boolean-attributes:

    The values "true" and "false" are not allowed on boolean attributes. To
    represent a false value, the attribute has to be omitted altogether.

https://html.spec.whatwg.org/#the-style-attribute

It is also possible to recursively construct tag strings::

    FIXME todolist

Tag names like ``html`` bind to a callable, or **tag function**. Such tag
functions can use logic specific to the DSL it is working with, such as HTML and
any interpolation rules. In addition, because tag strings generalize f-strings,
it is possible to use Python in the construction in the template, given that any
interpolated expressions are Python expressions.

Specification
=============

A tag string generalizes f-strings

In the rest of this specification, ``mytag`` will be used for an arbitrary tag name:

.. code-block:: python

    mytag'Hi, {name}!'

Grammar
-------

tag - undotted name
Such names cannot be a valid string prefix

Other tag names that might be popular include ``html``, ``sql``, ``sh``.

The tag name can be any undotted name that isn't an [existing valid string or bytes
prefix](https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals),
namely the following:

.. code-block:: text

    stringprefix: "r" | "u" | "R" | "U" | "f" | "F"
                : | "fr" | "Fr" | "fR" | "FR" | "rf" | "rF" | "Rf" | "RF"

    bytesprefix: "b" | "B" | "br" | "Br" | "bR" | "BR" | "rb" | "rB" | "Rb" | "RB"

As with ordinary string literals, no whitespace can be between the tag and the quote.

Tags are undotted names. (This restriction could be relaxed to dotted names in
the future, if there is a compelling example.)

String concatenation
--------------------

Tag string concatenation is not supported, which is unlike other string
literals.
https://docs.python.org/3/reference/lexical_analysis.html#string-literal-concatenation

(It is possible to relax this in the future, but the expectation is that triple
quoting is sufficient. If relaxed, results from tag evaluations would need to
support the ``+`` operator with ``__add__`` and ``__radd__``.)


String fragments
----------------

Raw strings

Thunk
-----

The interpolation ``{name}`` is represented by a thunk, which is a tuple, more
specifically a named tuple:

.. code-block:: python

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None
        formatspec: str | None

.. note::

    In the CPython reference implementation, this would presumably use the equivalent
https://docs.python.org/3/c-api/tuple.html#struct-sequence-objects (as done with
for example ``stat_result``,
https://docs.python.org/3/library/os.html#os.stat_result). A suitable import
will be made available, say from ``typing``.

In this example, the thunk is the following tuple:

.. code-block:: python

    lambda: name, 'name', None, None

The lambda wrapping here, ``lambda: name``, uses the usual lexical scoping. As
with f-strings, there's no need to use ``locals()``, ``globals()``, or frame
introspection with ``sys._getframe`` to evaluate the interpolation.

The expression source, ``'name'`` is available, which means there is no need to
use ``inspect.getsource`` and then use column information to further look
up/parse the expression source of the interpolation.

The conversion and format spec are both ``None``.

In this example, ``tag`` is evaluated as follows:

.. code-block:: python

    tag(r'Hi, ', (lambda: name, 'name', None, None), r', welcome back!')


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


Interpolations and thunks
-------------------------

TODO: this needs to be changed in the reference implementation/discussed in
issues, specifically bikeshedding. It would seem to be better used as a
protocol, for flexibility.



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

Then the following holds for the two thunks TODO complete this example::

* ``getvalue`` is the lambda-wrapped expression of the interpolation, ``lambda: name``.
* ``raw`` is the **expression text** of the interpolation, ``'name'``
* ``conv`` is the optional conversion used, one of `r`, `s`, and `a`,
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
--------------------------

There are two limitations with respect to roundtripping to the exact original raw text.

First, the ``formatspec`` can be arbitrarily nested:

.. code-block:: python

    tag'{x:{a{b{c}}}}'

However, in this PEP and corresponding reference implementation, the formatspec
is eagerly evaluated to get the ``formatspec`` in the thunk.
``c``).

Secondly, ``tag'{expr=}'`` is parsed to being the same as ``tag'expr={expr}``'

While it would be feasible to preserve roundtripping in every usage, this would
require an extra flag ``equals`` for ``{x=}`` and a recursive ``Thunk``
definition for ``formatspec``. The following is roughly the pure Python
equivalent of this type, including preserving the sequence unpacking:

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

This additional complexity seems unnecessary.


Example tag implementation - fl
===============================

TODO

FIXME: rewrite the following, it needs to be specific that it is
* a string
* prefixed by something
* which gets translated into the desired sequence


Authoring such tags need to consider the following::

* Parsing the DSL associated with that tag
* Interpolations
  - Recursive construction, where templates embed other templates
  - Quoting

See the companion tutorial PEP [FIXME link] for how to author the ``html`` and
other tags, including parsing an HTML template and quoting interpolations.


Common patterns seen in writing tag functions
=============================================

Recursive construction
----------------------

Some type of marker class


Structural pattern matching
---------------------------

Iterating over the arguments with structural pattern matching is the expected
best practice for many tag function implementations:

.. code-block:: python

    def tag(*args: str | Thunk) -> Any:
        for arg in args:
            match arg:
                case str():
                    ... # handle each string fragment
                case getvalue, raw, conv, format:
                    ... # handle each interpolation

This can then be nested, to support recursive construction:

.. code-block:: python

    TODO

Decoding raw strings
--------------------

One possible implementation:

.. code-block:: python

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

Consider this tag string:

.. code-block:: python

    html"<li {attrs}>Some todo: {todo}</li>"

Regardless of the expressions ``attrs`` and ``todo``, we would expect that the
static part of the tag string should be parsed the same. So it is possible to
memoize the parse only on the strings ``'<li> ''``, ``''>Some todo: ''``,
``'</li>''``:

.. code-block:: python

    def memoization_key(*args: str | Thunk) -> tuple[str...]:
        return tuple(arg for arg in args if isinstance(arg, str))

Such tag functions can memoize as follows::

1. Compute the memoization key
2. Check in the cache if there's an existing parsed templated for that
   memoization key
3. If not, parse, keeping tracking of interpolation points
4. Apply interpolations to parsed template

TODO need to actually write this - there's an example of how to do this for
writing an ``html`` tag in the companion tutorial PEP.


Reference Implementation
========================

AST
---

FIXME are we going to actually show the AST? Depends on if there are PEPs that
do that...

Appendix
========

Tagged template literals in JavaScript
--------------------------------------


Note that JSX expressions are actually functions that result in JavaScript
objects - so very close to what we are doing here with tag strings.

https://reactjs.org/docs/introducing-jsx.html


Related mailing list discussion
-------------------------------

pyxl
----


Comparison with :pep:`501`
--------------------------

It is possible to implement the interpolation templates of :pep:`501`, which use
an ``i`` prefix, with the following tag function:

.. code-block:: python

    def i(*args: str | Thunk) -> InterpolationTemplate:
        raw_template = []
        parsed_template = []
        last_str_arg = ''
        field_values = []
        format_specifiers = []
        for arg, raw_arg in zip(decode_raw(*args), args):
            match arg:
                case str():
                    raw_template.append(raw_arg)
                    last_str_arg = arg
                case getvalue, raw, conv, formatspec:
                    value = getvalue()
                    raw_template.append(f"{{{raw}{'!' + conv if conv else ''}{':' + formatspec if formatspec else ''}}}")
                    parsed_template.append((last_str_arg, raw))
                    field_values.append(value)
                    format_specifiers.append('' if formatspec is None else formatspec)
                    last_str_arg = ''
        if last_str_arg:
            parsed_template.append((last_str_arg, None))

        return InterpolationTemplate(
            ''.join(raw_template),
            tuple(parsed_template),
            tuple(field_values),
            tuple(format_specifiers)
        )


References
==========

https://github.com/python/cpython/issues/80998
Add = to f-strings for easier debugging
