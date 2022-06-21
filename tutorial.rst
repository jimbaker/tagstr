PEP: 999
Title: Tag Strings: Tutorial
Content-Type: text/x-rst


Abstract
========

This PEP is a tutorial for the tag strings PEP. This tutorial introduces tag
strings with respect to how they generalize f-strings, then works through how to
implement example tags. For each example tag, we show how tag strings make it
possible to correctly work with a target domain specific language (DSL), whether
it's the examples used here in this tutorial (shell, HTML, SQL, lazy f-strings),
or other tags.

We will also look at best practices for using tag strings.


Tutorial
========

Tag strings start with the functionality in f-strings, as described in PEP 498.
Let's take a look first at a simple example with f-strings::

    name = 'Bobby'
    s = f"Hello, {name}, it's great to meet you!"

The above code is the equivalent of writing this code::

    name = 'Bobby'
    s = 'Hello, ' + format(name, '') + ", it's great to meet you!"

    # or equivalently

    s = ''.join(['Hello, ', format(name, ''), ", it's great to meet you!"])

Here we see that the f-string syntax has a compact syntax for combining into one
string a sequence of strings -- ``"Hello, "`` and ``", it's great to meet
you!"`` -- with interpolations of values, which are formatted into strings.
Often this overall string construction is exactly what you want.

