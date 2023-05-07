# fl tag implementation - lazy version of f-string eval

from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from typing import *

from tagstr.taglib import decode_raw, format_value
from tagstr import Thunk


def just_like_f_string(*args: str | Thunk) -> str:
    return ''.join((format_value(arg) for arg in decode_raw(*args)))


@dataclass
class LazyFString:
    args: Sequence[str | Thunk]

    def __str__(self) -> str:
        return self.value

    @cached_property
    def value(self) -> str:
        return just_like_f_string(*self.args)


def fl(*args: str | Thunk) -> LazyFString:
    return LazyFString(args)


def demo():
    import logging
    import random
    from functools import wraps

    a = 47
    b = 'foo'
    c = 'baz\nbar\n'
    text = 'some text here'

    # The following loop results in this logged to stdin, with values 0 to 4 for the iteration:
    # WARNING:root:0: a=47, b='foo', c='baz\nbar\n', some text here
    # WARNING:root:1: a=47, b='foo', c='baz\nbar\n', some text here
    # ...
    # WARNING:root:4: a=47, b='foo', c='baz\nbar\n', some text here
    for i in range(5):
        logging.warning(fl'{i}: {a=}, {b=}, {c=}, {text}')

    # Note that the use of the tag returns a LazyFString, which in turn memoizes its string value with
    # cached_propery. So using the same LazyFString object repeatedly doesn't change its stringification,
    # even if the expression(s) it depends on could change.
    for i in range(5):
        s = fl'{i}: {a=}, {b=}, {c=}, {random.randint(0, 100)=}'
        logging.warning(s)
        logging.error(s)
    # Note: this might look more interesting with multiple logging handlers, but that requires setup.

    # By default with logging with our simplistic setup, logging.info and below levels are not logged.
    # Verify that LazyFString objects are never called with __str__ unless actually used by logging.
    # See LogRecord.getMessage (https://github.com/python/cpython/blob/main/Lib/logging/__init__.py)
    def report_called(f):
        @wraps(f)
        def wrapper(*args, **kwds):
            print('Calling wrapped function', f)
            return f(*args, **kwds)
        return wrapper

    @report_called
    def expensive_fn():
        return 42  # ultimate answer takes some time to compute! :)

    logging.info(fl'{expensive_fn()}')     # nothing logged, report_called/expensive_fn is not called
    logging.warning(fl'{expensive_fn()}')  # but this is


if __name__ == '__main__':
    demo()
