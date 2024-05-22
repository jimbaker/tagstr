# Tag strings

This PEP introduces tag strings for custom, repeatable string processing. Tag strings
are an extension to f-strings, with a custom function -- the "tag" -- in place of the
`f` prefix. This function can then provide rich features such as safety checks, lazy
evaluation, domain specific languages (DSLs) for web templating, and more.

Tag strings are similar to `JavaScript tagged templates <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals#tagged_templates>`_
and similar ideas in other languages.

## Examples repo

To keep the conversation here focused on the PEP, we moved supporting material to 
[a companion repo](https://github.com/pauleveritt/tagstr-site). There you can find 
resources such as:

- JupyterLite playground for tag strings
- Docker builds
- Long-form tutorials
- Example code

## Related Work

- [Flufl i18n substitutions](https://flufli18n.readthedocs.io/en/stable/using.html#substitutions-and-placeholders)
- [Tagged library](https://github.com/jviide/tagged)
- [PEP 501: Interpolation templates](https://peps.python.org/pep-0501/)
- [Earlier work by the same authors](https://github.com/jimbaker/fl-string-pep)
