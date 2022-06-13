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
string a sequence of strings -- ``'Hello, '`` and ``", it's great to meet
you!"`` -- with interpolations of values, which are formatted into strings.
Often this overall string construction is exactly what you want.

But consider this shell example. You want to use ``subprocess.run``, but for
your scenario you would like to use the full power of the shell, including pipes
and subprocesses. This means you have to use ``use_shell=True``::

    from subprocess import run

    path = 'some/path/to/data'
    print(run(f'ls -ls {path} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

However, this code as written is broken on any untrusted input. In other words,
we have a shell injection attack, or from XKCD, a Bobby Tables problem::

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

`html` tag
----------

TODO: initial ``html.parse`` example

Recursive `html` construction
-----------------------------

TODO: extend with a marker class

`fl` tag - lazy interpolation of f-strings
------------------------------------------

TODO: same semantics as f-strings, but with lazy evaluation of interpolations.

`sql` tag
---------

TODO: demonstrate construction of named placeholders, along with using ``raw``

`html` tag, revisited
---------------------

TODO: compilation to a virtual DOM object, such as used in Reactive
