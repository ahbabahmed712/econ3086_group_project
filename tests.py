# Assert tests, plus the synthetic, reverse, placebo, known-event and calibration checks.
# Run with: python tests.py

from datetime import timedelta

import numpy
import pandas

import config
from align import first_cross_date, merge_series, odds_changes, resample_daily
from filters import is_liquid, rank_by_volume, select_markets
from leadlag import (
    adf_pvalue,
    analyse_all,
    best_lag,
    bonferroni,
    corr_pvalue,
    cross_corr,
    granger_both_ways,
)
from polymarket import as_float, parse_json_list, parse_market, parse_price_history, yes_token_id
from prices import close_from_frame, to_returns
from report import append_sheet, build_report, send_telegram
from verdict import make_verdict


def _say(name, ok):
    """Print PASS or FAIL for one test."""
    if ok:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")


def _check(name, condition):
    """Assert one fact and print the result. A failure stops this test."""
    assert condition
    _say(name, True)


def test_parse_helpers():
    """Sample Gamma and CLOB payloads parse into the fields the rest of the code uses."""
    assert as_float("12.5") == 12.5
    assert as_float("nope") == 0.0
    assert parse_json_list('["Yes", "No"]') == ["Yes", "No"]
    assert yes_token_id(["yes-token", "no-token"], ["Yes", "No"]) == "yes-token"
    raw = {
        "id": "9",
        "question": "Will the Fed cut rates?",
        "clobTokenIds": '["yes-token", "no-token"]',
        "outcomes": '["Yes", "No"]',
        "volumeNum": 250000,
        "liquidityNum": 1000,
        "endDate": "2026-12-31T00:00:00Z",
        "closed": False,
    }
    market = parse_market(raw)
    assert market["question"] == "Will the Fed cut rates?"
    assert market["market_id"] == "9"
    assert market["yes_token_id"] == "yes-token"
    assert market["volume"] == 250000
    assert market["closed"] is False
    payload = {"history": [{"t": 1700000000, "p": 0.4}, {"t": 1700086400, "p": 0.5}]}
    series = parse_price_history(payload)
    assert len(series) == 2
    assert float(series.iloc[0]) == 0.4
    _say("parse helpers", True)


def test_is_liquid_and_select():
    """Made-up markets: one liquid, one thin, one closed. The liquid one is kept."""
    liquid = {
        "question": "Liquid Fed market",
        "market_id": "a",
        "volume": 500000,
        "n_points": 40,
        "closed": False,
    }
    thin = {
        "question": "Thin market",
        "market_id": "b",
        "volume": 10,
        "n_points": 2,
        "closed": False,
    }
    closed = {
        "question": "Closed market",
        "market_id": "c",
        "volume": 900000,
        "n_points": 50,
        "closed": True,
    }
    ok, reason = is_liquid(liquid, config.MIN_VOLUME, config.MIN_POINTS)
    assert ok is True
    assert "minimum" in reason
    bad, bad_reason = is_liquid(thin, config.MIN_VOLUME, config.MIN_POINTS)
    assert bad is False
    assert "volume" in bad_reason
    shut, shut_reason = is_liquid(closed, config.MIN_VOLUME, config.MIN_POINTS)
    assert shut is False
    assert shut_reason == "market is closed"
    ranked = rank_by_volume([thin, liquid])
    assert ranked[0]["market_id"] == "a"
    chosen, rejected = select_markets([liquid, thin, closed])
    assert len(chosen) == 1
    assert chosen[0]["market_id"] == "a"
    assert len(rejected) == 2
    _say("filters", True)


def test_returns_and_close():
    """Prices 100 then 110 give a 10 percent return. An empty frame gives an empty series."""
    prices = pandas.Series([100.0, 110.0], index=pandas.to_datetime(["2026-01-01", "2026-01-02"]))
    returns = to_returns(prices)
    assert len(returns) == 1
    assert abs(float(returns.iloc[0]) - 10.0) < 1e-9
    frame = pandas.DataFrame({"Close": [5.0, 6.0]}, index=pandas.to_datetime(["2026-01-01", "2026-01-02"]))
    close = close_from_frame(frame)
    assert float(close.iloc[1]) == 6.0
    assert len(close_from_frame(pandas.DataFrame())) == 0
    _say("prices", True)


