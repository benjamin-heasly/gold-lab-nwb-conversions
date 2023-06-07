from pyramid.__about__ import __version__
from pyramid.hello import hello

def test_hello():
    word = hello()
    assert word == "hello"

def test_version():
    assert __version__ == "0.0.1"