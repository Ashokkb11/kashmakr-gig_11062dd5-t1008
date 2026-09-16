import pytest
import main

def test_module_smoke():
    assert hasattr(main, '__name__')
