from __future__ import annotations
import re

from typing import *
from types import GeneratorType
from string import Template
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

from taglib import decode_raw, Thunk


def demo():
    color = "blue"
    attrs = {"style": {"font-size": "bold", "font-family": "mono"}}
    dom = html"<a {attrs} color=dark{color} >{html'<h{i}/>' for i in range(1, 4)}</a>".render(indent=2)
    print(dom)


def html(*args: str | Thunk) -> str:
    parser = HtmlNodeParser()
    for arg in decode_raw(*args):
        parser.feed(arg)
    return parser.close()


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
        self.open_node: HtmlNode | None = None
        self.starttag_interpolations: dict[str, Any] = {}
        self.data_interpolations: list = []

    def feed(self, data: str | Thunk) -> None:
        match data:
            case str():
                super().feed(data.replace("$", "$$"))
            case getvalue, _, conv, spec:
                value = _format_value(getvalue(), conv, spec)
                if self.open_node:
                    self.data_interpolations.append(value)
                    super().feed(_DATA_DELIMITER)
                else:
                    key = f"x{len(self.starttag_interpolations)}"
                    self.starttag_interpolations[key] = value
                    super().feed(f"${{{key}}}")

    def result(self) -> HtmlNode:
        root = self.root
        if len(root.children) == 1:
            return root.children[0]
        else:
            return root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = Template(tag).substitute(self.starttag_interpolations)

        attributes = {}
        for key, value in attrs:
            if value is not None:
                _disallow_interpolation(key, "use attribute expansion instead")
                attributes[key] = Template(value).substitute(
                    self.starttag_interpolations
                )
            elif (match := _TEMPLATE_PLACEHOLDER_PATTERN.match(key)) is not None:
                # A valid template placeholder should always have a corresponding interpolation
                attribute_expansion = self.starttag_interpolations[match.group(1)]
                if not isinstance(attribute_expansion, dict):
                    raise TypeError("Expected a dictionary for attribute expension")
                attributes.update(attribute_expansion)
            else:
                _disallow_interpolation(key, "use attribute expansion instead")
                attributes[key] = True

        this_node = HtmlNode(tag, attributes)
        last_node = self.stack[-1]
        last_node.children.append(this_node)
        self.stack.append(this_node)

        self.open_node = this_node

        self.starttag_interpolations.clear()

    def handle_data(self, data: str) -> None:
        assert self.open_node

        interleaved_children = []
        for dat, val in zip(
            data.split(_DATA_DELIMITER), self.data_interpolations + [""]
        ):
            interleaved_children.append(dat)
            if isinstance(val, (list, tuple, GeneratorType)):
                interleaved_children.extend(val)
            else:
                interleaved_children.append(val)

        self.open_node.children.extend(c for c in interleaved_children if c != "")
        self.data_interpolations.clear()
        self.open_node = None

    def handle_endtag(self, tag: str) -> None:
        self.open_node = None
        self.stack.pop()


# We choose this symbol because, after replacing all $ with $$, there is no way for a
# user to feed a string that would result in {$}. Thus we can reliably split an HTML
# data string on {$}.
_DATA_DELIMITER = "{$}"


# Use this to grab the name of a template placeholder (e.g. ${name})
_TEMPLATE_PLACEHOLDER_PATTERN = re.compile(r"^\${(\w[\w\d)]*)}$")


def _format_value(value: Any, conv: str, spec: str) -> Any | str:



def _disallow_interpolation(string: str, reason: str) -> None:
    try:
        Template(string).substitute()
    except KeyError:
        raise ValueError(f"Cannot interpolate {string} - {reason}")


if __name__ == "__main__":
    demo()
