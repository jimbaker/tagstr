Tag Strings
===========

Welcome to tag strings, a planned enhancement for Python 3.13. Here you will
find examples, specifications, and sample libraries.

About Tag Strings
-----------------

This PEP introduces tag strings for custom, repeatable string processing.
Tag strings are an extension to f-strings, with a custom function -- the "tag"
-- in place of the `f` prefix. This function can then provide rich features
such as safety checks, lazy evaluation, DSLs such as web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages. See the :doc:`work-in-progress PEP <./pep>`
for more detail.


Example
-------

In this tiny example, a ``greet`` function is defined and used to tag strings:

.. literalinclude:: ../src/tagstr/greeting.py
    :start-at: def greet
    :end-at: return f

.. testsetup::

    from tagstr.greeting import greet

With a string that obeys f-string semantics, we can then "tag" it:

.. doctest::

    >>> print(greet"Hello")
    HELLO!


.. toctree::
    :hidden:
    :maxdepth: 0
    :caption: Contents:

    Tutorial <tutorial>
    Work-In-Progress PEP <pep>
    Examples <examples/index>