def test_align():
    """Hand-made odds: daily last print, first difference, inner join, first threshold cross."""
    index = pandas.to_datetime(
        ["2026-01-01 01:00", "2026-01-01 18:00", "2026-01-03 12:00"], utc=True
    )
    odds = pandas.Series([0.20, 0.40, 0.55], index=index)
    daily = resample_daily(odds)
    assert len(daily) == 2
    assert abs(float(daily.iloc[0]) - 0.40) < 1e-9
    changes = odds_changes(daily)
    assert abs(float(changes.iloc[0]) - 0.15) < 1e-9
    returns = pandas.Series([1.0, 2.0], index=pandas.to_datetime(["2026-01-01", "2026-01-04"]))
    # Rebuild a change series that shares one date with returns.
    odds_chg = pandas.Series([0.1, 0.2], index=pandas.to_datetime(["2026-01-01", "2026-01-04"]))
    frame, n_obs = merge_series(odds_chg, returns)
    assert n_obs == 2
    assert list(frame.columns) == ["odds_change", "asset_return"]
    first = first_cross_date(daily, 0.50)
    assert pandas.Timestamp(first) == pandas.Timestamp("2026-01-03")
    assert first_cross_date(daily, 0.99) is None
    _say("align", True)


def test_corr_and_bonferroni():
    """A perfect line has correlation 1. Bonferroni multiplies p-values and caps at 1."""
    x = pandas.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pandas.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    assert abs(cross_corr(x, y, 0) - 1.0) < 1e-9
    assert corr_pvalue(0.0, 30) == 1.0 or abs(corr_pvalue(0.0, 30) - 1.0) < 1e-9
    assert corr_pvalue(0.2, 2) == 1.0
    adjusted = bonferroni([0.04, 0.5], 3)
    assert abs(adjusted[0] - 0.12) < 1e-9
    assert adjusted[1] == 1.0
    _say("correlation helpers", True)


def test_synthetic_lead():
    """Asset returns are the odds change from two days earlier, plus tiny noise. Lag must be 2."""
    rng = numpy.random.default_rng(7)
    odds = pandas.Series(rng.normal(0, 1, 160))
    noise = rng.normal(0, 0.05, 160)
    asset = odds.shift(2) + noise
    frame = pandas.DataFrame({"odds": odds, "asset": asset}).dropna()
    lag, corr = best_lag(frame["odds"], frame["asset"], config.MAX_LAG)
    assert lag == 2
    assert corr > 0.8
    _say("synthetic lead", True)


def test_reverse_lead():
    """If odds follow the asset by two days, the lag is negative and the verdict is not a lead."""
    rng = numpy.random.default_rng(11)
    asset = pandas.Series(rng.normal(0, 1, 160))
    noise = rng.normal(0, 0.05, 160)
    odds = asset.shift(2) + noise
    frame = pandas.DataFrame({"odds": odds, "asset": asset}).dropna()
    lag, corr = best_lag(frame["odds"], frame["asset"], config.MAX_LAG)
    assert lag < 0
    forward, backward = granger_both_ways(frame["odds"], frame["asset"], config.MAX_LAG)
    overlap = len(frame) - abs(lag)
    result = {
        "n_obs": len(frame),
        "passed_filter": True,
        "best_lag": lag,
        "adjusted_p": corr_pvalue(corr, overlap),
        "granger_odds_to_asset_p": forward,
        "granger_asset_to_odds_p": backward,
    }
    verdict, _reason = make_verdict(result)
    assert verdict != "LEAD DETECTED"
    _say("reverse lead", True)


def test_verdicts():
    """One hand-built result for each of the three labels."""
    thin = {
        "n_obs": 5,
        "passed_filter": True,
        "best_lag": 2,
        "adjusted_p": 0.01,
        "granger_odds_to_asset_p": 0.01,
        "granger_asset_to_odds_p": 0.40,
    }
    label, _reason = make_verdict(thin)
    assert label == "DATA TOO THIN"
    lead = {
        "n_obs": 40,
        "passed_filter": True,
        "best_lag": 2,
        "adjusted_p": 0.01,
        "granger_odds_to_asset_p": 0.01,
        "granger_asset_to_odds_p": 0.40,
    }
    label, _reason = make_verdict(lead)
    assert label == "LEAD DETECTED"
    none = {
        "n_obs": 40,
        "passed_filter": True,
        "best_lag": -1,
        "adjusted_p": 0.20,
        "granger_odds_to_asset_p": 0.30,
        "granger_asset_to_odds_p": 0.04,
    }
    label, _reason = make_verdict(none)
    assert label == "NO RELIABLE LEAD"
    blocked = dict(lead)
    blocked["passed_filter"] = False
    label, _reason = make_verdict(blocked)
    assert label == "DATA TOO THIN"
    _say("verdicts", True)