But consider this shell example. You want to use ``subprocess.run``, but for
your scenario you would like to use the full power of the shell, including pipes
and subprocesses. This means you have to use ``use_shell=True``::

    from subprocess import run

    path = 'some/path/to/data'
    print(run(f'ls -ls {path} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

However, this code as written is broken on any untrusted input. In other words,
we have a shell injection attack, or from xkcd, a Bobby Tables problem::

    path = 'foo; cat /etc/passwd'
    print(run(f'ls -ls {path} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

There's a straightforward fix, of course. Quote the interpolation of ``path``
with ``shlex.quote``::

    import shlex

    path = 'foo; cat /etc/passwd'
    print(run(f'ls -ls {shlex.quote(path)} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

However, this means that wherever you use such interpolations within a f-string,
you need to ensure that the interpolation is properly quoted. This extra step can
be easy to forget. Let's fix this potential oversight -- and lurking security
hole -- by using tag string support.

Writing a ``sh`` tag
--------------------

For the first example, we want to write a ``sh`` tag that automatically does this
interpolation for the user::

    path = 'foo; cat /etc/passwd'
    print(run(sh'ls -ls {path}', use_shell=True))

Fundamentally, tag strings are a straightforward generalization of f-strings:

* a f-string is a sequence of strings (possibly raw, with ``fr``) and
  interpolations (including format specification and conversions, such as ``!r``
  for ``repr``). This sequence is **implicitly evaluated** by concatenating these
  parts, and it results in a string.

* a tag string is a sequence of **raw** strings and **thunks**, which generalize
  such interpolations. This sequence is implicitly evaluated by calling the
  **tag function** bound to that name and which can return **any value**.

So in the example above::

    sh'ls -ls {path}'

``sh`` is the tag name. In evaluation, it looks up the name and applies it, just
as with other functions. In this exanple, it is a function with this signature::

    def sh(*args: str | Thunk) -> str:
        ...

So what is a thunk? It has the following type::

    Thunk = tuple[
        Callable[[], Any],  # getvalue
        str,  # raw
        str | None,  # conv
        str | None,  # formatspec
    ]

* ``getvalue`` is the lambda-wrapped expression of the interpolation. For
  ``sh'ls -ls {path}``, ``getvalue`` is ``lambda: path``. (For any arbitary
  expression ``expr``, it would be ``lambda: expr``.)
* ``raw`` is the **expression text** of the interpolation. In this example, it's
  ``path``.
* ``conv`` is the optional conversion used, one of `r`, `s`, and `a`,
  corresponding to repr, str, and ascii conversions.
* ``formatspec`` is the optional formatspec.

This then gives us the following generic signature for a **tag function**,
``some_tag``::

    def some_tag(*args: str | Thunk) -> Any:
        ...

Let's now write a first pass of ``sh``::

    def sh(*args: str | Thunk) -> str:
        command = []
        for arg in args:
            match arg:
                # handle each static part of the tag string
                case str():
                    command.append(arg)
                # handle each dynamic part of the tag string by interpolating it,
                # including the necessary shell quoting
                case getvalue, _, _, _:
                    command.append(shlex.quote(str(getvalue()))
        return ''.join(command)

Let's go through this code: for each arg, either it's a string (the static
part), or an interpolation (the dynamic part).

If it's a **static** part, it's shell code the developer using the ``sh`` tag
wrote to work with the shell. So this cannot be user input -- it's part of the
Python code, and it is therefore can be safely used without further quoting. (Of
course that code could have a bug, just like any other line of code in this
program.) Note that for tag strings, this will always be a raw string. This is
convenient for working with the shell - we might want to use regexes in ``grep``
or similar tools like the Silver Surfer (``ag``)::

    run(sh"find {path} -print | grep '\.py$'", shell=True)

If it's a **dynamic** part, it's a ``Thunk``. A tag string ``Thunk`` is a
tuple of a function (``getvalue``, takes no arguments, as we see with its type
signature), along with the other elements that were mentioned but not used here
(``raw``, ``conv``, ``formatspec``). To process the interpolation of the thunk,
you would use the following steps::

1. Call ``getvalue``
2. Quote its result with ``shlex.quote``
3. Interpolate, in this case by adding it to the ``command`` list in the above code

This implicit evaluation of the tag string, by calling the ``sh`` tag function,
then results in some arbitrary value -- in this case a ``str`` -- which can then
be used by some API, in this case ``subprocess.run``.

.. note:: Tag functions should not have visible side effects.

    It is a best practice for the evaluation of the tag string to not have any
    visible side effects, such as actually running this command. However, it can
    be a good idea to memoize, or perform some other processing, to support this
    evaluation. More about this in a later section on compiling the ``html`` tag.


Writing an `html` tag
---------------------

Tag strings also find applications where complex string interpolation would otherwise
require a templating engine like Jinja. Such engines typically come along with a Domain
Specific Language (DSL) for declaring templates that, given some contextual data, can be
compiled into larger bodies of text. An especially common use case for such engines is
the construction of HTML documents. For example, if you wanted to create a simple todo
list using Jinja it might look something like this::

    from jinja2 import Template

    t = Template("""
    <h1>{{ title }}</h1>
    <ol>{% for item in list_items %}
        <li>{{ item }}</li>{% endfor %}
    </ol>
    """)

    doc = t.render(title="My Todo List", list_items=["Eat", "Code", "Sleep"])

    print(doc)

Which will render::

    <h1>My Todo List</h1>
    <ol>
        <li>Eat</li>
        <li>Code</li>
        <li>Sleep</li>
    </ol>

This is simple enough, but Jinja templates can grow rapidly in complexity. For example,
if we want to dynamically set attributes on the ``<li>`` elements the Jinja template
it's far less straightforward::

    from jinja2 import Template

    t = Template(
        """
    <h1>{{ title }}</h1>
    <ol>{% for item in list_items %}
        <li {% for key, value in item["attributes"].items() %}{{ key }}={{ value }} {% endfor %}>
            {{ item["value"] }}
        </li>{% endfor %}
    </ol>
    """
    )

    doc = t.render(
        title="My Todo List",
        list_items=[
            {
                "attributes": {"value": "'3'"},
                "value": "Eat",
            },
            {
                "attributes": {"style": "'font-weight: bold'"},
                "value": "Eat",
            },
            {
                "attributes": {"type": "'a'", "style": "'font-weight: bold'"},
                "value": "Eat",
            },
        ],
    )

    print(doc)

The result of which is::

    <h1>My Todo List</h1>
    <ol>
        <li value='3' >
            Eat
        </li>
        <li style='font-weight: bold' >
            Eat
        </li>
        <li type='a' style='font-weight: bold' >
            Eat
        </li>
    </ol>

One of the problems here is that Jinja is a generic templating tool, so the specific
needs that come with rendering HTML, like expanding dynamic attributes, aren't supported
out of the box. More broadly, Jinja templates make it difficult to coordinate business
and UI logic since markup in the template is kept separate from your logic in Python.

Thankfully though, string tags give us an opportunity to develop a syntax specifically
designed to make declaring elaborate HTML documents easier. In the tutorial to follow,
you'll learn how to create an ``html`` tag which can do just this. Specifically, we'll
be taking inspiration from the JSX in order to bring your markup and logic closer
together. Here's a couple examples of what it will be able to do that would be
challenging to do with a standard templating solution::

    # Attribute expansion
    attributes = {"color": "blue", "style": {"font-style": "bold"}}
    assert (
        html"<h1 {attributes}>Hello, world!</h1>".render()
        == '<h1 color="blue" style="font-style:bold">Hello, world!<h1>'
    )

    # Recursive construction
    assert (
        html"<body>{html"<h{i}/>" for i in range(1, 4)}</body>".render()
        == "<body><h1></h1><h2></h2><h3></h3></body>"
    )

Perhaps most interestingly though, this ``html`` tag will output a structured
representation of the HTML which can be freely manipulated - a Document Object Model
(DOM) of sorts for HTML::

    node: HtmlNode = html"<h1/>"
    node.attributes["color"] = "blue"
    node.children.append("Hello, world!")
    assert node.render() == '<h1 color="blue">Hello, world!</h1>'

Where ``HtmlNode`` is defined as:


    HtmlAttributes = dict[str, Any]
    HtmlChildren = list[str, "HtmlNode"]

    class HtmlNode:
        """A single HTML document object model node"""

        type: str
        attributes: HtmlAttributes
        children: HtmlChildren

        def render(self) -> str:
            ...

This capability in particular is one which would be impossible, or at the very least
convoluted, to achieve with a templating engine like Jinja. By returning a DOM instead
of a string, this ``html`` tag allows for a much broader set of uses.

NOTE: we should probably come up with a simpler example than the one below

For example, while we can't strictly embed callbacks into any HTML we render, we can
correspond them with an ID which a client could send as part of an event. With this in
mind, we could trace the DOM for functions that have been assigned to
``HtmlNode.attributes`` in order to replace them with an ID that could used to relocate
and trigger them later::

    EventHandlers = dict[str, Callable[..., Any]]

    def load_event_handlers(node: HtmlNode) -> DomNode, EventHandlers:
        handlers = handlers or {}

        new_attributes: HtmlAttributes = {}
        for k, v in node.attributes.items():
            if isinstance(v, callable):
                handler_id = id(v)
                handlers[handler_id] = v
                new_attributes[f"data-handle-{k}"] = handler_id
            else:
                new_attributes[k] = v

        new_children: HtmlChildren = []
        for child in node.children:
            if isinstance(child, HtmlNode):
                child, child_handlers = load_event_handlers(child)
                handlers.update(child_handlers)
            new_children.append(child)

        return HtmlNode(type=node.type, attributes=new_attributes, children=new_children)

    handle_onclick = lambda event: ...
    handle_onclick_id = id(handle_onclick)

    button = html"<button onclick={handle_onclick} />"
    button, handlers = load_event_handlers(button)

    assert button.render() == f'<button data-handle-onclick="{handle_onclick_id}" />'
    assert handlers == {handle_onclick_id: handle_onclick}


The skeleton of an ``html`` tag
...............................

In contrast to the ``sh`` tag, which did not need to do any parsing, the ``html`` tag
must parse the HTML it receives since, to it needs to know the  it must know the
semantic meaning of values it will interpolate.



Recursive ``html`` construction
.............................

TODO: extend with a marker class

`html` components
.................

TODO: show how you can expand html tag to allow for HTML components

`fl` tag - lazy interpolation of f-strings
------------------------------------------

Up until now your tags always call the ``getvalue`` element in the thunk. Recall
that ``getvalue`` is the lambda that implicitly wraps each interpolation
expression. Let's consider a case when you may not want to **eagerly**
call ``getvalue``, but instead do so **lazily**. In doing so, we can avoid
the overhead of expensive computations unless the tag is actually rendered.

With this mind, you can write a lazy version of f-strings with a ``fl`` tag,
which returns an object that does the interpolation only if it is called with
``__str__`` to get the string.

Start by adding the following function to ``taglib``, since it's generally
useful. (FIXME: refactor such that it is presented when the tutorial first
covers conversions and formatting.) ::

    def format_value(arg: str | Thunk) -> str:
        match arg:
            case str():
                return arg
            case getvalue, _, conv, spec:
                value = getvalue()
                match conv:
                    case 'r': value = repr(value)
                    case 's': value = str(value)
                    case 'a': value = ascii(value)
                    case None: pass
                    case _: raise ValueError(f'Bad conversion: {conv!r}')
                return format(value, spec if spec is not None else '')

Now write the following function, which implements the PEP 498 semantics of
f-strings::

    def just_like_f_string(*args: str | Thunk) -> str:
        return ''.join((format_value(arg) for arg in decode_raw(*args)))

With this tag function (we will use it later in implementing another tag, but it
has the required signature for tags), you can now use it interchangeabley with
f-strings. Let's use the starting example of this tutorial to verify::

    name = 'Bobby'
    s = just_like_f_string"Hello, {name}, it's great to meet you!"

Note ``just_like_f_string`` results in the same concatenation of formatted
values.

So far, this functionality is not so interesting. But let's add some extra
indirection to get lazy behavior. Start by defining the ``LazyFString``
dataclass, along with the necessary imports::

    from dataclasses import dataclass
    from functools import cached_property
    from typing import *

    @dataclass
    class LazyFString:
        args: Sequence[str | Thunk]

        def __str__(self) -> str:
            return self.value

        @cached_property
        def value(self) -> str:
            return just_like_f_string(*self.args)

The ``cached_property`` decorator defers the evaluation of the construction of
the ``str`` from ``just_like_f_string`` until it is actually used. It is then
cached until a given ``LazyFString`` object is garbage collected, as usual. Now
write the tag function::

    def fl(*args: str | Thunk) -> LazyFString:
        return LazyFString(args)

You can now use the ``fl`` tag. Try it with logging. Let's assume the default
logging level -- so all message with at least ``WARNING`` will be logged::

    import logging  # add required import

    def report_called(f):
        @wraps(f)
        def wrapper(*args, **kwds):
            print('Calling wrapped function', f)
            return f(*args, **kwds)
        return wrapper

    @report_called
    def expensive_fn():
        return 42  # ultimate answer takes some time to compute! :)

    # Nothing is logged; neither report_called nor expensive_fn are called
    logging.info(fl'Expensive function: {expensive_fn()}')

    # However the following log statement is logged, and now expensive_fn is
    # actually called
    logging.warning(fl'Expensive function: {expensive_fn()}')

NOTE: This demo code implements the ``fl`` tag such that it has the same user
behavior as described in https://github.com/python/cpython/issues/77135. You can
further extend this example by looking at other possible caching.

`sql` tag
---------

The beginning of the tutorial introduced a shell injection attack, as
popularized by xkcd with "Bobby Tables." Of course, the `original injection in
the xkcd comic <https://xkcd.com/327/>`_ was for SQL::

    name = "Robert') DROP TABLE students; --"

which then might be naively used with SQLite3 with something like the
following::

    import sqlite3

    with sqlite3.connect(':memory:') as conn:
        cur = conn.cursor()
        # BOOM - don't do this!
        print(list(cur.execute(
            f'select * from students where first_name = "{name}"')))

This is a perennial question of Stack Overflow. Someone will ask, can I do
something like the above? "No" is the immediate response. Use parameterized
queries. Use a library like SQLAlchemy. These are valid answers.

However, occasionally there is a good reason to want to do something with
f-strings or similar templating. You might want to do DDL ("data definition
language") to work with your schemas in a dynamic fashion, such as creating a
table based on a variable. Or you are trying to build a very complex query
against a big data system. While it is possible to use SQLAlchemy or similar
tools to do such work, sometimes it may just be easier to use the underlying
SQL.

Let's implement a ``sql`` tag to do just that. Start with the following
observation: Any SQL text directly in string tagged with ``sql`` is safe,
because it cannot be from untrusted user input::

    from taglib import Thunk

    def sql(*args: str | Thunk) -> SQL:
        """Implements sql tag"""
        parts = []
        for arg in args:
            match arg:
                case str():
                    parts.append(arg)
                case getvalue, raw, _, _:
                    ...

As you have already done earlier in the tutorial, consider what substitutions to
support for the thunks.

**Placeholders**, such as with named parameters in SQLite3. This is safe,
because the SQL API -- such as sqlite3 library -- pass any arguments as data to
the executed SQL statement. In particular, use the ``raw`` expression
in the tag interpolation to get a nicely named parameter::

    from __future__ import annotations

    import re
    import sqlite3
    from collections import defaultdict
    from collections.abc import Sequence
    from dataclasses import dataclass, field
    from typing import Any

    from taglib import Thunk

    @dataclass
    class Param:
        raw: str
        value: Any

    def sql(*args: str | Thunk) -> SQL:
        """Implements sql tag"""
        parts = []
        for arg in args:
            match arg:
                case str():
                    parts.append(arg)
                case getvalue, raw, _, _:
                    parts.append(Param(raw, getvalue()))
        return SQL(parts)

Let's defined a useful ``SQL`` statement class::

    @dataclass
    class SQL(Sequence):
        """Builds a SQL statements and any bindings from a list of its parts"""
        parts: list[str | Param]
        sql: str = field(init=False)
        bindings: dict[str, Any] = field(init=False)

        def __post_init__(self):
            self.sql, self.bindings = analyze_sql(self.parts)

        def __getitem__(self, index):
            match index:
                case 0: return self.sql
                case 1: return self.bindings
                case _: raise IndexError

        def __len__(self):
            return 2

Note that the reason you are implementing the ``Sequence`` abstract base class
is so you can readily call it with cursor ``execute`` like so::

    name = 'C'
    date = 1972

    with sqlite3.connect(':memory:') as conn:
        cur = conn.cursor()
        cur.execute('create table lang (name, first_appeared)')
        cur.execute(*sql'insert into lang values ({name}, {date})')

The helper method ``analyze_sql`` is fairly simple to start::

    def analyze_sql(parts: list[str | Part]) -> tuple[str, dict[str, Any]]:
        text = []
        bindings = {}
        for part in parts:
            match part:
                case str():
                    text.append(part)
                case Param(raw, value):
                    bindings[name] = value
                    text.append(f':{name}')
        return ''.join(text), bindings

Now you want to add full support for two other substitutions, identifiers and
SQL fragments (such as subqueries).

**Identifiers** are things like table or column names. This requires direct
substitution in the SQL statement, but it can be done safely if it is
appropriately quoted; and your SQL statement properly uses it (no bugs!). So
this allows your ``sql`` tag users to write something like the following::

    table_name = 'lang'
    name = 'C'
    date = 1972

    with sqlite3.connect(':memory:') as conn:
        cur = conn.cursor()
        cur.execute(*sql'create table {Identifier(table_name)} (name, first_appeared)')

Of course, you probably don't want any arbitrary user on the Internet to create
tables in your database, but at least it's not vulnerable to a SQL injection
attack. More importantly, by marking it with ``Identifier`` you know exactly
where in your logic this usage happens.

Implement this ``Identifier`` support with a marker class::

    SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE = re.compile(r'[a-z_][a-z0-9_]*')

    def _quote_identifier(name: str) -> str:
        if not name:
            raise ValueError("Identifiers cannot be an empty string")
        elif SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE.fullmatch(name):
            # Do not quote if possible
            return name
        else:
            s = name.replace('"', '""')  # double any quoting to escape it
            return f'"{s}"'

    class Identifier(str):
        def __new__(cls, name):
            return super().__new__(cls, _quote_identifier(name))

The other substitution you may want to allow is **recursive substitution**,
which is where you build up a statement out of other SQL fragments. As you saw
earlier with other recursive substitutions, this is safe so long as it it made
of safe usage of literal SQL, placeholders, and identifiers; and it is also
correct if the named params don't collide. However, you already have what you
need for such substitutions with the ``SQL`` statement class you defined
earlier.

Putting this together::

    def sql(*args: str | Thunk) -> SQL:
        """Implements sql tag"""
        parts = []
        for arg in args:
            match arg:
                case str():
                    parts.append(arg)
                case getvalue, raw, _, _:
                    match value := getvalue():
                        case SQL() | Identifier():
                            parts.append(value)
                        case _:
                            parts.append(Param(raw, value))
        return SQL(parts)

You need to change the dataclass fields definition, so that ``parts`` can
include other SQL fragments::

    @dataclass
    class SQL(Sequence):
        parts: list[str | Param | SQL]  # added SQL to this line
        sql: str = field(init=False)
        bindings: dict[str, Any] = field(init=False)

And lastly let's support recursive construction, plus properly handle named
parameters so they don't collide (via a simple renaming)::

    def analyze_sql(parts, bindings=None, param_counts=None) -> tuple[str, dict[str, Any]]:
        if bindings is None:
            bindings = {}
        if param_counts is None:
            param_counts = defaultdict(int)

        text = []
        for part in parts:
            match part:
                case str():
                    text.append(part)
                case Identifier(value):
                    text.append(value)
                case Param(raw, value):
                    if not SQLITE3_VALID_UNQUOTED_IDENTIFIER_RE.fullmatch(raw):
                        # NOTE could slugify this expr, eg 'num + b' -> 'num_plus_b'
                        raw = 'expr'
                    param_counts[(raw, value)] += 1
                    count = param_counts[(raw, value)]
                    name = raw if count == 1 else f'{raw}_{count}'
                    bindings[name] = value
                    text.append(f':{name}')
                case SQL(subparts):
                    text.append(analyze_sql(subparts, bindings, param_counts)[0])
        return ''.join(text), bindings

`html` tag, revisited
---------------------

TODO: compilation to a virtual DOM object, such as used in Reactive
