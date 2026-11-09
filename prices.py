# Download daily asset prices with yfinance and turn them into percentage returns.

import os

import pandas
import yfinance

import config


# Why: yfinance 1.x puts the ticker in a second column level. Tests use a flat frame.
def close_from_frame(frame):
    """Pull one adjusted-close column out of a yfinance table. Empty in, empty out."""
    if frame is None or len(frame) == 0:
        return pandas.Series(dtype=float)
    if "Close" not in frame.columns and not isinstance(frame.columns, pandas.MultiIndex):
        return pandas.Series(dtype=float)
    close = frame["Close"]
    if isinstance(close, pandas.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    close.index = pandas.to_datetime(close.index).tz_localize(None)
    close.name = "close"
    return close


# Why: the lead test must use changes. A high price level is not a move.
def to_returns(series):
    """Percentage change from one price to the next. 100 then 110 becomes 10."""
    changes = []
    dates = []
    previous = None
    for date, price in series.items():
        if previous is not None and previous != 0:
            percent = (price - previous) / previous * 100
            changes.append(percent)
            dates.append(date)
        previous = price
    return pandas.Series(changes, index=dates, name="return_pct")


def _cache_path(cache_name):
    """CSV path for one asset. The name is the label, such as Gold."""
    safe = str(cache_name).replace("^", "").replace("=", "").replace(".", "")
    return os.path.join(config.DATA_DIR, f"price_{safe}.csv")


# Why: offline mode and failed downloads must still return a Series.
def read_price_cache(path):
    """Load a cached close Series. Missing files become an empty Series."""
    if not os.path.exists(path):
        print(f"No cached prices at {path}.")
        return pandas.Series(dtype=float)
    frame = pandas.read_csv(path, index_col=0, parse_dates=True)
    if frame.shape[1] == 0:
        return pandas.Series(dtype=float)
    series = frame.iloc[:, 0]
    series.index = pandas.to_datetime(series.index).tz_localize(None)
    series.name = "close"
    return series


# Why: the program has to fetch live prices, and it has to survive a bad day.
def download_prices(ticker, start, end, cache_name, offline=False):
    """Download adjusted close for ticker between start and end. Cache it as CSV."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    cache_path = _cache_path(cache_name)
    if not offline:
        try:
            frame = yfinance.download(
                ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )
            series = close_from_frame(frame)
            if len(series) == 0:
                raise ValueError("yfinance returned no rows.")
            series.to_frame().to_csv(cache_path)
            print(f"Saved {len(series)} prices for {cache_name} ({ticker}).")
            return series
        except Exception as exc:
            print(f"Price download failed for {ticker}: {exc}")
    else:
        print(f"Offline mode: reading cached prices for {cache_name}.")
    cached = read_price_cache(cache_path)
    if len(cached) == 0:
        print(f"No price data for {ticker}.")
    return cached
