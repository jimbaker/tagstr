from __future__ import annotations

from typing import *
from types import GeneratorType
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

from taglib import decode_raw, Thunk, format_value


def demo():
    color = "blue"
    attrs = {"style": {"font-size": "bold", "font-family": "mono"}}
    dom = html"<a {attrs} color=dark{color} >{html'<h{i}/>' for i in range(1, 4)}</a>".render(indent=2)
    print(dom)


def html(*args: str | Thunk) -> str:
    parser = HtmlNodeParser()
    for arg in decode_raw(*args):
        parser.feed(arg)
    return parser.result()


HtmlChildren = list[str, "HtmlNode"]
HtmlAttributes = dict[str, str | bool | dict[str, str]]


@dataclass
class HtmlNode:
    tag: str = field(default_factory=str)
    attributes: HtmlAttributes = field(default_factory=dict)
    children: HtmlChildren = field(default_factory=list)

    def render(self, *, indent: int = 0, depth: int = 0) -> str:
        tab = " " * indent * depth

        attribute_list: list[str] = []
        for key, value in self.attributes.items():
            match key, value:
                case _, True:
                    attribute_list.append(f" {key}")
                case _, False | None:
                    pass
                case "style", style:
                    if not isinstance(style, dict):
                        raise TypeError("Expected style attribute to be a dictionary")
                    css_string = escape("; ".join(f"{k}:{v}" for k, v in style.items()))
                    attribute_list.append(f' style="{css_string}"')
                case _:
                    attribute_list.append(f' {key}="{escape(str(value))}"')

        children_list: list[str] = []
        for item in self.children:
            match item:
                case str():
                    item = escape(item, quote=False)
                case HtmlNode():
                    item = item.render(indent=indent, depth=depth + 1)
                case _:
                    item = str(item)
            children_list.append(item)

        if indent:
            assert indent > 0
            children_list = [f"\n{tab}{child}" for child in children_list]

        body = "".join(children_list)

        if not self.tag:
            if self.attributes:
                raise ValueError("Untagged node cannot have attributes.")
            result = body
        else:
            attr_body = "".join(attribute_list)
            if body:
                result = f"{tab}<{self.tag}{attr_body}>{body}\n{tab}</{self.tag}>"
            else:
                result = f"{tab}<{self.tag}{attr_body}>{body}</{self.tag}>"

        return result

    __str__ = render


class HtmlNodeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = HtmlNode()
        self.stack = [self.root]
        self.values: list[Any] = []

    def feed(self, data: str | Thunk) -> None:
        match data:
            case str():
                super().feed(escape_placeholder(data))
            case getvalue, _, conv, spec:
                value = getvalue()
                self.values.append(
                    format_value(value, conv, spec) if (conv or spec) else value
                )
                super().feed(PLACEHOLDER)

    def result(self) -> HtmlNode:
        root = self.root
        self.close()
        if (len_root_children := len(root.children)) == 0:
            raise ValueError("Nothing to return")
        elif len_root_children == 1:
            return root.children[0]
        else:
            return root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag, self.values = join_with_values(tag, self.values)

        node_attrs = {}
        for k, v in attrs:
            if v is not None:
                _disallow_interpolation(k, "use attribute expansion instead")
                node_attrs[k], self.values = join_with_values(v, self.values)
            elif k == PLACEHOLDER:
                attribute_expansion, *self.values = self.values
                if not isinstance(attribute_expansion, dict):
                    raise TypeError("Expected a dictionary for attribute expension")
                node_attrs.update(attribute_expansion)
            else:
                _disallow_interpolation(k, "use attribute expansion instead")
                node_attrs[k] = True
        assert not self.values, "Did not interpolate all values"

        this_node = HtmlNode(tag, node_attrs)
        last_node = self.stack[-1]
        last_node.children.append(this_node)
        self.stack.append(this_node)

    def handle_data(self, data: str) -> None:
        interleaved_children, self.values = interleave_with_values(data, self.values)
        assert not self.values, "Did not interpolate all values"

        children = self.stack[-1].children = []
        for child in interleaved_children:
            match child:
                case list() | tuple() | GeneratorType():
                    children.extend(child)
                case "":
                    pass
                case _:
                    children.append(child)

    def handle_endtag(self, tag: str) -> None:
        self.stack.pop()


# We choose this symbol because, after replacing all $ with $$, there is no way for a
# user to feed a string that would result in {$}. Thus we can reliably split an HTML
# data string on {$}.
PLACEHOLDER = "{$}"


def escape_placeholder(string: str) -> str:
    return string.replace("$", "$$")


def unescape_placeholder(string: str) -> str:
    return string.replace("$$", "$")


def join_with_values(string, values) -> tuple[str, list[Any]]:
    interleaved_values, remaining_values = interleave_with_values(string, values)
    return "".join(map(str, interleaved_values)), remaining_values


def interleave_with_values(string, values) -> tuple[list[str | Any], list[Any]]:
    string_parts = string.split(PLACEHOLDER)
    remaining_values = values[len(string_parts) - 1 :]

    interleaved_values: list[str] = []
    for s, v in zip(string_parts[:-1], values):
        interleaved_values.append(unescape_placeholder(s))
        interleaved_values.append(v)
    interleaved_values.append(string_parts[-1])

    return interleaved_values, remaining_values


def _disallow_interpolation(string: str, reason: str) -> None:
    if PLACEHOLDER in string:
        raise ValueError(f"Cannot interpolate {string} - {reason}")


if __name__ == "__main__":
    demo()
