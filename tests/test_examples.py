"""Test variations of each example.

Each test case is a function in an example. These test case functions 
can return either an expected/actual tuple or a sequence of these.
"""

from tagstr.greeting import greet, greet2, greet3, greet4, greet5


def test_greeting():
    assert greet"Hello" == "Hello!"  # Use the custom "tag" on the string

def test_greeting2():
    name = "World"
    assert greet2"Hello {name}" == "Hello WORLD!"

def test_greeting3():
    name = "World"
    result = greet3"Hello {name:s} nice to meet you"
    assert result == "Hello WORLD nice to meet you!"

def test_greeting4():
    name = "World"
    assert greet4"Hello {name}" == "Hello WORLD!"

def test_greeting5():
    name = "World"
    assert greet5"Hello {name!r:s}" == "Hello gv: World, r: name, c: r, f: s!"

