from typing import *


# TODO: thunks likely should have a "tuple-like object with named attributes"
# (so namedtuples) as seen in the os module. This will enable future expansion.
# Of course such named attribute support can also be done in the future!

Thunk = tuple[
    Callable[[], Any],  # getvalue
    str,  # raw
    str | None,  # conv
    str | None,  # formatspec
]


def decode_raw(*args: str | Thunk) -> Generator[str | Thunk, None, None]:
    # To bytes, then decoded back as a string, applying amy escapes, while
    # maintaining the underlying Unicode codepoints. There may be a better way,
    # but this conversion uses the same internal code path as Python's parser.
    for arg in args:
        if isinstance(arg, str):
            yield arg.encode('utf-8').decode('unicode-escape')
        else:
            yield arg


def format_value(arg: str | Thunk) -> str:
    match arg:
        case str():
            return arg
        case getvalue, _, conv, spec:
            value = getvalue()
            match conv:
                case 'r': value = repr(value)
                case 's': value = str(value)
                case 'a': value = ascii(value)
                case None: pass
                case _: raise ValueError(f'Bad conversion: {conv!r}')
            return format(value, spec if spec is not None else '')
