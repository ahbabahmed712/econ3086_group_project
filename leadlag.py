# Cross-correlation, best lag, and Granger tests for one market against each asset.

import math
import warnings

import pandas
import scipy.stats
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

import config
from align import merge_series


# Why: a positive lag means yesterday's odds line up with today's asset move.
def cross_corr(x, y, lag):
    """Correlation between odds shifted by lag and the asset return."""
    paired = pandas.DataFrame({"x": x.shift(lag), "y": y}).dropna()
    if len(paired) < 3:
        return 0.0
    value = paired["x"].corr(paired["y"])
    if value != value:
        return 0.0
    return float(value)


# Why: the best lag is chosen with an explicit best-so-far loop, not argmax.
def best_lag(x, y, max_lag):
    """Search lags from -max_lag to +max_lag. Return (lag, correlation)."""
    best_lag_value = 0
    best_corr = 0.0
    started = False
    for lag in range(-max_lag, max_lag + 1):
        corr = cross_corr(x, y, lag)
        if (not started) or abs(corr) > abs(best_corr):
            started = True
            best_lag_value = lag
            best_corr = corr
    return best_lag_value, best_corr


# Why: a correlation of 0.3 on 20 days is not the same evidence as on 200 days.
def corr_pvalue(r, n):
    """Two-sided p-value for a Pearson correlation, using scipy's t distribution."""
    if n is None or n <= 2:
        return 1.0
    if r != r:
        return 1.0
    if abs(r) >= 0.999999:
        return 0.0
    t_stat = r * math.sqrt((n - 2) / (1.0 - r * r))
    p_value = scipy.stats.t.sf(abs(t_stat), df=n - 2) * 2
    return float(p_value)


# Why: we test many pairs. Bonferroni stops one lucky pair from looking special.
def bonferroni(p_values, n_tests):
    """Multiply each p-value by the number of tests. Cap the result at 1."""
    adjusted = []
    tests = n_tests
    if tests < 1:
        tests = 1
    for p_value in p_values:
        value = p_value * tests
        if value > 1:
            value = 1.0
        adjusted.append(float(value))
    return adjusted


# Why: Granger assumes the series do not wander like a random walk. We record the check.
def adf_pvalue(series):
    """Augmented Dickey-Fuller p-value. A small p-value means the series looks stationary."""
    clean = series.dropna()
    if len(clean) < 10:
        return 1.0
    try:
        # result_object=False keeps the old tuple, so result[1] is the p-value.
        result = adfuller(clean, autolag="AIC", result_object=False)
    except (ValueError, RuntimeError):
        return 1.0
    return float(result[1])


# Why: statsmodels wants columns [effect, cause]. We take the smallest p-value across lags.
def _granger_min_p(effect, cause, max_lag):
    """Smallest Granger p-value for 'cause helps forecast effect'. 1.0 if it cannot run."""
    frame = pandas.concat([effect, cause], axis=1).dropna()
    if len(frame) < max_lag + 5:
        return 1.0
    frame.columns = ["effect", "cause"]
    try:
        # statsmodels 0.15 has no verbose argument. A near-perfect lag can make
        # the regression singular; the warning is not a crash, so we hide it.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = grangercausalitytests(frame, maxlag=max_lag)
    except (ValueError, RuntimeError):
        return 1.0
    best_p = 1.0
    for lag in result:
        p_value = result[lag][0]["ssr_ftest"][1]
        if p_value < best_p:
            best_p = float(p_value)
    return best_p


# Why: a lead claim needs odds to help forecast the asset, not the other way around.
def granger_both_ways(x, y, max_lag):
    """Return (odds_to_asset_p, asset_to_odds_p). x is odds changes, y is returns."""
    forward = _granger_min_p(y, x, max_lag)
    backward = _granger_min_p(x, y, max_lag)
    return forward, backward


def _lag_profile(x, y, max_lag):
    """Correlation at every lag, for the bar chart."""
    profile = []
    for lag in range(-max_lag, max_lag + 1):
        profile.append({"lag": lag, "corr": cross_corr(x, y, lag)})
    return profile


def _one_pair(market, asset_name, asset_returns):
    """Statistics for one market and one asset. This is one dictionary entry."""
    frame, n_obs = merge_series(market.get("odds_change"), asset_returns)
    x = frame["odds_change"] if n_obs > 0 else pandas.Series(dtype=float)
    y = frame["asset_return"] if n_obs > 0 else pandas.Series(dtype=float)
    lag, corr = best_lag(x, y, config.MAX_LAG)
    overlap = len(pandas.DataFrame({"x": x.shift(lag), "y": y}).dropna())
    p_value = corr_pvalue(corr, overlap)
    forward, backward = granger_both_ways(x, y, config.MAX_LAG)
    result = {
        "best_lag": lag,
        "corr": corr,
        "p_value": p_value,
        "adjusted_p": p_value,
        "granger_odds_to_asset_p": forward,
        "granger_asset_to_odds_p": backward,
        "n_obs": n_obs,
        "adf_odds_p": adf_pvalue(x),
        "adf_asset_p": adf_pvalue(y),
        "passed_filter": True,
        "lag_profile": _lag_profile(x, y, config.MAX_LAG),
    }
    return result


# Why: every pair is stored under (market name, asset name), as the brief requires.
def analyse_all(markets, assets):
    """Test every market against every asset. Then Bonferroni-adjust the correlation p-values."""
    results = {}
    keys = []
    p_values = []
    for market in markets:
        market_name = market.get("question", "")
        for asset_name in assets:
            key = (market_name, asset_name)
            result = _one_pair(market, asset_name, assets[asset_name])
            results[key] = result
            keys.append(key)
            p_values.append(result["p_value"])
    # Each pair looks at every lag and keeps the strongest correlation.
    # Counting only the pairs would make that search look more significant than it is.
    n_lags = config.MAX_LAG * 2 + 1
    n_tests = len(p_values) * n_lags
    adjusted = bonferroni(p_values, n_tests)
    for index, key in enumerate(keys):
        results[key]["adjusted_p"] = adjusted[index]
    return results
