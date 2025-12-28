# coding=utf-8
"""
Tests for RingBuffer class
"""
import os
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from modules.RingBuffer import RingBuffer


def test_ringbuffer_init():
    """Test RingBuffer initialization"""
    rb = RingBuffer(5)
    assert rb.size == 5
    assert rb.get() == []


def test_ringbuffer_append_below_capacity():
    """Test appending items when below capacity"""
    rb = RingBuffer(5)
    rb.append(1)
    rb.append(2)
    rb.append(3)
    assert rb.get() == [1, 2, 3]


def test_ringbuffer_append_at_capacity():
    """Test appending items when at capacity"""
    rb = RingBuffer(5)
    for i in range(5):
        rb.append(i)
    assert rb.get() == [0, 1, 2, 3, 4]


def test_ringbuffer_append_over_capacity():
    """Test that oldest items are removed when over capacity"""
    rb = RingBuffer(5)
    for i in range(9):
        rb.append(i)
    # Should contain [4, 5, 6, 7, 8] - last 5 items
    assert rb.get() == [4, 5, 6, 7, 8]


def test_ringbuffer_single_element():
    """Test RingBuffer with size 1"""
    rb = RingBuffer(1)
    rb.append('a')
    assert rb.get() == ['a']
    rb.append('b')
    assert rb.get() == ['b']
    rb.append('c')
    assert rb.get() == ['c']


def test_ringbuffer_preserves_order():
    """Test that items are returned in insertion order"""
    rb = RingBuffer(10)
    items = ['first', 'second', 'third', 'fourth', 'fifth']
    for item in items:
        rb.append(item)
    assert rb.get() == items


def test_ringbuffer_with_different_types():
    """Test RingBuffer with different data types"""
    rb = RingBuffer(3)
    rb.append(42)
    rb.append('string')
    rb.append({'key': 'value'})
    result = rb.get()
    assert result[0] == 42
    assert result[1] == 'string'
    assert result[2] == {'key': 'value'}
