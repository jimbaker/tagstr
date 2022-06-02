# Codegens functions to build DOMs for html tag string implementations
#
# It should (eventually) be suitable for use with such packages as the following:
# * https://github.com/nteract/vdom
# * https://github.com/idom-team/idom
# * https://github.com/pauleveritt/viewdom

from __future__ import annotations

import re
from functools import cache
from html.parser import HTMLParser
from types import CodeType
from typing import *

from taglib import decode_raw, Thunk


ENDS_WITH_WHITESPACE_RE = re.compile(r'\s+$')
ENDS_WITH_ATTRIBUTE_KEY_RE = re.compile(r'\s+(\S+)\=$')


class DomCodeGenerator(HTMLParser):
    """Given HTML input with interpolations, generates code to build an equivalent DOM"""
    def __init__(self):
        self.lines = ['def compiled(vdom, /, *args):', '  return \\']
        self.tag_interpolations = []
        self.tag_stack = []
        super().__init__()

    def indent(self) -> str:
        return '  ' * (len(self.tag_stack) + 2)

    @property
    def code(self) -> str:
        return '\n'.join(self.lines)

    def handle_starttag(self, tag, attrs):
        attrs_code = [f'{dict(attrs)!r}']
        attrs_code.extend(self.tag_interpolations)
        self.tag_interpolations = []
        self.lines.append(f"{self.indent()}vdom('{tag}', {'|'.join(attrs_code)}, [")
        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        if tag != self.tag_stack[-1]:
            raise RuntimeError(f'unexpected </{tag}>')
        self.tag_stack.pop()
        self.lines.append(f'{self.indent()}]){"," if self.tag_stack else ""}')

    def handle_data(self, data: str):
        # At the very least the first empty line needs to be removed, as might
        # be seen in
        # html"""
        #   <tag>...</tag>
        # """
        # (given that our codegen is so rudimentary!)

        # Arguably other blank strings should be removed as well, and this
        # stripping results in having output equivalent to standard vdom
        # construction.
        if not data.strip():
            return
        self.lines.append(f'{self.indent()}{data!r},')

    def add_interpolation(self, i: int):
        # There are five possible locations for interpolations, but not all
        # should be necessarily supported:

        # 1. In the data for some tag: <tag ...>...{interpolation}...</tag>
        # 2. In the tag, splatted in: <tag {interpolation} ...>
        # 3. In the tag, as the value: <tag key={interpolation} ...>
        # 4. In the tag, as the key or as part of it <tag {interpolation}=value ...>
        # 5. In the tag name itself: <tag{intepolation}... ...>. Such
        #    functionality also requires it being balanced in the end tag with a
        #    matching interpolation. At best, this seems tricky.
        #
        # Of these, let's at least support #1, #2, #3, given that it's unclear
        # if #4, #5 are used in practice (or expectation that they would be
        # supported - this listing is just an opportunity to be exhaustive).

        # The convention used here in the codegen is that the code
        # `args[{i}][0]()` implements the following logic:
        #
        #    Call getvalue for the thunk at the i-th position in args.
        #
        # This interpolation could optionally also process formatspec and
        # conversion, if specified.
        print(f'raw data seen in the interpolation: {i=} {self.rawdata!r}')

        # At this point when we get this method called, if is processing a start
        # tag, self.rawdata will have that tag as it is being fed into the
        # parser - up to the point of the interpolation. Let's use this state
        # accordingly to implement the "in the tag" support.

        # 1. We are in data, not in a tag. We can just add the code to do the
        #    interpolation:
        if not self.rawdata:
            self.lines.append(f'{self.indent()}args[{i}][0](), ')

        # 2. Splatted mapping, combine with the attributes:
        elif ENDS_WITH_WHITESPACE_RE.search(self.rawdata):
            # if we are being careful, we keep track of what we are applying so
            # first one wins. Let's ignore for now. Also it's probably a good
            # idea to have a wrapper on any possible TypeError raised if we are
            # not splatting in a mapping, just to make it easier for usage.
            # Ignore that too.
            self.tag_interpolations.append(f'args[{i}][0]()')

        # 3. We have an attribute value interpolation. We need to get what is to
        #    its left, which is the key. Note that we don't currently support
        #    quoting the interpolation, since this adds even more fun to the
        #    logic (we would then have to track that extra state).
        elif m := ENDS_WITH_ATTRIBUTE_KEY_RE.search(self.rawdata):
            self.tag_interpolations.append(f'{{{m.group(1)!r}: args[{i}][0]()}}')


@cache
def make_compiled_template(*args: str | CodeType) -> Callable:
    print(f'Making compiled template {hash(args)}...')
    builder = DomCodeGenerator()
    for i, arg in enumerate(decode_raw(*args)):
        match arg:
            case str():
                builder.feed(arg)
            case _:
                builder.add_interpolation(i)
    print("Code:\n", builder.code)
    code_obj = compile(builder.code, '<string>', 'exec')
    captured = {}
    exec(code_obj, captured)
    return captured['compiled']


# The "lambda wrapper" function objects will change at each usage of the call
# site. Let's use the underlying code object instead as part of the key to
# construct the compiled function so it can be memoized. This approach is
# correct, since we will call getvalue in the thunk in the interpolation.

def immutable_bits(*args: str | Thunk) -> Tuple(str | CodeType):
    bits = []
    for arg in args:
        if isinstance(arg, str):
            bits.append(arg)
        else:
            bits.append((arg[0].__code__,))
    return tuple(bits)


# Makes 'tag' functions to be used like so: html"<body>blah</body>"
# It needs to be specialized for a specific DOM implementation.

def make_html_tag(f: Callable) -> Callable:
    def html_tag(*args: str | Thunk) -> Any:
        compiled = make_compiled_template(*immutable_bits(*args))
        return compiled(f, *args)
    return html_tag


def useit():
    # Example usage to adapt. Subset of functionality in IDOM's vdom constructor
    def vdom(tagName: str, attributes: Dict | None, children: List | None) -> Dict:
        d = {'tagName': tagName}
        if attributes:
            d['attributes'] = attributes
        if children:
            d['children'] = children
        return d
    html = make_html_tag(vdom)

    some_attrs = {'a': 6, 'b': 7}
    for i in range(3):
        for j in range(3):
            node = html'<body {some_attrs} attr1={i}><div{j}>\N{{GRINNING FACE}}: {i} along with {j}</div{j}></body>'
            print(node)

    def Todo(prefix, label):
        return html'<li>{prefix}: {label}</li>'

    def TodoList(prefix, todos):
        return html'<ul>{[Todo(prefix, label) for label in todos]}</ul>'

    b = html"""<html>
        <body attr=blah" yo={1}>
            {TodoList('High', ['Get milk', 'Change tires'])}
        </body>
    </html>
    """
    print(b)


if __name__ == '__main__':
    useit()
