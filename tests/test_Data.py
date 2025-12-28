# coding=utf-8
"""
Tests for Data module utility functions
"""

import os
import sys
import inspect
import datetime

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# Import only the functions we can test independently (without API dependencies)
from modules.Data import truncate, get_max_duration


class TestTruncate:
    """Tests for the truncate function"""

    def test_truncate_normal_float(self):
        """Test truncating a normal float"""
        assert truncate(1.23456789, 4) == 1.2345

    def test_truncate_rounds_down(self):
        """Test that truncate does not round up"""
        assert truncate(1.9999, 2) == 1.99

    def test_truncate_zero_decimals(self):
        """Test truncating to 0 decimal places"""
        assert truncate(3.14159, 0) == 3.0

    def test_truncate_integer(self):
        """Test truncating an integer"""
        assert truncate(42, 3) == 42.0

    def test_truncate_negative_number(self):
        """Test truncating a negative number"""
        assert truncate(-1.23456, 3) == -1.234

    def test_truncate_small_number(self):
        """Test truncating a very small number"""
        result = truncate(0.00012345, 6)
        assert result == 0.000123

    def test_truncate_scientific_notation(self):
        """Test truncating a number in scientific notation"""
        # Very small numbers may be in scientific notation
        result = truncate(1e-10, 12)
        assert result == 1e-10

    def test_truncate_pads_with_zeros(self):
        """Test that truncate pads shorter decimals"""
        assert truncate(1.5, 4) == 1.5


class TestGetMaxDuration:
    """Tests for the get_max_duration function"""

    def test_get_max_duration_empty_date(self):
        """Test with empty end_date returns empty string"""
        assert get_max_duration("", "order") == ""
        assert get_max_duration(None, "order") == ""
        assert get_max_duration(False, "order") == ""

    def test_get_max_duration_order_context(self):
        """Test get_max_duration with order context returns int"""
        # Use a date far in the future to ensure positive days
        future_date = "2030,12,31"
        result = get_max_duration(future_date, "order")
        assert isinstance(result, int)
        assert result > 0

    def test_get_max_duration_status_context(self):
        """Test get_max_duration with status context returns string"""
        future_date = "2030,12,31"
        result = get_max_duration(future_date, "status")
        assert isinstance(result, basestring)
        assert "Days Remaining" in result
