"""
Tests for Lending module utility functions
"""

from lendingbot.modules.Configuration import RootConfig, XDayThreshold
from lendingbot.modules.Lending import LendingEngine


def build_engine(thresholds: list[XDayThreshold]) -> LendingEngine:
    engine = LendingEngine(RootConfig(), api=None, log=None, data=None)  # type: ignore[arg-type]
    engine.xday_thresholds = thresholds
    return engine


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
