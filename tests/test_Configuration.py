
import unittest
from decimal import Decimal
from pathlib import Path
import tempfile
import os

from lendingbot.modules import Configuration_new as Conew
from lendingbot.modules.Configuration_new import LendingStrategy, GapMode

class TestConfigurationNew(unittest.TestCase):
    def setUp(self):
        # Create a temporary TOML file
        self.test_dir = tempfile.TemporaryDirectory()
        self.toml_path = Path(self.test_dir.name) / "test_config.toml"
        
    def tearDown(self):
        self.test_dir.cleanup()

    def test_load_basic(self):
        content = """
        [api]
        exchange = "Poloniex"
        apikey = "123"
        secret = "abc"
        
        [bot]
        period_active = 120
        """
        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        config = Conew.load_config(self.toml_path)
        
        self.assertEqual(config.api.exchange, "Poloniex")
        self.assertEqual(config.bot.period_active, 120)
        self.assertEqual(config.bot.period_inactive, 300) # Default
        
    def test_coin_defaults_and_overrides(self):
        content = """
        [coin.default]
        min_loan_size = 0.5
        strategy = "Spread"
        gap_bottom = 10
        
        [coin.BTC]
        strategy = "FRR"
        gap_bottom = 20
        
        [coin.ETH]
        # Inherits all defaults
        """
        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        config = Conew.load_config(self.toml_path)
        
        # Check Default
        default_cfg = config.coin["default"]
        self.assertEqual(default_cfg.min_loan_size, Decimal("0.5"))
        self.assertEqual(default_cfg.strategy, LendingStrategy.SPREAD)
        
        # Check BTC (Overrides)
        btc_cfg = config.get_coin_config("BTC")
        self.assertEqual(btc_cfg.strategy, LendingStrategy.FRR)     # Overridden
        self.assertEqual(btc_cfg.gap_bottom, Decimal("20"))         # Overridden
        self.assertEqual(btc_cfg.min_loan_size, Decimal("0.5"))     # Inherited
        
        # Check ETH (Inherits)
        eth_cfg = config.get_coin_config("ETH")
        self.assertEqual(eth_cfg.strategy, LendingStrategy.SPREAD)  # Inherited
        self.assertEqual(eth_cfg.gap_bottom, Decimal("10"))         # Inherited

    def test_validation_error(self):
        # Invalid daily rate > 5.0
        content = """
        [coin.default]
        max_daily_rate = 6.0 
        """
        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            Conew.load_config(self.toml_path)

    def test_xday_thresholds_parsing(self):
        content = """
        [coin.default]
        xday_thresholds = [
            { rate = 0.05, days = 30 },
            { rate = 0.06, days = 60 }
        ]
        """
        with open(self.toml_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        config = Conew.load_config(self.toml_path)
        cfg = config.get_coin_config("BTC")
        
        self.assertEqual(len(cfg.xday_thresholds), 2)
        self.assertEqual(cfg.xday_thresholds[0].days, 30)
        # Verify Decimal conversion if possible, or float comparison
        self.assertAlmostEqual(float(cfg.xday_thresholds[0].rate), 0.05)

if __name__ == '__main__':
    unittest.main()
