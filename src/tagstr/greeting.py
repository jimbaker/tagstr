"""Simplest example of tag function.

Our *customers* **EXPECT** nice greetings.
"""

from tagstr import Thunk  # Later, will be in typing


def greet(*args):
    """Uppercase and add exclamation."""
    salutation = args[0].upper()
    return f"{salutation}!"


def greet2(*args):
    """Handle an interpolation thunk."""
    salutation = args[0].strip()
    # Second arg is a "thunk" tuple for the interpolation.
    getvalue = args[1][0]
    recipient = getvalue().upper()
    return f"{salutation} {recipient}!"


def greet3(*args):
    """Handle arbitrary length of args."""
    result = []
    for arg in args:
        match arg:
            case str():  # This is a chunk...just a string
                result.append(arg)
            case getvalue, _, _, _:  # This is a thunk...an interpolation
                result.append(getvalue().upper())

    return f"{''.join(result)}!"


def greet4(*args: str | Thunk) -> str:
    """More about the thunk."""
    result = []
    for arg in args:
        match arg:
            case str():
                result.append(arg)
            case getvalue, raw, conversion, formatspec:
                gv = f"gv: {getvalue()}"
                r = f"r: {raw}"
                c = f"c: {conversion}"
                f = f"f: {formatspec}"
                result.append(", ".join([gv, r, c, f]))

    return f"{''.join(result)}!"
