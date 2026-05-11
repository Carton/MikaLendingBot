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


def test_effective_rate_mode_setting_is_removed() -> None:
    script = Path("www/lendingbot.js").read_text(encoding="utf-8")
    html = Path("www/lendingbot.html").read_text(encoding="utf-8")

    assert "name=\"effRateMode\"" not in html
    assert "Effective loan rates calculation" not in html
    assert "Fee Only" not in html
    assert "onlyfee" not in script
    assert "newSettings.effRateMode" not in script
    assert "considering lent percentage and exchange 15% fee" in script


def test_effective_rate_always_uses_lent_percentage() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');

function makeCell() {
  return {
    innerHTML: '',
    style: {},
    setAttribute: function () {}
  };
}

function makeRow() {
  return {
    cells: [],
    appendChild: function () {
      const cell = makeCell();
      this.cells.push(cell);
      return cell;
    }
  };
}

const table = {
  innerHTML: '',
  bodyRows: [],
  insertRow: function () {
    const row = makeRow();
    this.bodyRows.push(row);
    return row;
  },
  createTHead: function () {
    return { insertRow: function () { return makeRow(); } };
  }
};

function jquery() {
  return {
    text: function () { return this; },
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
    getElementById: function (id) {
      if (id === 'detailsTable') return table;
      return {};
    },
    createElement: function () {
      return makeCell();
    }
  }
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('www/lendingbot.js', 'utf8'), context);
context.timespans = [context.Day];
context.updateRawValues({
  USD: {
    averageLendingRate: '0.04',
    lentSum: '50',
    totalCoins: '100',
    maxToLend: '100',
    highestBid: '1'
  }
});

const rateCell = table.bodyRows[0].cells[2].innerHTML;
if (!rateCell.includes('0.01700% Day')) {
  throw new Error('effective rate did not use lent percentage: ' + rateCell);
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


def test_summary_mode_does_not_render_empty_account_earnings() -> None:
    script = r"""
const fs = require('fs');
const vm = require('vm');

function makeCell() {
  return {
    innerHTML: '',
    style: {},
    setAttribute: function () {}
  };
}

function makeRow() {
  return {
    cells: [],
    appendChild: function () {
      const cell = makeCell();
      this.cells.push(cell);
      return cell;
    }
  };
}

const table = {
  innerHTML: '',
  bodyRows: [],
  headRows: [],
  insertRow: function () {
    const row = makeRow();
    this.bodyRows.push(row);
    return row;
  },
  createTHead: function () {
    return {
      insertRow: function () {
        const row = makeRow();
        table.headRows.push(row);
        return row;
      }
    };
  }
};

function jquery() {
  return {
    text: function () { return this; },
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
    getElementById: function (id) {
      if (id === 'detailsTable') return table;
      return {};
    },
    createElement: function () {
      return makeCell();
    }
  }
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('www/lendingbot.js', 'utf8'), context);
context.outputCurrencyDisplayMode = 'summary';
context.timespans = [context.Year, context.Month, context.Week, context.Day, context.Hour];
context.updateOutputCurrency({ currency: 'USD', highestBid: '80000' });
context.updateRawValues({
  USD: { totalCoins: '139176.70496700' }
});

const rendered = table.headRows.concat(table.bodyRows)
  .flatMap(row => row.cells)
  .map(cell => cell.innerHTML)
  .join('\n');

if (rendered.includes('Account<br/>Estimated<br/>Earnings')) {
  throw new Error('empty account summary was rendered');
}
if (rendered.includes('0 USD / Year')) {
  throw new Error('zero-only account summary earnings were rendered');
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
