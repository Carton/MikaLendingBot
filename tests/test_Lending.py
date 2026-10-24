"""
Tests for Lending module utility functions
"""

from decimal import Decimal

from lendingbot.modules.Configuration import CoinConfig, RootConfig, XDayThreshold
from lendingbot.modules.Lending import LendingEngine


def build_engine(thresholds: list[XDayThreshold]) -> LendingEngine:
    engine = LendingEngine(RootConfig(), api=None, log=None, data=None)  # type: ignore[arg-type]
    engine.xday_thresholds = thresholds
    return engine


class TestPerCurrencySettings:
    """Resolution order: coin web > global web > coin TOML > default TOML."""

    def _engine(self) -> LendingEngine:
        engine = LendingEngine(RootConfig(), api=None, log=None, data=None)  # type: ignore[arg-type]
        engine.coin_cfg = {
            "USD": CoinConfig(
                xday_thresholds=[XDayThreshold(rate="0.03", days=30)],
                frr_delta_min=Decimal("-5"),
                frr_delta_max=Decimal("5"),
            ),
            "USDt": CoinConfig(xday_thresholds=[XDayThreshold(rate="0.03", days=60)]),
        }
        engine.default_coin_cfg = CoinConfig()
        return engine

    def test_xday_coin_web_beats_global_web_and_toml(self) -> None:
        engine = self._engine()
        engine.xday_thresholds = [XDayThreshold(rate="0.01", days=10)]
        engine.has_web_xday_override = True
        engine.web_coin_settings = {"USDt": {"xday": [XDayThreshold(rate="0.02", days=20)]}}
        assert [t.days for t in engine.xday_thresholds_for("USDt")] == [20]

    def test_xday_global_web_beats_coin_toml(self) -> None:
        engine = self._engine()
        engine.xday_thresholds = [XDayThreshold(rate="0.01", days=10)]
        engine.has_web_xday_override = True
        assert [t.days for t in engine.xday_thresholds_for("USD")] == [10]

    def test_xday_coin_toml_used_without_web_overrides(self) -> None:
        engine = self._engine()
        assert [t.days for t in engine.xday_thresholds_for("USD")] == [30]
        assert [t.days for t in engine.xday_thresholds_for("USDt")] == [60]
        # Unknown currency falls back to the engine default curve.
        assert engine.xday_thresholds_for("BTC") == engine.xday_thresholds

    def test_calculate_duration_uses_per_currency_curve(self) -> None:
        engine = self._engine()
        engine.web_coin_settings = {"USDt": {"xday": [XDayThreshold(rate="0.03", days=90)]}}
        assert engine._calculate_duration(0.0003, "2", "USDt") == "90"
        assert engine._calculate_duration(0.0003, "2", "USD") == "30"
        assert engine._calculate_duration(0.0003, "2") == "2"

    def test_frr_deltas_priority(self) -> None:
        engine = self._engine()
        assert engine._frr_deltas_for("USD") == (Decimal("-5"), Decimal("5"))
        engine.frrdelta_min = Decimal("-9")
        engine.frrdelta_max = Decimal("9")
        engine.has_web_frr_override = True
        assert engine._frr_deltas_for("USD") == (Decimal("-9"), Decimal("9"))
        engine.web_coin_settings = {"USD": {"frr_min": Decimal("-1"), "frr_max": Decimal("1")}}
        assert engine._frr_deltas_for("USD") == (Decimal("-1"), Decimal("1"))
        assert engine._frr_deltas_for("USDt") == (Decimal("-9"), Decimal("9"))

    def test_parse_web_coin_settings_filters_unknown_currencies(self) -> None:
        engine = self._engine()
        parsed = engine._parse_web_coin_settings(
            {
                "USDt": {"xday_thresholds": [{"rate": 0.03, "days": 40}]},
                "DOGE": {"xday_thresholds": [{"rate": 1.0, "days": 5}]},
                "bogus": "not-a-dict",
            }
        )
        assert list(parsed.keys()) == ["USDt"]
        assert [t.days for t in parsed["USDt"]["xday"]] == [40]


