"""Test all the combinations of features in thunks."""
from tagstr import Thunk


def test_getvalue():
    def greet(*args: str | Thunk) -> str:
        return args[0][0]()
    age = 10
    result = greet"{age}"
    assert age == result
def test_raw():
    def greet(*args: str | Thunk) -> str:
        return args[0][1]
    age = 10
    result = greet"{age}"
    assert "age" == result
def test_conversion():
    def greet(*args: str | Thunk) -> str:
        return args[0][2]
    age = 10
    result = greet"{age!r}"
    assert "r" == result

def test_formatspec():
    def greet(*args: str | Thunk) -> str:
        return args[0][3]
    age = 10
    result = greet"{age:d}"
    assert "d" == result


