import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

# Import the new Configuration module
from lendingbot.modules import Configuration as Conf
from lendingbot.modules.Configuration import LendingStrategy


class TestConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.TemporaryDirectory()
        self.toml_path = Path(self.test_dir.name) / "test_config.toml"

    def tearDown(self) -> None:
        self.test_dir.cleanup()

    def test_load_basic(self) -> None:
        content = """
        [api]
        exchange = "Poloniex"
        apikey = "123"
        secret = "abc"

        [bot]
        period_active = 120
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)

        self.assertEqual(config.api.exchange, "Poloniex")
        self.assertEqual(config.bot.period_active, 120)
        self.assertEqual(config.bot.period_inactive, 300)  # Default

    def test_coin_defaults_and_overrides(self) -> None:
        # Override strategy in BTC, inherit min_loan_size
        content = """
        [coin.default]
        min_loan_size = 0.5
        strategy = "Spread"
        gap_bottom = 10

        [coin.BTC]
        strategy = "FRR"
        gap_bottom = 20
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)

        # Check Default
        default_cfg = config.coin["default"]
        self.assertEqual(default_cfg.min_loan_size, Decimal("0.5"))
        self.assertEqual(default_cfg.strategy, LendingStrategy.SPREAD)

        # Check BTC (Overrides)
        btc_cfg = config.get_coin_config("BTC")
        self.assertEqual(btc_cfg.strategy, LendingStrategy.FRR)  # Overridden
        self.assertEqual(btc_cfg.gap_bottom, Decimal("20"))  # Overridden
        self.assertEqual(btc_cfg.min_loan_size, Decimal("0.5"))  # Inherited

        # Check ETH (Inherits default implicitly)
        eth_cfg = config.get_coin_config("ETH")
        self.assertEqual(eth_cfg.strategy, LendingStrategy.SPREAD)  # Inherited

    def test_xday_formatting(self) -> None:
        content = """
        [coin.default]
        xday_thresholds = [
            { rate = 0.05, days = 30 }
        ]
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)
        cfg = config.get_coin_config("BTC")
        self.assertEqual(cfg.xday_thresholds[0].days, 30)

    def test_validation_error(self) -> None:
        content = """
        [bot]
        period_active = -5  # Invalid
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            Conf.load_config(self.toml_path)
