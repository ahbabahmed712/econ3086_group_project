# Daily pipeline: markets, filter, odds, prices, lead-lag, verdict, report.

import argparse
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

import config
from align import first_cross_date, odds_changes, resample_daily
from filters import rank_by_volume, select_markets
from leadlag import analyse_all
from polymarket import fetch_market_pages, find_markets, get_price_history
from prices import download_prices, to_returns
from report import append_sheet, send_telegram, write_outputs
from tests import known_event_report, test_synthetic_lead
from verdict import make_verdict

load_dotenv(os.path.join(config.BASE_DIR, ".env"))


# Why: four keywords would otherwise download the same pages four times.
def collect_markets(offline):
    """Page the Gamma market list once, then keep questions that match any keyword."""
    raw_rows = fetch_market_pages(offline=offline)
    found = []
    seen_ids = []
    for keyword in config.MARKET_KEYWORDS:
        matches = find_markets(keyword, raw_rows=raw_rows, offline=offline)
        for market in matches:
            if market["market_id"] in seen_ids:
                continue
            seen_ids.append(market["market_id"])
            found.append(market)
    print(f"Unique markets after all keywords: {len(found)}.")
    return found


# Why: downloading odds for every name would miss the three-minute demo limit.
def download_top_odds(markets, offline):
    """Download Yes-token history for the highest-volume names. The rest are rejected."""
    ranked = rank_by_volume(markets)
    rejected = []
    downloaded = []
    for index, market in enumerate(ranked):
        if index >= config.MAX_DOWNLOADS:
            rejected.append(
                {
                    "question": market["question"],
                    "reason": "outside the download limit, so history was not fetched",
                }
            )
            continue
        print(f"Odds history: {market['question']}")
        history = get_price_history(market["yes_token_id"], offline=offline)
        daily = resample_daily(history)
        market["daily_odds"] = daily
        market["n_points"] = int(len(daily))
        market["odds_change"] = odds_changes(daily)
        cross = first_cross_date(daily, 0.50)
        if cross is None:
            print("  First date at or above 50% odds: none in this sample.")
        else:
            print(f"  First date at or above 50% odds: {pandas_date(cross)}.")
        downloaded.append(market)
    return downloaded, rejected


def pandas_date(value):
    """Print a timestamp as a calendar date."""
    return str(value)[:10]


# Why: every asset should cover the same calendar window as the odds we kept.
def price_window(markets):
    """Earliest and latest odds dates, padded by a few days. None if there are no odds."""
    start = None
    end = None
    for market in markets:
        daily = market.get("daily_odds")
        if daily is None or len(daily) == 0:
            continue
        first = daily.index.min()
        last = daily.index.max()
        if start is None or first < start:
            start = first
        if end is None or last > end:
            end = last
    if start is None or end is None:
        return None, None
    start_text = (start - timedelta(days=5)).strftime("%Y-%m-%d")
    end_text = (end + timedelta(days=2)).strftime("%Y-%m-%d")
    return start_text, end_text


# Why: the overlay should be the pair with the strongest correlation, found best-so-far.
def strongest_key(results):
    """Return the (market, asset) key with the largest absolute correlation."""
    best_key = None
    best_abs = None
    for key, result in results.items():
        if result["n_obs"] < 3:
            continue
        size = abs(result["corr"])
        if best_key is None or size > best_abs:
            best_key = key
            best_abs = size
    return best_key


def run(offline):
    """Run the full lead-lag pipeline and write output/."""
    print(f"Lead-lag monitor starting. Offline={offline}.")
    print("Step 1: find markets.")
    markets = collect_markets(offline)
    print("Step 2: download odds for the highest-volume matches and filter.")
    downloaded, early_rejected = download_top_odds(markets, offline)
    chosen, rejected = select_markets(downloaded)
    for item in early_rejected:
        rejected.append(item)
    print(f"Markets kept: {len(chosen)}. Markets rejected: {len(rejected)}.")
    print("Step 3: download asset prices.")
    start, end = price_window(chosen)
    assets = {}
    price_levels = {}
    if start is None:
        print("No odds dates, so asset prices were not downloaded.")
    else:
        print(f"Price window: {start} to {end}.")
        for name, ticker in config.ASSETS.items():
            prices = download_prices(ticker, start, end, name, offline=offline)
            price_levels[name] = prices
            assets[name] = to_returns(prices)
            print(f"  {name}: {len(prices)} prices, {len(assets[name])} returns.")
    print("Step 4: lead-lag tests.")
    results = analyse_all(chosen, assets)
    print("Step 5: verdicts.")
    verdict_rows = []
    for key, result in results.items():
        market_name, asset_name = key
        label, reason = make_verdict(result)
        result["verdict"] = label
        result["reason"] = reason
        print(f"  {market_name} vs {asset_name}: {label}")
        verdict_rows.append(
            {
                "market": market_name,
                "asset": asset_name,
                "verdict": label,
                "reason": reason,
                "lag": result["best_lag"],
                "n_obs": result["n_obs"],
                "corr": result["corr"],
                "adf_odds_p": result["adf_odds_p"],
                "adf_asset_p": result["adf_asset_p"],
            }
        )
    print("Step 6: quick synthetic check (the full list is python tests.py).")
    try:
        test_synthetic_lead()
    except AssertionError:
        print("FAIL synthetic check inside main. Run python tests.py.")
    print("Step 7: known-event note.")
    known_event_report(config.KNOWN_EVENT, None, None)
    print("Step 8: charts and report.")
    odds_for_plot = None
    prices_for_plot = None
    best = strongest_key(results)
    if best is not None:
        market_name, asset_name = best
        for market in chosen:
            if market["question"] == market_name:
                odds_for_plot = {"series": market["daily_odds"], "title": f"{market_name} vs {asset_name}"}
        if asset_name in price_levels:
            prices_for_plot = {"series": price_levels[asset_name]}
        lag = results[best]["best_lag"]
        corr = results[best]["corr"]
        print(f"Strongest pair: {market_name} vs {asset_name}, lag {lag}, corr {corr:.3f}.")
    text = write_outputs(
        chosen, rejected, results, verdict_rows, odds_for_plot, prices_for_plot
    )
    print(text)
    print("Step 9: optional delivery.")
    send_telegram(text)
    sheet_rows = []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for row in verdict_rows:
        sheet_rows.append([stamp, row["market"], row["asset"], row["verdict"], row["lag"], row["n_obs"]])
    append_sheet(sheet_rows)
    print("Done.")
    return results


def main():
    """Command line: python main.py or python main.py --offline."""
    parser = argparse.ArgumentParser(description="Polymarket lead-lag monitor")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use cached CSV and JSON files only. Do not call the network.",
    )
    args = parser.parse_args()
    run(offline=args.offline)


if __name__ == "__main__":
    main()
