PEP: 999
Title: Tag Strings: Tutorial

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
Let's take a look first at a simple example with f-strings:

.. code-block::
    name = 'Jim'
    s = f"Hello, {name}, it's great to meet you!"

This is the equivalent of writing

.. code-block::
    name = 'Jim'
    s = 'Hello, ' + format(name, '') + ", it's great to meet you!"
    
    # or equivalently
    
    s = ''.join(['Hello, ', format(name, ''), ", it's great to meet you!"])

Here we see that the f-string syntax has a compact syntax for combining into one
string a sequence of strings -- ``'Hello, '`` and ``", it's great to meet

you!"`` -- with interpolations of values, which are formatted into strings.
Often this overall string construction is exactly what you want.

But consider this shell example. You want to use ``subprocess.run``, but for
your scenario you would like to use the full power of the shell (so you need to
have the keyword arg ``use_shell=True``):

.. code-block::
    import subprocess

    path = 'some/path/to/data'
    print(subprocess.run('ls -ls {path} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

This code is broken on any untrusted input. In other words, we have a shell
injection attack, or from XKCD, a Bobby Tables problem:

.. code-block::
    import subprocess

    path = 'foo; cat /etc/passwd'
    print(subprocess.run('ls -ls {path} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

There's a straightforward fix. You just need to quote the interpolation of
``path`` with ``shlex.quote``:

.. code-block::
    import shlex
    import subprocess

    path = 'foo; cat /etc/passwd'
    print(subprocess.run('ls -ls {shlex.quote(path)} | (echo "First 5 results from ls:"; head -5)', use_shell=True))

For the first example, you can write a ``sh`` tag that automatically does this
interpolation for the user.

.. code-block::
    path = 'foo; cat /etc/passwd'
    print(subprocess.run(sh'ls -ls {path}', use_shell=True))

Fundamentally tag strings are a straightforward generalization of f-strings:

- f-strings are a sequence of strings (possibly raw, with ``fr``) and
  interpolations (including format specification and conversions, such as ``!r``
  for ``repr``); when evaluated, they result in a string
- tag strings are a sequence of **raw** strings and **thunks**, which generalize
  such interpolations; and result in **any value**

This then gives us the following generic signature for a **tag function**,
``some_tag``:

.. code-block::
    Thunk = tuple[
        Callable[[], Any],  # getvalue
        str,  # raw
        str | None,  # conv
        str | None,  # formatspec
    ]

    def some_tag(*args: str | Thunk) -> Any

Let's now write a first pass of this tag function, ``sh``:

.. code-block::
    def sh(*args: str | Thunk) -> str:
        command = []
        for arg in args:
            match arg:
                case str():
                    command.append(arg)
                case getvalue, _, _, _:
                    command.append(shlex.quote(str(getvalue()))
        return ''.join(command)

Let's go through this code: for each arg, either it's a string (the static
part), or an interpolation (the dynamic part).

If it's the static part, it's code the tag user wrote to work with the shell.
That shell code can be considered to be safe (not necessarily correct!). Note
that for tag strings, this will always be a raw string. This is convenient for
working with the shell - we might want to use regexes in ``grep`` or similar
tools like the Silver Surfer (``ag``).

If it's the dynamic part, this part is a ``Thunk``. A tag string ``Thunk`` is a
tuple of a function (``getvalue``, takes no arguments, per the above type
signature), along with other elements that we will discuss in a moment. So this
means we can just do the following:

1. Call ``getvalue``
2. Quote its result with ``shlex.quote``
3. Interpolate, in this case by adding it to the ``command`` list in the above code

This evaluation of the tag string then results in some arbitrary value -- in
this case a ``str`` -- which can then be used by some API. Note that it is a
best practice for the evaluation of the tag string to not have any side effect.
