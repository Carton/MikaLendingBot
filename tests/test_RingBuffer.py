"""
Tests for RingBuffer class
"""

from lendingbot.modules.RingBuffer import RingBuffer


def test_ringbuffer_init() -> None:
    """Test RingBuffer initialization"""
    rb = RingBuffer(5)
    assert rb.size == 5
    assert rb.get() == []


def test_ringbuffer_append_below_capacity() -> None:
    """Test appending items when below capacity"""
    rb = RingBuffer(5)
    rb.append(1)
    rb.append(2)
    rb.append(3)
    assert rb.get() == [1, 2, 3]


def test_ringbuffer_append_at_capacity() -> None:
    """Test appending items when at capacity"""
    rb = RingBuffer(5)
    for i in range(5):
        rb.append(i)
    assert rb.get() == [0, 1, 2, 3, 4]


def test_ringbuffer_append_over_capacity() -> None:
    """Test that oldest items are removed when over capacity"""
    rb = RingBuffer(5)
    for i in range(9):
        rb.append(i)
    # Should contain [4, 5, 6, 7, 8] - last 5 items
    assert rb.get() == [4, 5, 6, 7, 8]


def test_ringbuffer_single_element() -> None:
    """Test RingBuffer with size 1"""
    rb = RingBuffer(1)
    rb.append("a")
    assert rb.get() == ["a"]
    rb.append("b")
    assert rb.get() == ["b"]
    rb.append("c")
    assert rb.get() == ["c"]


def test_ringbuffer_preserves_order() -> None:
    """Test that items are returned in insertion order"""
    rb = RingBuffer(10)
    items = ["first", "second", "third", "fourth", "fifth"]
    for item in items:
        rb.append(item)
    assert rb.get() == items


def test_ringbuffer_with_different_types() -> None:
    """Test RingBuffer with different data types"""
    rb = RingBuffer(3)
    rb.append(42)
    rb.append("string")
    rb.append({"key": "value"})
    result = rb.get()
    assert result[0] == 42
    assert result[1] == "string"
    assert result[2] == {"key": "value"}
