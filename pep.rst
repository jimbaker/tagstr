Abstract
========

This PEP introduces tag strings, which enables Python developers to create and
use their own custom tags (or prefixes) when working with string literals and
any interpolation. Tag strings are based on a related idea in JavaScript,
`tagged template literals
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates`_,
but they naturally extend string literal interpolation ("f-strings"), as
introduced to Python with :pep:`498`. Tag strings have a Pythonic syntax for both
the use of and the definition of tags.

Motivation
==========

Motivating example - HTML escaping
----------------------------------

Working with templates is a common need in Python programs. Popular packages
include Jinja, which supports general purpose templating; and Django Templates,
which specifically support HTML. However, such templates use their own
minilanguages and rules for resolving interpolations.

Also popular for templating are f-strings. For producing formatted strings, they
work well and are consequently popular. Interpolations in f-strings support
standard Python expressions with names resolved according to lexical scope. This
use of lexical scope means it is straightforward to reason about how expressions
are evaluated in interpolations.

But for more general templating use, using f-strings can be problematic.
Consider this HTML example:

.. code-block:: python

    brothers = 'Click & Clack'
    s = f'<div>Hi, {brothers}!/>'

When the expression ``brothers`` is interpolated into HTML text, the use of the
ampersand needs to be appropriately quoted, namely with ``&amp;``. There is of
course an existing solution in the stdlib:

.. code-block:: python

    from html import escape

    brothers = 'Click & Clack'
    s = f'<div>Hi, {escape(brothers)}!/>'

Note that this input could also be "unsanitized" and directly from a user and
therefore possibly a malicious injection attack; regardless it needs to be
escaped.

HTML also has the following additional cases to consider for escaping input,
even if such interpolations are generally not sourced from user input. These
cases depend on the context of the interpolations, specifically that they occur
within attributes or the tag itself and for the
specific attributes used:

* `HTML Attributes
  https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes`_, which
  naturally correspond to a ``dict`` mapping as input. One possible way of
  writing this is with a hypothetical function ``escape_attrs(dict: [str, Any])
  -> str``. So this could be used like so: ``f'<div
  {escape_attrs(attrs)}>...</div>''``

* `Boolean attributes https://html.spec.whatwg.org/#boolean-attributes`_  where
  the presence of the attribute indicates it is true, otherwise false. Example:
  ``f'<input {escape_boolean('checked', checked)} ...>'``. In particular per
  this spec, "[the] values 'true' and 'false' are not allowed on boolean
  attributes. To represent a false value, the attribute has to be omitted
  altogether."

* `style attribute
  https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/style`_,
  which is of the form ``key: value``, separated by a semicolon, and taking in
  account specific aspects of formatting values, such as colors with hashmarks.
  Example: ``f'<div {escape_style(props)}...>'.

Clearly, f-strings are not an ideal fit here. The context of the interpolations
has to be considered, as we saw with these cases, and there are still additional
contextual considerations:

* Nesting such constructs to generate HTML require systematic tracking of
  escapes.

* Do we want to use a virtual DOM approach? This is not going to work well with
  formatting strings directly, given the need to parse again to get the DOM. But
  direct construction of DOMs with a standard function approach require more
  setup with respect to tags and attributes to capture what can be done readily
  in source HTML.

* If we are looking at other output besides HTML, such as for logging, we may
  want to lazily render the interpolations, because they are potentially
  expensive and the logging level for that log means that the record will end
  not being emitted.

Introducing tag strings
-----------------------

The takeaway from looking at HTML templating is the importance of context for
determining how to perform interpolations. Such context requires parsing the
non-interpolated part of the string literal (in the body of the tag, or
interpolated as attributes). Additionally, the context includes how any
templating will be used.

This PEP proposes an alternative approach, **tag strings**, which generalize
f-strings. Tag strings are directly inspired by the use of `tagged template
literals
https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates`_
in JavaScript. Tag strings enable the authoring and use of arbitrary undotted
name prefixes (except those already reserved in Python), which we call **tags**.

In particular, we have the following generalization:

* a f-string is a sequence of strings (possibly raw, with the ``fr`` prefix) and
  interpolations (including format specification and conversions, such as ``!r``
  for ``repr``). This sequence is **implicitly evaluated** by concatenating
  these parts, and it results in a ``str``.