class TestCalculateDuration:
    """Tests for the rate -> days mapping in _calculate_duration"""

    def test_no_thresholds_keeps_requested_days(self) -> None:
        """Without thresholds the requested duration is returned unchanged"""
        engine = build_engine([])
        assert engine._calculate_duration(0.0005, "2") == "2"
        assert engine._calculate_duration(0.0005, "30") == "30"

    def test_rate_below_first_threshold_uses_first_days(self) -> None:
        engine = build_engine([XDayThreshold(rate="0.05", days=25)])
        assert engine._calculate_duration(0.0002, "2") == "25"

    def test_rate_above_last_threshold_uses_last_days(self) -> None:
        engine = build_engine(
            [
                XDayThreshold(rate="0.050", days=25),
                XDayThreshold(rate="0.058", days=30),
                XDayThreshold(rate="0.060", days=45),
                XDayThreshold(rate="0.064", days=60),
                XDayThreshold(rate="0.070", days=120),
            ]
        )
        # Rate is a daily fraction; 0.08% daily is above the 0.070% threshold.
        assert engine._calculate_duration(0.0008, "2") == "120"

    def test_rate_exactly_on_threshold_uses_that_days(self) -> None:
        engine = build_engine(
            [
                XDayThreshold(rate="0.050", days=25),
                XDayThreshold(rate="0.070", days=120),
            ]
        )
        assert engine._calculate_duration(0.0005, "2") == "25"
        assert engine._calculate_duration(0.0007, "2") == "120"

    def test_rate_between_thresholds_is_interpolated(self) -> None:
        """Midpoint rate lands on the midpoint of the two surrounding days"""
        engine = build_engine(
            [
                XDayThreshold(rate="0.03", days=30),
                XDayThreshold(rate="0.05", days=120),
            ]
        )
        assert engine._calculate_duration(0.0004, "2") == "75"

    def test_interpolation_truncates_toward_zero(self) -> None:
        engine = build_engine(
            [
                XDayThreshold(rate="0.03", days=30),
                XDayThreshold(rate="0.05", days=120),
            ]
        )
        # 30 + 90 * 0.375 = 63.75 -> 63
        assert engine._calculate_duration(0.000375, "2") == "63"

    def test_thresholds_only_apply_to_default_duration(self) -> None:
        """A requested duration other than the default "2" is kept as-is"""
        engine = build_engine([XDayThreshold(rate="0.05", days=120)])
        assert engine._calculate_duration(0.0005, "30") == "30"

    def test_unsorted_thresholds_are_matched_by_rate(self) -> None:
        """Threshold order in the list does not need to be pre-sorted"""
        engine = build_engine(
            [
                XDayThreshold(rate="0.070", days=120),
                XDayThreshold(rate="0.050", days=25),
            ]
        )
        assert engine._calculate_duration(0.0002, "2") == "25"
        assert engine._calculate_duration(0.0008, "2") == "120"


class TestExplicitEmptyCurveOverrides:
    """An explicit empty curve is a valid override (disables duration mapping)."""

    def _engine(self) -> LendingEngine:
        engine = LendingEngine(RootConfig(), api=None, log=None, data=None)  # type: ignore[arg-type]
        engine.coin_cfg = {
            "USDt": CoinConfig(xday_thresholds=[XDayThreshold(rate="0.03", days=40)]),
        }
        engine.default_coin_cfg = CoinConfig()
        return engine

    def test_coin_level_empty_curve_beats_coin_toml(self) -> None:
        engine = self._engine()
        engine.web_coin_settings = {"USDt": {"xday": []}}
        assert engine.xday_thresholds_for("USDt") == []
        assert engine._calculate_duration(0.0005, "2", "USDt") == "2"

    def test_global_empty_curve_beats_coin_toml(self) -> None:
        engine = self._engine()
        engine.xday_thresholds = []
        engine.has_web_xday_override = True
        assert engine.xday_thresholds_for("USDt") == []
        assert engine._calculate_duration(0.0005, "2", "USDt") == "2"

    def test_field_level_override_only_xday_keeps_toml_frr(self) -> None:
        engine = self._engine()
        engine.web_coin_settings = {"USDt": {"xday": []}}
        # No FRR override on the coin: falls back to the coin TOML window.
        assert engine._frr_deltas_for("USDt") == (
            CoinConfig().frr_delta_min,
            CoinConfig().frr_delta_max,
        )
