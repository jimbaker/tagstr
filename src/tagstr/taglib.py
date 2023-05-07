from typing import Generator

from tagstr import Thunk


def decode_raw(*args: str | Thunk) -> Generator[str | Thunk, None, None]:
    """Convert string to bytes then, applying decoding escapes.

    Maintain underlying Unicode codepoints. Uses the same internal code
    path as Python's parser.
    """
    for arg in args:
        if isinstance(arg, str):
            yield arg.encode("utf-8").decode("unicode-escape")
        else:
            yield arg


def format_value(arg: str | Thunk) -> str:
    match arg:
        case str():
            return arg
        case getvalue, _, conv, spec:
            value = getvalue()
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
            return format(value, spec if spec is not None else "")