def test_analyse_all_and_adf():
    """Results are stored in a dictionary keyed by (market name, asset name)."""
    rng = numpy.random.default_rng(3)
    index = pandas.date_range("2026-01-01", periods=40, freq="D")
    odds_change = pandas.Series(rng.normal(0, 0.02, 40), index=index)
    returns = pandas.Series(rng.normal(0, 1, 40), index=index)
    markets = [{"question": "Sample market", "odds_change": odds_change}]
    assets = {"Gold": returns}
    results = analyse_all(markets, assets)
    assert ("Sample market", "Gold") in results
    result = results[("Sample market", "Gold")]
    assert result["n_obs"] == 40
    assert "adjusted_p" in result
    assert 0.0 <= adf_pvalue(returns) <= 1.0
    _say("analyse_all", True)


def test_placebo():
    """Shift unrelated series by a large random amount and count false leads.

    A false lead here means: best lag is positive and the Bonferroni-adjusted
    p-value across the lags we searched is below alpha. The rate should sit
    near alpha or below. The full verdict also requires Granger, so that
    stricter rate is printed as well.
    """
    rng = numpy.random.default_rng(1)
    runs = 30
    raw_hits = 0
    adjusted_hits = 0
    strict_hits = 0
    lags_tested = config.MAX_LAG * 2 + 1
    for _run in range(runs):
        odds = pandas.Series(rng.normal(0, 1, 120))
        asset = pandas.Series(rng.normal(0, 1, 120))
        shift = int(rng.integers(25, 50))
        moved = pandas.concat([odds.iloc[shift:], odds.iloc[:shift]], ignore_index=True)
        lag, corr = best_lag(moved, asset, config.MAX_LAG)
        overlap = len(moved) - abs(lag)
        p_value = corr_pvalue(corr, overlap)
        p_adjusted = min(1.0, p_value * lags_tested)
        if lag > 0 and p_value < config.ALPHA:
            raw_hits = raw_hits + 1
        if lag > 0 and p_adjusted < config.ALPHA:
            adjusted_hits = adjusted_hits + 1
            forward, backward = granger_both_ways(moved, asset, config.MAX_LAG)
            result = {
                "n_obs": len(moved),
                "passed_filter": True,
                "best_lag": lag,
                "adjusted_p": p_adjusted,
                "granger_odds_to_asset_p": forward,
                "granger_asset_to_odds_p": backward,
            }
            verdict, _reason = make_verdict(result)
            if verdict == "LEAD DETECTED":
                strict_hits = strict_hits + 1
    raw_rate = raw_hits / runs
    adjusted_rate = adjusted_hits / runs
    strict_rate = strict_hits / runs
    print(
        f"Placebo rates over {runs} runs: "
        f"raw best-lag {raw_rate:.2f}, "
        f"Bonferroni-across-lags {adjusted_rate:.2f}, "
        f"full verdict {strict_rate:.2f}. "
        f"Alpha is {config.ALPHA:.2f}."
    )
    assert adjusted_rate <= 0.25
    _say("placebo", True)


def test_known_event():
    """Empty config must not invent an event. A filled dict prints the window and the lag."""
    message = known_event_report(config.KNOWN_EVENT, None, None)
    assert "does not invent" in message
    event = {
        "name": "Synthetic class example",
        "date": "2026-01-10",
        "market_question_contains": "synthetic",
        "asset_name": "Gold",
        "window_days": 2,
    }
    odds_index = pandas.date_range("2026-01-08", periods=5, freq="D")
    odds = pandas.Series([0.40, 0.42, 0.50, 0.55, 0.53], index=odds_index)
    asset = pandas.Series([100, 101, 103, 102, 104], index=odds_index)
    message = known_event_report(event, odds, asset)
    assert "Synthetic class example" in message
    assert "lag" in message
    _say("known event", True)


