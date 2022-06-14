# Don't name this file html.py!

from __future__ import annotations

from typing import *
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser

from taglib import decode_raw, Thunk

AttrsDict = dict[str, str]
BodyList = list["str | HTMLNode"]


@dataclass
class HTMLNode:
    tag: str|None
    attrs: AttrsDict
    body: BodyList

    def __init__(
        self,
        tag: str|None = None,
        attrs: AttrsDict|None = None,
        body: BodyList |None = None,
    ):
        self.tag = tag
        self.attrs = {}
        if attrs:
            self.attrs.update(attrs)
        self.body = []
        if body:
            self.body.extend(body)
    
    def __str__(self):
        attrlist = []
        for key, value in self.attrs.items():
            attrlist.append(f' {key}="{escape(str(value))}"')
        bodylist = []
        for item in self.body:
            if isinstance(item, str):
                item = escape(item, quote=False)
            else:
                item = str(item)
            bodylist.append(item)
        stuff = "".join(bodylist)
        if self.tag:
            stuff =  f"<{self.tag}{''.join(attrlist)}>{stuff}</{self.tag}>"
        return stuff


class HTMLBuilder(HTMLParser):
    def __init__(self):
        self.stack = [HTMLNode()]
        super().__init__()

    def handle_starttag(self, tag, attrs):
        node = HTMLNode(tag, attrs)
        self.stack[-1].body.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        if tag != self.stack[-1].tag:
            raise RuntimeError(f"unexpected </{tag}>")
        self.stack.pop()

    def handle_data(self, data: str):
        self.stack[-1].body.append(data)        

# This is the actual 'tag' function: html"<body>blah</body>""
def html(*args: str | Thunk) -> HTMLNode:
    builder = HTMLBuilder()
    for arg in decode_raw(*args):
        match arg:
            case str():
                builder.feed(arg)
            case getvalue, raw, conv, spec:
                value = getvalue()
                match conv:
                    case 'r': value = repr(value)
                    case 's': value = str(value)
                    case 'a': value = ascii(value)
                    case None: pass
                    case _: raise ValueError(f"Bad conversion: {conv!r}")
                # see https://github.com/jimbaker/tagstr/issues/3#issuecomment-1154010616
                # spec should default to '' to avoid this step  
                if spec is not None:
                    value = format(value, spec)
                match value:
                    case HTMLNode():
                        builder.feed(str(value))
                    case list():
                        for item in value:
                            if isinstance(item, HTMLNode):
                                builder.feed(str(item))
                            else:
                                builder.feed(escape(str(item)))
                    case _:
                        builder.feed(escape(str(value)))
    root = builder.stack[0]
    if not root.tag and not root.attrs:
        stuff = root.body[:]
        while stuff and isinstance(stuff[0], str) and stuff[0].isspace():
            del stuff[0]
        while stuff and isinstance(stuff[-1], str) and stuff[-1].isspace():
            del stuff[-1]
        if len(stuff) == 1:
            return stuff[0]
        return stuff
    return root


def demo():
    x = HTMLNode("foo", {"x": 1, "y": "2"}, ["hohoho"])

    a = html"""
    <html>
        <body>
            foo
            {x}
            bar
            {x!s}
            baz
            {x!r}
        </body>
    </html>
    """
    print(a)

    print()

    s = '"'
    b = html"""
    <html>
        <body attr=blah" yo={1}>
            {[html"<div class=c{i}>haha{i}</div> " for i in range(3)]}
        </body>
    </html>
    """
    print(b)


if __name__ == '__main__':
    demo()