* a tag string is a sequence of **raw** strings and **thunks**, which generalize
  such interpolations. This sequence is implicitly evaluated by calling the
  **tag function** bound to the tag name with this sequence, and it can return
  an object of ``Any`` type.

This generalization means that tag strings can support a wide range of use
cases, including HTML, SQL, lazy f-strings, and shell commands.

Example tag usage - html
------------------------

Let's go back to the motivating example. This time we we will use a custom
``html`` tag; as seen here, this tag can be imported from an arbitary module
using standard import semantics:

.. code-block:: python

    from my_htmllib import html

    brothers = 'Click & Clack'
    dom = html'<div>Hi, {brothers}!/>'

First, interpolations are represented by thunks, which are named tuples. This
PEP proposes that the ``Thunk`` type can be imported from the ``typing`` module:

.. code-block:: python

    class Thunk(NamedTuple):
        getvalue: Callable[[], Any]
        raw: str
        conv: str | None
        formatspec: str | None

Per the type definition, ``getvalue`` is a no-arg function that can return
``Any`` value. For the ``brothers`` interpolation in the above example,
``getvalue`` would be ``lambda: brothers``.

The ``html`` tag function can be defined following this sketch:

.. code-block:: python

    from typing import Thunk

    # define a DOM type...

    def html(*args: str | Thunk) -> DOM:
        for arg in args:
            match arg:
                case str():
                    # parse arg in the context of an HTML template that
                    # is being built
                case getvalue, _, _, _:
                    # interpolate `getvalue()` in this HTML template

As a named tuple, thunks can be matched using a case statement either as a tuple
(as above), or with respect to the class ``Thunk`` and any desired attributes to
be structurally unpacked.

.. note::

    For more complete details on how to implement this fully using
    ``html.parser`` in the `stdlib
    https://docs.python.org/3/library/html.parser.html`_, see the companion
    tutorial PEP.

With an implemented ``html`` tag, it is then possible to write code like the
following:

.. code-block:: python

    from typing import Any
    from my_htmllib import html, DOM

    def title(report: str, props: dict[str, Any], styling: dict[str, Any]) -> DOM:
        return html'<div {props} style={styling}>Report: {report}</div>'

    report = 'Profit & Loss'  # arbitrary, so need to interpolate properly
    styling = {'color': 'blue'}  # for a CSS style tag, special interpolation required
    props = {FIXME, but include a boolean element}
    dom = title(report, props, styling)

It is also possible to recursively compose tag strings:

    FIXME todolist

Tag names like ``html`` bind to a callable, or **tag function**. Such tag
functions can use logic specific to the DSL it is working with, such as HTML and
any interpolation rules. In addition, because tag strings generalize f-strings,
it is possible to use Python in the construction in the template, given that any
interpolated expressions are Python expressions.

Specification
=============

In the rest of this specification, ``mytag`` will be used for an arbitrary tag.

Grammar
-------

The tag name can be any **undotted** name that isn't an existing valid string or
bytes prefix, as seen in the `lexical analysis specification
https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals`_:

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
https://docs.python.org/3/reference/lexical_analysis.html#string-literal-concatenation`_.

.. note::

    Tthe expectation is that triple quoting is sufficient. If string
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



.. note::

    In the CPython reference implementation, this would presumably use the equivalent
https://docs.python.org/3/c-api/tuple.html#struct-sequence-objects (as done with
for example ``os.stat_result`` https://docs.python.org/3/library/os.html#os.stat_result). A suitable importable type
will be made available from ``typing``.

In the example above, the thunk is equivalent to the following tuple:

.. code-block:: python

    lambda: name, 'name', None, None

The lambda wrapping here, ``lambda: name``, uses the usual lexical scoping. As
with f-strings, there's no need to use ``locals()``, ``globals()``, or frame
introspection with ``sys._getframe`` to evaluate the interpolation.

The code of the expression source is , ``'name'`` is available, which means there is no need to
use ``inspect.getsource``, or otherwise parse the source code to get this expression source.

The conversion and format spec are both ``None``.

In this example, ``mytag`` is evaluated as follows:

.. code-block:: python

    mytag(r'Hi, ', (lambda: name, 'name', None, None), r', welcome back!')

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

    Callable[[list[str | Thunk]], Any]

    (FIXME check starargs)


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
easier debugging https://github.com/python/cpython/issues/80998`_.

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

`Add = to f-strings for easier debugging
https://github.com/python/cpython/issues/80998`_

