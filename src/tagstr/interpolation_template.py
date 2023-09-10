from dataclasses import dataclass
from typing import Any

from taglib import decode_raw, Thunk


@dataclass
class InterpolationTemplate:
    raw_template: str
    parsed_template: tuple[tuple[str, str | None], ...]
    field_values: tuple[Any, ...]
    format_specifiers: tuple[str, ...]

    # optionally implement __str__ per https://peps.python.org/pep-0501/#interoperability-with-str-only-interfaces

    def __format__(self, format_specifier):
        # When formatted, render to a string, and use string formatting
        return format(self.render(), format_specifier)

    def render(self, *, render_template=''.join, render_field=format):
        iter_fields = enumerate(self.parsed_template)
        values = self.field_values
        specifiers = self.format_specifiers
        template_parts = []
        for field_pos, (leading_text, field_expr) in iter_fields:
            template_parts.append(leading_text)
            if field_expr is not None:
                value = values[field_pos]
                specifier = specifiers[field_pos]
                rendered_field = render_field(value, specifier)
                template_parts.append(rendered_field)
        return render_template(template_parts)


def i(*args: str | Thunk) -> InterpolationTemplate:
    raw_template = []
    parsed_template = []
    last_str_arg = ''
    field_values = []
    format_specifiers = []
    for arg, raw_arg in zip(decode_raw(*args), args):
        match arg:
            case str():
                raw_template.append(raw_arg)
                last_str_arg = arg
            case getvalue, raw, conv, format_spec:
                value = getvalue()
                raw_template.append(f"{{{raw}{'!' + conv if conv else ''}{':' + format_spec if format_spec else ''}}}")
                parsed_template.append((last_str_arg, raw))
                field_values.append(value)
                format_specifiers.append('' if format_spec is None else format_spec)
                last_str_arg = ''
    if last_str_arg:
        parsed_template.append((last_str_arg, None))

    return InterpolationTemplate(
        ''.join(raw_template),
        tuple(parsed_template),
        tuple(field_values),
        tuple(format_specifiers)
    )


def demo():
    from unittest.mock import MagicMock

    def reprformat(template):
        def render_field(value, specifier):
            return format(repr(value), specifier)
        return template.render(render_field=render_field)

    names = ["Alice", "Bob"]
    def expressions():
        return 6 * 7

    t1 = i"Substitute {names} and {expressions()} at runtime"
    print(t1)
    print(t1.render())
    print(reprformat(t1))

    response = MagicMock()
    t2 = i"<html><body>{response.body}</body></html>"
    print(t2)
    print(t2.render())

    detailed = "some detail"
    debugging = "some debugging"
    info = "some info"
    t3 = i"Message with {detailed!r:^20} {debugging!a} {info!s}"
    print(t3)
    print(t3.render())

    bar=10
    def foo(data):
        return data + 20

    t4 = i'input={bar}, output={foo(bar)}'
    print(t4)
    print(t4.render())

    # re https://peps.python.org/pep-0501/#possible-integration-with-the-logging-module
    # implementation of the logging module delayed evaluation in PEP 501 requires an expression parser...
    # outside the scope of what I'm demoing today


if __name__ == '__main__':
    demo()
