"""Code likely to be included in CPython itself."""

from typing import Any, Callable, NamedTuple


class Thunk(NamedTuple):
    getvalue: Callable[[], Any]
    raw: str
    conv: str | None
    formatspec: str | None
