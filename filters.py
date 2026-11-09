# Decide which markets are liquid enough to test, and which to reject.

import config


# Why: thin markets move on a few trades, so a "lead" there is not evidence.
def is_liquid(market, min_volume, min_points):
    """Return (True/False, reason). Uses and/or/not so the rule is visible."""
    volume = market.get("volume") or 0
    points = market.get("n_points") or 0
    closed = bool(market.get("closed"))
    volume_ok = volume >= min_volume
    points_ok = points >= min_points
    is_open = not closed
    if is_open and volume_ok and points_ok:
        return True, "volume and history both clear the minimum"
    if not is_open:
        return False, "market is closed"
    if (not volume_ok) and (not points_ok):
        return False, "volume is low and history is short"
    if not volume_ok or not points_ok:
        if not volume_ok:
            return False, "volume is below the minimum"
        return False, "not enough odds observations"
    return False, "rejected"


# Why: the marker wants a visible best-so-far loop, not a sort helper.
def rank_by_volume(markets):
    """Order markets from highest volume to lowest using a best-so-far loop."""
    pool = []
    for market in markets:
        pool.append(market)
    ranked = []
    while len(pool) > 0:
        best = None
        best_volume = None
        for market in pool:
            volume = market.get("volume") or 0
            if best is None or volume > best_volume:
                best = market
                best_volume = volume
        ranked.append(best)
        remaining = []
        for market in pool:
            if market.get("market_id") != best.get("market_id"):
                remaining.append(market)
        pool = remaining
    return ranked


# Why: we only want a handful of markets so the daily run stays short and readable.
def select_markets(markets):
    """Keep the 3 to 5 most liquid markets. Also return every rejection and its reason."""
    rejected = []
    liquid = []
    for market in markets:
        ok, reason = is_liquid(market, config.MIN_VOLUME, config.MIN_POINTS)
        if ok:
            liquid.append(market)
        else:
            rejected.append({"question": market.get("question", ""), "reason": reason})
    ranked = rank_by_volume(liquid)
    chosen = []
    for market in ranked:
        if len(chosen) < config.MAX_SELECTED:
            chosen.append(market)
        else:
            rejected.append(
                {
                    "question": market.get("question", ""),
                    "reason": "liquid, but outside the top 5 by volume",
                }
            )
    return chosen, rejected
