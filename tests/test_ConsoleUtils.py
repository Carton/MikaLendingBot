"""
Tests for ConsoleUtils
"""

from lendingbot.modules import ConsoleUtils


def test_get_terminal_size() -> None:
    """Test get_terminal_size returns a tuple of two integers"""
    size = ConsoleUtils.get_terminal_size()
    assert isinstance(size, tuple)
    assert len(size) == 2
    assert isinstance(size[0], int)
    assert isinstance(size[1], int)
    assert size[0] > 0
    assert size[1] > 0
