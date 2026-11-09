# Download Polymarket questions and Yes-token odds. Cache every reply under data/.

import json
import os

import pandas
import requests

import config


# Why: one place for "this value did not parse" so callers can keep going.
def as_float(value):
    """Convert a volume or liquidity field to a float. Bad values become 0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# Why: the API sends token ids and outcome names as JSON text, not as lists.
def parse_json_list(value):
    """Read a JSON list stored as text. A real list is returned unchanged."""
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return parsed
    return []


# Why: the Yes price is the market probability. The No token is the mirror image.
def yes_token_id(token_ids, outcomes):
    """Pick the Yes token. If the market has no Yes label, use the first token."""
    for index, name in enumerate(outcomes):
        if str(name).strip().lower() == "yes" and index < len(token_ids):
            return str(token_ids[index])
    if len(token_ids) == 0:
        return ""
    return str(token_ids[0])


# Why: the rest of the program should not depend on the raw API field names.
def parse_market(raw):
    """Turn one Gamma market object into a small dictionary."""
    token_ids = parse_json_list(raw.get("clobTokenIds"))
    outcomes = parse_json_list(raw.get("outcomes"))
    volume = raw.get("volumeNum")
    if volume is None:
        volume = raw.get("volume")
    liquidity = raw.get("liquidityNum")
    if liquidity is None:
        liquidity = raw.get("liquidity")
    market = {
        "question": str(raw.get("question") or ""),
        "market_id": str(raw.get("id") or ""),
        "token_ids": [str(token) for token in token_ids],
        "yes_token_id": yes_token_id(token_ids, outcomes),
        "volume": as_float(volume),
        "liquidity": as_float(liquidity),
        "end_date": str(raw.get("endDate") or ""),
        "closed": bool(raw.get("closed")),
        "n_points": 0,
    }
    return market


# Why: tests can check the parser without calling the network.
def parse_price_history(payload):
    """Turn a CLOB prices-history JSON object into a UTC Series of odds."""
    history = []
    if isinstance(payload, dict):
        history = payload.get("history") or []
    times = []
    prices = []
    for row in history:
        times.append(pandas.to_datetime(int(row["t"]), unit="s", utc=True))
        prices.append(float(row["p"]))
    series = pandas.Series(prices, index=times, name="odds")
    series = series.sort_index()
    return series


# Why: GET /markets is a list, paged with limit and offset. Checked in the docs.
def fetch_market_page(offset, limit):
    """Download one page of open markets ordered by volume, highest first."""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": limit,
        "offset": offset,
        "order": "volumeNum",
        "ascending": "false",
        "closed": "false",
    }
    response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Gamma /markets did not return a list.")
    return payload


def _pages_cache_path():
    """Path of the raw market-page cache."""
    return os.path.join(config.DATA_DIR, "market_pages.json")


# Why: a failed request should not wipe out the last good download.
def fetch_market_pages(offline=False):
    """Walk offset pages with a for loop. On failure, read data/market_pages.json."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    cache_path = _pages_cache_path()
    if offline:
        return _read_pages_cache(cache_path)
    rows = []
    offset = 0
    try:
        for _page in range(config.MAX_MARKET_PAGES):
            batch = fetch_market_page(offset, config.MARKET_PAGE_SIZE)
            if len(batch) == 0:
                break
            for row in batch:
                rows.append(row)
            print(f"Fetched market page at offset {offset}: {len(batch)} rows.")
            offset = offset + config.MARKET_PAGE_SIZE
            if len(batch) < config.MARKET_PAGE_SIZE:
                break
    except (requests.RequestException, ValueError) as exc:
        print(f"Market list request failed: {exc}")
        cached = _read_pages_cache(cache_path)
        if len(cached) > 0:
            print("Using the cached market list.")
            return cached
        return rows
    if len(rows) == 0:
        print("Market list was empty. Trying the cache.")
        return _read_pages_cache(cache_path)
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle)
    return rows


def _read_pages_cache(cache_path):
    """Read the cached market pages. Missing or broken files become an empty list."""
    if not os.path.exists(cache_path):
        print(f"No cached market list at {cache_path}.")
        return []
    try:
        with open(cache_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read the market cache: {exc}")
        return []
    if not isinstance(payload, list):
        return []
    return payload


# Why: the list endpoint cannot search by word, so the filter happens here.
def find_markets(keyword, raw_rows=None, offline=False):
    """Return markets whose question contains keyword. Pages the Gamma list once if needed."""
    if raw_rows is None:
        raw_rows = fetch_market_pages(offline=offline)
    matches = []
    seen_ids = []
    needle = keyword.lower()
    for raw in raw_rows:
        market = parse_market(raw)
        if needle not in market["question"].lower():
            continue
        if market["market_id"] in seen_ids:
            continue
        seen_ids.append(market["market_id"])
        matches.append(market)
    print(f"Keyword '{keyword}' matched {len(matches)} markets in the downloaded pages.")
    return matches


def _odds_cache_path(token_id):
    """CSV path for one token. The token id is the file name."""
    return os.path.join(config.DATA_DIR, f"odds_{token_id}.csv")


# Why: tests and the offline demo both need the same reader.
def read_odds_cache(path):
    """Load a cached odds Series. Returns an empty Series if the file is missing."""
    if not os.path.exists(path):
        print(f"No cached odds at {path}.")
        return pandas.Series(dtype=float)
    frame = pandas.read_csv(path, index_col=0, parse_dates=True)
    if frame.shape[1] == 0:
        return pandas.Series(dtype=float)
    series = frame.iloc[:, 0]
    series.index = pandas.to_datetime(series.index, utc=True)
    series.name = "odds"
    return series


# Why: history is required for the lead test, and the live call can fail.
def get_price_history(token_id, offline=False):
    """Download CLOB odds for one token. Fall back to data/odds_<token>.csv."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    cache_path = _odds_cache_path(token_id)
    if token_id == "":
        print("This market has no token id, so there is no odds history.")
        return read_odds_cache(cache_path)
    if offline:
        print(f"Offline mode: reading cached odds for {token_id[:12]}...")
        return read_odds_cache(cache_path)
    url = "https://clob.polymarket.com/prices-history"
    params = {
        "market": token_id,
        "interval": config.PRICE_HISTORY_INTERVAL,
        "fidelity": config.PRICE_HISTORY_FIDELITY,
    }
    try:
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        series = parse_price_history(payload)
        if len(series) == 0:
            raise ValueError("The price history list was empty.")
        series.to_frame().to_csv(cache_path)
        print(f"Saved {len(series)} odds points for token {token_id[:12]}...")
        return series
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"Price history failed for token {token_id[:12]}...: {exc}")
        return read_odds_cache(cache_path)
