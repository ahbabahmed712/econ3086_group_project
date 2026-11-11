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


# Why: the core quota is reserved for the Fed-style questions in config.
def is_core_question(question):
    """True when the question contains one of the core keywords."""
    text = str(question or "").lower()
    for keyword in config.MARKET_KEYWORDS:
        if keyword.lower() in text:
            return True
    return False


def market_group(market):
    """Return 'core' or 'wider'. A missing tag is decided from the question text."""
    group = market.get("group")
    if group == "core" or group == "wider":
        return group
    if is_core_question(market.get("question") or ""):
        return "core"
    return "wider"


# Why: one election can contain many contracts. The wider quota should be events, not outcomes.
def headline_by_event(markets):
    """Keep the highest-volume market for each event. No event id means the market stands alone."""
    best = {}
    order = []
    dropped = []
    for market in markets:
        event_id = str(market.get("event_id") or "")
        if event_id == "":
            key = "market:" + str(market.get("market_id"))
        else:
            key = "event:" + event_id
        current = best.get(key)
        if current is None:
            best[key] = market
            order.append(key)
            continue
        if (market.get("volume") or 0) > (current.get("volume") or 0):
            dropped.append(current)
            best[key] = market
        else:
            dropped.append(market)
    kept = []
    for key in order:
        kept.append(best[key])
    return kept, dropped


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


def _fill_quota(ranked, limit, reason, chosen, rejected):
    """Append up to limit markets. The rest are rejected with reason."""
    kept = 0
    for market in ranked:
        if kept < limit:
            chosen.append(market)
            kept = kept + 1
        else:
            rejected.append({"question": market.get("question", ""), "reason": reason})
    return kept


# Why: the core quota is filled first, then other events. A big crypto market cannot take a Fed slot.
def select_markets(markets):
    """Keep up to 5 liquid core markets and up to 10 liquid wider headlines."""
    rejected = []
    core_liquid = []
    wider_liquid = []
    for market in markets:
        ok, reason = is_liquid(market, config.MIN_VOLUME, config.MIN_POINTS)
        if not ok:
            rejected.append({"question": market.get("question", ""), "reason": reason})
            continue
        group = market_group(market)
        market["group"] = group
        if group == "core":
            core_liquid.append(market)
        else:
            wider_liquid.append(market)
    headlines, dropped = headline_by_event(wider_liquid)
    for market in dropped:
        rejected.append(
            {
                "question": market.get("question", ""),
                "reason": "liquid, but another market in the same event has higher volume",
            }
        )
    chosen = []
    _fill_quota(
        rank_by_volume(core_liquid),
        config.MAX_SELECTED,
        "liquid, but outside the core quota",
        chosen,
        rejected,
    )
    _fill_quota(
        rank_by_volume(headlines),
        config.MAX_EXTRA_SELECTED,
        "liquid, but outside the wider quota",
        chosen,
        rejected,
    )
    return chosen, rejected
