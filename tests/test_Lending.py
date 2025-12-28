# coding=utf-8
"""
Tests for Lending module utility functions
"""
import os
import sys
import inspect
from decimal import Decimal

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# Import only the pure functions we can test independently
from modules.Lending import parse_xday_threshold


class TestParseXdayThreshold:
    """Tests for the parse_xday_threshold function"""

    def test_parse_empty_threshold(self):
        """Test parsing empty threshold returns empty lists"""
        rates, xdays = parse_xday_threshold('')
        assert rates == []
        assert xdays == []

    def test_parse_none_threshold(self):
        """Test parsing None threshold returns empty lists"""
        rates, xdays = parse_xday_threshold(None)
        assert rates == []
        assert xdays == []

    def test_parse_single_pair(self):
        """Test parsing a single rate:days pair"""
        rates, xdays = parse_xday_threshold('0.050:25')
        assert len(rates) == 1
        assert len(xdays) == 1
        # Rate should be converted from percentage (0.050 -> 0.00050)
        assert rates[0] == 0.00050
        assert xdays[0] == '25'

    def test_parse_multiple_pairs(self):
        """Test parsing multiple rate:days pairs"""
        threshold = '0.050:25,0.058:30,0.060:45,0.064:60,0.070:120'
        rates, xdays = parse_xday_threshold(threshold)
        
        assert len(rates) == 5
        assert len(xdays) == 5
        
        # Check rates are correctly converted
        expected_rates = [0.00050, 0.00058, 0.00060, 0.00064, 0.00070]
        for i, expected in enumerate(expected_rates):
            assert abs(rates[i] - expected) < 1e-10
        
        # Check days
        expected_days = ['25', '30', '45', '60', '120']
        assert xdays == expected_days

    def test_parse_threshold_order_preserved(self):
        """Test that order of pairs is preserved"""
        threshold = '0.070:120,0.050:25'  # Reverse order
        rates, xdays = parse_xday_threshold(threshold)
        
        assert rates[0] > rates[1]  # 0.070 > 0.050
        assert xdays[0] == '120'
        assert xdays[1] == '25'

    def test_parse_threshold_with_high_rates(self):
        """Test parsing thresholds with higher rates"""
        threshold = '1.0:60,2.5:90'
        rates, xdays = parse_xday_threshold(threshold)
        
        assert rates[0] == 0.01  # 1.0% -> 0.01
        assert rates[1] == 0.025  # 2.5% -> 0.025
