import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

# Import the new Configuration module
from lendingbot.modules import Configuration as Conf
from lendingbot.modules.Configuration import LendingStrategy
from lendingbot.modules.Data import get_max_duration


class TestConfiguration(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.TemporaryDirectory(dir="C:/tmp")
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

        with self.assertRaises(ValidationError):
            Conf.load_config(self.toml_path)

    def test_unknown_core_config_field_is_rejected(self) -> None:
        content = """
        [bot]
        period_active = 60
        period_activ = 30
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        with self.assertRaises(ValidationError):
            Conf.load_config(self.toml_path)

    def test_all_currencies_loading(self) -> None:
        content = """
        [api]
        all_currencies = ["USD", "BTC", "ETH"]
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)
        config = Conf.load_config(self.toml_path)
        self.assertEqual(config.api.all_currencies, ["USD", "BTC", "ETH"])

    def test_transferable_currencies_loading(self) -> None:
        content = """
        [bot]
        transferable_currencies = ["USD", "BTC"]
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)
        config = Conf.load_config(self.toml_path)
        self.assertEqual(config.bot.transferable_currencies, ["USD", "BTC"])

    def test_rate_percent_conversion(self) -> None:
        """Test that min/max_daily_rate are converted from percent to decimal."""
        content = """
        [coin.default]
        min_daily_rate = 0.005  # 0.005%
        max_daily_rate = 5.0    # 5%
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)
        default_cfg = config.get_coin_config("BTC")

        # 0.005 / 100 = 0.00005
        self.assertEqual(default_cfg.min_daily_rate, Decimal("0.00005"))
        # 5.0 / 100 = 0.05
        self.assertEqual(default_cfg.max_daily_rate, Decimal("0.05"))

    def test_xday_merge_regression(self) -> None:
        """Test that merging specific config doesn't break nested models (xday_thresholds)."""
        content = """
        [coin.default]
        xday_thresholds = [
            { rate = 0.05, days = 30 }
        ]

        [coin.BTC]
        strategy = "FRR"
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)
        # This forces the merge path in get_coin_config
        cfg = config.get_coin_config("BTC")

        # Accessing nested model field should work if correctly parsed
        self.assertIsInstance(cfg.xday_thresholds[0], Conf.XDayThreshold)
        self.assertEqual(cfg.xday_thresholds[0].days, 30)

    def test_sample_configs_load(self) -> None:
        root = Path(__file__).resolve().parents[1]

        basic = Conf.load_config(root / "config_sample.toml")
        advanced = Conf.load_config(root / "config_sample_advanced.toml")

        self.assertEqual(basic.api.exchange, Conf.Exchange.BITFINEX)
        self.assertEqual(advanced.api.exchange, Conf.Exchange.BITFINEX)

    def test_basic_sample_uses_defaults_for_omitted_optional_settings(self) -> None:
        root = Path(__file__).resolve().parents[1]

        config = Conf.load_config(root / "config_sample.toml")

        self.assertEqual(config.bot.period_active, 60)
        self.assertEqual(config.bot.request_timeout, 30)
        self.assertEqual(config.bot.web.host, "127.0.0.1")
        self.assertIsNone(config.get_coin_config("USD").max_active_amount)
        self.assertEqual(config.get_coin_config("USD").max_offer_size, Decimal("0"))

    def test_max_active_amount_semantics(self) -> None:
        default_cfg = Conf.CoinConfig()
        disabled_cfg = Conf.CoinConfig(max_active_amount=Decimal("0"))
        capped_cfg = Conf.CoinConfig(max_active_amount=Decimal("5000"))

        self.assertIsNone(default_cfg.max_active_amount)
        self.assertEqual(disabled_cfg.max_active_amount, Decimal("0"))
        self.assertEqual(capped_cfg.max_active_amount, Decimal("5000"))

        with self.assertRaises(ValidationError):
            Conf.CoinConfig(max_active_amount=Decimal("-1"))

    def test_max_offer_size_semantics(self) -> None:
        default_cfg = Conf.CoinConfig()
        zero_unlimited_cfg = Conf.CoinConfig(max_offer_size=Decimal("0"))
        capped_cfg = Conf.CoinConfig(max_offer_size=Decimal("100"))

        self.assertEqual(default_cfg.max_offer_size, Decimal("0"))
        self.assertEqual(zero_unlimited_cfg.max_offer_size, Decimal("0"))
        self.assertEqual(capped_cfg.max_offer_size, Decimal("100"))

        with self.assertRaises(ValidationError):
            Conf.CoinConfig(max_offer_size=Decimal("-1"))

    def test_end_date_accepts_documented_dash_format(self) -> None:
        assert isinstance(get_max_duration("2999-12-31", "order"), int)

    def test_typed_plugin_defaults(self) -> None:
        config = Conf.RootConfig()

        self.assertEqual(config.plugins.account_stats.report_interval, 86400)
        self.assertEqual(config.plugins.charts.dump_interval, 21600)

    def test_recent_successful_loans_dashboard_setting(self) -> None:
        content = """
        [bot.web]
        recent_successful_loans = 6
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(content)

        config = Conf.load_config(self.toml_path)

        self.assertEqual(config.bot.web.recent_successful_loans, 6)

        invalid = """
        [bot.web]
        recent_successful_loans = 7
        """
        with self.toml_path.open("w", encoding="utf-8") as f:
            f.write(invalid)

        with self.assertRaises(ValidationError):
            Conf.load_config(self.toml_path)
