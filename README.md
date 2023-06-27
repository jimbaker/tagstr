# Tag strings

An early stage PEP that introduces tag strings - a natural extension of "f-strings" from [PEP 498](https://peps.python.org/pep-0498/) which enables Python developers to create and use their own custom tags (or prefixes) when working with string literals and any interpolation. Tag strings are based on a related idea in JavaScript, [tagged template literals](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates) but with a Pythonic syntax for both the use of and the definition of tags.

# Install

```shell
$ path/to/venv/bin/pip install -e .
```

# Documents

- [WIP PEP](https://github.com/jimbaker/tagstr/blob/main/docs/pep.rst)
- [Tutorial](https://github.com/jimbaker/tagstr/blob/main/docs/tutorial.rst)
- [Implementation (WIP)](https://github.com/gvanrossum/cpython/tree/tag-strings)

# Examples

- [Shell](https://github.com/jimbaker/tagstr/blob/main/src/tagstr/shell.py)
- [SQL](https://github.com/jimbaker/tagstr/blob/main/src/tagstr/sql.py)
- [HTML](https://github.com/jimbaker/tagstr/blob/main/src/tagstr/htmldom.py)
- [Among others...](https://github.com/jimbaker/tagstr/blob/main/src/tagstr)

# Related Work

- [Flufl i18n substitutions](https://flufli18n.readthedocs.io/en/stable/using.html#substitutions-and-placeholders)
- [Tagged library](https://github.com/jviide/tagged)
- [PEP 501: Interpolation templates](https://peps.python.org/pep-0501/)
- [Earlier work by the same authors](https://github.com/jimbaker/fl-string-pep)
