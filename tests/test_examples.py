"""Test variations of each example.

Each test case is a function in an example. These test case functions 
can return either an expected/actual tuple or a sequence of these.
"""

from tagstr.greeting import greet, greet2, greet3, greet4


def test_greeting():
    result = greet"Hello"
    assert "HELLO!" == result

def test_greeting2():
    name = "World"
    result = greet2"Hello {name}"
    assert "Hello WORLD!" == result

def test_greeting3():
    name = "World"
    result = greet3"Hello {name:s} nice to meet you"
    assert "Hello WORLD nice to meet you!" == result

def test_greeting4():
    name = "World"
    result = greet4"Hello {name!r:s}"
    expected = "Hello gv: World, r: name, c: r, f: s!"
    assert expected == result

