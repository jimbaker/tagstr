# September update to PEP 750

We digested all the concerns and suggestions -- whew! Based on the feedback, we're modifying the PEP in significant
ways.

Too busy to read? Here's the top-line:

- No more lazy evaluation of interpolations
- No more tag functions, no more "tag"
- Instead, a single `t` prefix which passes a `Template` to your function
- `Template.source` which has the full-string
- A normative section on how to signal the DSL to tools
- Better examples and explanations of the need

Now for more detail.

## Eager evaluation of interpolations

Our first version featured lazy evaluation of interpolations. This generated very strong pushback: it's hard for coders
to reason about, leads to surprising outcomes vs. f-strings, and challenges static analysis. The feeling: choosing "
lazy" should be opt-in, and the coder should make that choice e.g. via lambda wrapping the interpolation.

We now use eager evaluation of interpolation, storing the result on `Interpolation.value`. We still believe lazy
evaluation has a place, but will defer (hah!) that to another PEP. We also believe there are ways to keep some of the
deferred approach, which we plan to briefly outline. Finally, we envision DSLs with intermediate representations (i.e.
ASTs) which lazily-render to a string as a later step.

## Template strings

The first version followed JS by using tag functions as prefixes to f-string-like strings. For example:
`html"<div>Hello {name}</div>"`. This met serious resistance:

- Very hard to teach/discover
- No dotted names
- Namespace pollution

Our approach combined two steps into one: converting the string into a standard data structure, then running
a DSL function with that data. We now plan to split those steps: `html(t"<div>Hello {name}</div>")`. Template string ->
template function.

We now propose a single `t` prefix, as suggested in the thread. It generates a `Template` which can be stored as a
variable, passed to a callable -- all regular normal Python stuff.

## `Template` and `Interpolation`

The previous version passed a sequence of `args` to the tag function. An `arg` was either a `Decoded` or
`Interpolation`.

Instead, we will gather all the information into a `Template`:

```python
@runtime_checkable
class Template(Protocol):
    args: tuple[Decoded | Interpolation, ...]
    source: str
```

`Template` is a runtime-checkable protocol with a built-in implementation of `TemplateConcrete`. But template functions
can be called with custom classes, e.g. for testing or alternate implementations. `Template.source` has the original
text of the template string.

The other change: the `Interpolation.getvalue()` callable is replaced by `Interpolation.value`. It contains the
eagerly-evaluated interpolation result. We can thus drop the work done for annotation scopes.

## DSL typing

The discussion showed strong interest in the DSL nature of this. That is, a way to signal the language to be used in a
template string.

`Template` and `TemplateConcrete` don't contain any information about the DSL. We believe this is a good thing. But we
do plan a normative section on how another PEP might do this. In fact, we want this PEP's goal to remain focused on DSLs
and developer experience.

We plan to *suggest* (again: normative) putting the language information into type information. This makes it available
for static analysis. For example, signaling an HTML DSL:

```python
@runtime_checkable
class Template(Protocol):
    args: tuple[Decoded | Interpolation, ...]
    source: str


@runtime_checkable
class HTMLTemplate(Template):
    source: Annotated[str, Literal("html")]
    # Literal("html") might be imported from a standard library 
    # package. Or a registry. Or some other idea. Or, Annotated
    # might have multiple "flags".
```

We will try to capture some of the discussion about alternatives and variations: a registry, dialects, etc. To be very
clear though: typing is *not* required when using template strings.

## Better examples

People felt the example used was too basic and the section on Jinja didn't make the case for HTML
templating. This was intentional. We previously had long passages of explainers and removed them.

We'll add back in some material, rather than asking people to visit the separate tutorial. But we'll also provide longer
material (perhaps a video) that shows the vision.

## What we believe we addressed

To recap, here are some main points raised for which we changed the proposal.

- Too magical and hard to teach
- Lazy evaluation is cryptic
- Filling up namespaces (since no dotted names were allowed)
- Prevents future core f-string-style prefixes
- `print”Foo”` and the worry that almost anything can accidentally become a tag function

## What we believe we left for future work

We had some important discussion points that we aren't tackling directly.

First, though we're removing lazy evaluation, there were some voices that wanted to keep it. We do hope to do so. But in
a follow-on PEP.

i18n is a really important use case. In particular, choosing syntax that fits into existing workflows. It would be great
if we could consolidate templating and translation into one PEP and syntax. While we don't see a path at the moment,
it's hopeful that a future variety of template string could accomplish this.

The thread discussed variations of template strings, such as `tb` for bytes. We plan to leave that for follow-on
work.
