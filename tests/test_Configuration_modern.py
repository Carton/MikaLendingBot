from decimal import Decimal

from lendingbot.modules import Configuration


def test_coin_config_dataclass():
    """
    Test that CoinConfig is a dataclass and has expected fields.
    This test will fail until CoinConfig is implemented as a dataclass.
    """
    # This will raise AttributeError until implemented
    from lendingbot.modules.Configuration import CoinConfig

    cfg = CoinConfig(
        minrate=Decimal("0.0001"),
        maxactive=Decimal("100"),
        maxtolend=Decimal("1000"),
        maxpercenttolend=Decimal("0.5"),
        maxtolendrate=Decimal("0.0005"),
        gapmode="raw",
        gapbottom=Decimal("10"),
        gaptop=Decimal("20"),
        frrasmin=True,
        frrdelta_min=Decimal("0.00001"),
        frrdelta_max=Decimal("0.00005"),
    )

    assert cfg.minrate == Decimal("0.0001")
    assert cfg.gapmode == "raw"


def test_get_coin_cfg_returns_dataclass(tmp_path):
    """
    Test that get_coin_cfg returns a dictionary of CoinConfig dataclasses.
    """
    config_file = tmp_path / "test.cfg"
    content = """
[BITFINEX]
all_currencies = BTC

[BTC]
mindailyrate = 0.02
maxactiveamount = 50
maxtolend = 500
maxpercenttolend = 25
maxtolendrate = 0.025
gapmode = raw
gapbottom = 5
gaptop = 15
frrasmin = True
frrdelta_min = 0.0001
frrdelta_max = 0.0005
"""
    config_file.write_text(content)
    Configuration.init(str(config_file))

    coin_cfg = Configuration.get_coin_cfg()
    assert "BTC" in coin_cfg

    from lendingbot.modules.Configuration import CoinConfig

    assert isinstance(coin_cfg["BTC"], CoinConfig)
    assert coin_cfg["BTC"].minrate == Decimal("0.0002")
