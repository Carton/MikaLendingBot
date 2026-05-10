import subprocess
from pathlib import Path


def test_status_poll_interval_uses_configured_refresh_rate() -> None:
    script = Path("www/lendingbot.js").read_text(encoding="utf-8")

    assert "statusRefreshRate = 5" not in script
    assert "scheduleStatusRefresh(refreshRate * 1000)" in script


def test_status_fetch_does_not_render_full_stats_table() -> None:
    script = Path("www/lendingbot.js").read_text(encoding="utf-8")
    fetch_status = script[script.index("function fetchStatus()") :]
    fetch_status = fetch_status[: fetch_status.index("function refreshStatusSoon()")]

    assert "get_status" in fetch_status
    assert "updateJson(" not in fetch_status
    assert "updateRawValues(" not in fetch_status


def test_update_json_does_not_show_waiting_when_stats_are_present() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');

const captured = {};
function jquery(selector) {
  return {
    text: function (value) {
      if (arguments.length > 0) captured[selector] = value;
      return this;
    },
    empty: function () { return this; },
    append: function () { return this; },
    find: function () { return { tooltip: function () { return this; } }; },
    ready: function () { return this; }
  };
}
jquery.each = function () {};

const context = {
  console: console,
  $: jquery,
  document: {
    title: '',
    getElementById: function () {
      return {
        innerHTML: '',
        insertRow: function () {
          return { appendChild: function () { return { style: {}, setAttribute: function () {} }; } };
        },
        createTHead: function () {
          return { insertRow: function () { return { appendChild: function () { return { style: {}, setAttribute: function () {} }; } }; } };
        }
      };
    },
    createElement: function () {
      return { style: {}, setAttribute: function () {} };
    }
  }
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('www/lendingbot.js', 'utf8'), context);
context.updateJson({
  last_status: '',
  last_update: '2026-05-10 18:27:48',
  exchange: 'Bitfinex',
  label: 'Lending Bot',
  raw_data: { USD: { totalCoins: '139176.70496700' } },
  outputCurrency: { currency: 'USD', highestBid: '80775.44426494346' }
});

if (captured['#status'] === 'Waiting for bot status update...') {
  throw new Error('status incorrectly shows waiting text when stats are present');
}
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
