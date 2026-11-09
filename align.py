# Put odds changes and asset returns on the same dates.

import pandas


# Why: the test compares moves, not the level of the probability.
def odds_changes(series):
    """First difference of odds. A move from 0.40 to 0.45 is +0.05."""
    changes = []
    dates = []
    previous = None
    for date, price in series.items():
        if previous is not None:
            changes.append(price - previous)
            dates.append(date)
        previous = price
    return pandas.Series(changes, index=dates, name="odds_change")


# Why: Polymarket trades all weekend. Gold, the dollar and Nasdaq do not.
def resample_daily(series):
    """Keep the last odds print of each UTC day.

    Time zone decision: CLOB timestamps are Unix seconds. We convert them
    to UTC and keep the UTC calendar date. yfinance daily bars are the
    exchange session date and have no clock time. We later join on that
    date. We do not shift the clock to US Eastern. A print just after
    00:00 UTC can therefore sit on the next date relative to the US close.
    That limit is stated in the report.
    """
    if series is None or len(series) == 0:
        return pandas.Series(dtype=float)
    utc = series.copy()
    utc.index = pandas.to_datetime(utc.index, utc=True)
    daily = utc.resample("1D").last().dropna()
    daily.index = daily.index.tz_convert("UTC").tz_localize(None).normalize()
    daily.name = "odds"
    return daily


# Why: correlation needs one row per shared date and no blanks.
def merge_series(left, right):
    """Align two series on dates, drop missing rows, and report how many remain."""
    if left is None or right is None or len(left) == 0 or len(right) == 0:
        empty = pandas.DataFrame(columns=["odds_change", "asset_return"])
        return empty, 0
    left_series = left.copy()
    right_series = right.copy()
    left_series.index = pandas.to_datetime(left_series.index).tz_localize(None).normalize()
    right_series.index = pandas.to_datetime(right_series.index).tz_localize(None).normalize()
    frame = pandas.DataFrame(
        {"odds_change": left_series, "asset_return": right_series}
    )
    frame = frame.dropna()
    return frame, int(len(frame))


# Why: the brief asks for a "first time" loop. This is that loop.
def first_cross_date(series, threshold):
    """Return the first date the series reaches the threshold. None if it never does."""
    first_date = None
    for date, value in series.items():
        if value >= threshold and first_date is None:
            first_date = date
    return first_date
