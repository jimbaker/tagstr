# Tag strings

This PEP introduces tag strings for custom, repeatable string processing. Tag strings
are an extension to f-strings, with a custom function -- the "tag" -- in place of the
`f` prefix. This function can then provide rich features such as safety checks, lazy
evaluation, domain specific languages (DSLs) for web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages.

## More info

- [Implementation (WIP) based on 3.14](https://github.com/lysnikolaou/cpython/tree/tag-strings-rebased)
- [Documentation site](https://pauleveritt.github.io/tagstr-site/) including:
  - An [HTML templating tutorial](https://pauleveritt.github.io/tagstr-site/htmlbuilder.html)
  - Docker instructions for [prebuilt image](https://hub.docker.com/r/koxudaxi/python)
  - Support for devcontainer checkout

## Related Work

- [Flufl i18n substitutions](https://flufli18n.readthedocs.io/en/stable/using.html#substitutions-and-placeholders)
- [Tagged library](https://github.com/jviide/tagged)
- [PEP 501: Interpolation templates](https://peps.python.org/pep-0501/)
- [Earlier work by the same authors](https://github.com/jimbaker/fl-string-pep)
