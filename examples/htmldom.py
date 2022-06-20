from __future__ import annotations

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
    parser = DomNodeParser()
    for arg in decode_raw(*args):
        parser.feed(arg)
    root_node = parser.dom
    if len(root_node.children) == 1:
        return root_node.children[0]
    else:
        return root_node


DomNodeChildren = list[str, "DomNode"]
DomNodeAttributes = dict[str, str | bool | dict[str, str]]


@dataclass
class DomNode:
    tag: str = field(default_factory=str)
    attributes: DomNodeAttributes = field(default_factory=dict)
    children: DomNodeChildren = field(default_factory=list)

    def render(self, *, indent: int = 0, depth: int = 0) -> str:
        tab = " " * indent * depth
        attribute_list: list[str] = []

        if (style := self.attributes.get("style")) is not None:
            if not isinstance(style, dict):
                raise TypeError("Expected style attribute to be a dictionary")
            style_string = escape("; ".join(f"{k}:{v}" for k, v in style.items()))
            attribute_list.append(f' style="{style_string}"')

        for key in set(self.attributes) - {"style"}:
            match self.attributes[key]:
                case True:
                    attribute_list.append(f" {key}")
                case False | None:
                    pass
                case value:
                    attribute_list.append(f' {key}="{escape(str(value))}"')

        children_list: list[str] = []
        for item in self.children:
            if isinstance(item, str):
                item = escape(item, quote=False)
            elif isinstance(item, DomNode):
                item = item.render(indent=indent, depth=depth + 1)
            else:
                item = str(item)
            children_list.append(item)

        if indent:
            assert indent > 0
            children_list = [f"\n{tab}{child}" for child in children_list]

        body = "".join(children_list)

        if self.tag:
            attr_body = ''.join(attribute_list)
            if body:
                stuff = f"{tab}<{self.tag}{attr_body}>{body}\n{tab}</{self.tag}>"
            else:
                stuff = f"{tab}<{self.tag}{attr_body}>{body}</{self.tag}>"
        elif self.attributes:
            raise ValueError("Untagged node cannot have children.")

        return stuff

    __str__ = render


class DomNodeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dom = DomNode()
        self.stack = [self.dom]
        self.open_node: DomNode | None = None
        self.interpolated_start_tag: dict[str, Any] = {}
        self.interpolated_data: list = []

    def feed(self, data: str | Thunk) -> None:
        match data:
            case str():
                super().feed(data.replace("$", "$$"))
            case call, _, conv, spec:
                value = _format_value(call(), conv, spec)
                if self.open_node:
                    self.interpolated_data.append(value)
                    super().feed(_DATA_SEP)
                else:
                    index = len(self.interpolated_start_tag)
                    key = f"x{index}"
                    self.interpolated_start_tag[key] = value
                    # just insert both for now because I'm feeling lazy
                    # we need to do this since there's a containment check
                    # in the case there we do attribute expansion.
                    self.interpolated_start_tag[f"${{{key}}}"] = value
                    super().feed(f"${{{key}}}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = Template(tag).substitute(self.interpolated_start_tag)

        attributes = {}
        for name, value in attrs:
            if value is None:
                if (
                    name in self.interpolated_start_tag
                ):  # this containment check is a bit of a hack
                    attributes.update(self.interpolated_start_tag[name])
                else:
                    _disallow_interpolation(name, "use attribute expansion instead")
                    attributes[name] = True
            else:
                _disallow_interpolation(name, "use attribute expansion instead")
                attributes[name] = Template(value).substitute(
                    self.interpolated_start_tag
                )

        this_node = DomNode(tag, attributes)
        last_node = self.stack[-1]
        last_node.children.append(this_node)
        self.stack.append(this_node)

        self.open_node = this_node

        self.interpolated_start_tag.clear()

    def handle_data(self, data: str) -> None:
        assert self.open_node

        interleaved_children = []
        for string, interp in zip(data.split(_DATA_SEP), self.interpolated_data + [""]):
            interleaved_children.append(string)
            if isinstance(interp, (list, tuple, GeneratorType)):
                interleaved_children.extend(interp)
            else:
                interleaved_children.append(interp)

        self.open_node.children.extend(c for c in interleaved_children if c != "")
        self.interpolated_data.clear()
        self.open_node = None

    def handle_endtag(self, tag: str) -> None:
        self.open_node = None
        self.stack.pop()


_DATA_SEP = "{$}"


def _format_value(value: Any, conv: str, spec: str) -> Any | str:
    if not conv and not spec:
        return value

    match conv:
        case "r":
            value = repr(value)
        case "s":
            value = str(value)
        case "a":
            value = ascii(value)
        case None:
            pass
        case _:
            raise ValueError(f"Bad conversion: {conv!r}")

    return format(value, spec)


def _disallow_interpolation(string: str, reason: str) -> None:
    try:
        Template(string).substitute()
    except KeyError:
        raise ValueError(f"Cannot interpolate {string} - {reason}")


if __name__ == "__main__":
    demo()