def known_event_report(event, odds, asset):
    """Print odds and the asset around one configured event. Return the same text."""
    name = ""
    event_date = ""
    if isinstance(event, dict):
        name = event.get("name") or ""
        event_date = event.get("date") or ""
    if name == "" or event_date == "":
        text = (
            "Known-event check skipped: KNOWN_EVENT in config.py is empty. "
            "The team must fill a real event. This program does not invent one."
        )
        print(text)
        return text
    center = pandas.Timestamp(event_date)
    window = int(event.get("window_days") or 5)
    lines = [f"Known event: {name} on {event_date}."]
    if odds is None or asset is None:
        lines.append("No series was passed in, so there is nothing to print around the date.")
        text = "\n".join(lines)
        print(text)
        return text
    odds_window = _window(odds, center, window)
    asset_window = _window(asset, center, window)
    lines.append("Odds in the window:")
    for date, value in odds_window.items():
        lines.append(f"  {pandas.Timestamp(date).date()}: {float(value):.4f}")
    lines.append("Asset in the window:")
    for date, value in asset_window.items():
        lines.append(f"  {pandas.Timestamp(date).date()}: {float(value):.4f}")
    changes = odds_changes(odds)
    returns = to_returns(asset)
    frame, n_obs = merge_series(changes, returns)
    if n_obs < 3:
        lines.append("Not enough overlap to estimate a lag.")
    else:
        lag, corr = best_lag(frame["odds_change"], frame["asset_return"], config.MAX_LAG)
        lines.append(f"Detected lag on this short window: {lag} (correlation {corr:.3f}).")
    text = "\n".join(lines)
    print(text)
    return text


def _window(series, center, window):
    """Rows whose date is within `window` days of the event date."""
    start = center - timedelta(days=window)
    end = center + timedelta(days=window)
    kept_index = []
    kept_values = []
    for date, value in series.items():
        stamp = pandas.Timestamp(date).tz_localize(None)
        if stamp >= start and stamp <= end:
            kept_index.append(stamp)
            kept_values.append(value)
    return pandas.Series(kept_values, index=kept_index)


def test_calibration():
    """Two of three markets in the 60 to 80 percent bin resolved Yes, so the share is 2/3."""
    rows = [
        {"odds_before": 0.70, "resolved_yes": True},
        {"odds_before": 0.65, "resolved_yes": True},
        {"odds_before": 0.75, "resolved_yes": False},
        {"odds_before": 0.20, "resolved_yes": False},
    ]
    table = calibration_table(rows)
    share = None
    for row in table:
        if row["low"] == 0.60:
            share = row["share_yes"]
    assert share is not None
    assert abs(share - (2 / 3)) < 1e-9
    _say("calibration", True)


def calibration_table(rows):
    """Bin the odds from the day before resolution and print the share that resolved Yes."""
    bins = [(0.00, 0.20), (0.20, 0.40), (0.40, 0.60), (0.60, 0.80), (0.80, 1.01)]
    table = []
    print("Calibration: share that resolved Yes, by the odds one day before resolution.")
    for low, high in bins:
        group = []
        for row in rows:
            odds = row["odds_before"]
            if odds >= low and odds < high:
                group.append(row)
        share = None
        if len(group) > 0:
            yes_count = 0
            for row in group:
                if row["resolved_yes"]:
                    yes_count = yes_count + 1
            share = yes_count / len(group)
            print(f"  {low:.0%} to {high:.0%}: {yes_count} of {len(group)} resolved Yes ({share:.2f}).")
        else:
            print(f"  {low:.0%} to {high:.0%}: no markets in this bin.")
        table.append({"low": low, "high": high, "count": len(group), "share_yes": share})
    return table


def test_report_and_delivery():
    """The report text contains the limits paragraph. Empty secrets do not raise."""
    chosen = [{"question": "Sample", "volume": 10, "n_points": 30}]
    rejected = [{"question": "Other", "reason": "volume is below the minimum"}]
    verdicts = [
        {
            "market": "Sample",
            "asset": "Gold",
            "verdict": "NO RELIABLE LEAD",
            "reason": "checks failed",
            "n_obs": 30,
            "corr": 0.1,
            "adf_odds_p": 0.2,
            "adf_asset_p": 0.3,
        }
    ]
    text = build_report(chosen, rejected, verdicts, when="2026-11-09 00:00 UTC")
    assert "NO RELIABLE LEAD" in text
    assert "does not prove causation" in text
    assert send_telegram("hello", token="", chat_id="") is False
    assert append_sheet([["a"]], credentials_file="", sheet_id="") is False
    _say("report", True)


def run_all():
    """Run every test and print a final count."""
    tests = [
        test_parse_helpers,
        test_is_liquid_and_select,
        test_returns_and_close,
        test_align,
        test_corr_and_bonferroni,
        test_synthetic_lead,
        test_reverse_lead,
        test_verdicts,
        test_analyse_all_and_adf,
        test_placebo,
        test_known_event,
        test_calibration,
        test_report_and_delivery,
    ]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:
            failed = failed + 1
            print(f"FAIL {test.__name__}: {exc}")
    passed = len(tests) - failed
    print(f"{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    raise SystemExit(run_all())
