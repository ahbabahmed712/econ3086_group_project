# Turn one pair's numbers into a label a person can read.

import config


# Why: the program must not call a lead unless every check agrees.
def make_verdict(result):
    """Return (verdict, one-line reason) using if/elif/else."""
    n_obs = result.get("n_obs") or 0
    passed = result.get("passed_filter", True)
    lag = result.get("best_lag") or 0
    adjusted = result.get("adjusted_p")
    if adjusted is None:
        adjusted = 1.0
    forward = result.get("granger_odds_to_asset_p")
    if forward is None:
        forward = 1.0
    backward = result.get("granger_asset_to_odds_p")
    if backward is None:
        backward = 1.0
    lead_ok = lag > 0 and adjusted < config.ALPHA and forward < config.ALPHA
    reverse_stronger = backward < forward
    if n_obs < config.MIN_POINTS or not passed:
        reason = (
            f"Only {n_obs} overlapping observations "
            f"(minimum is {config.MIN_POINTS}), or the market failed the filter."
        )
        return "DATA TOO THIN", reason
    elif lead_ok and not reverse_stronger:
        reason = (
            f"Best lag is +{lag} day(s), adjusted p={adjusted:.4f}, "
            f"and Granger odds-to-asset p={forward:.4f}."
        )
        return "LEAD DETECTED", reason
    else:
        reason = (
            f"Best lag is {lag}, adjusted p={adjusted:.4f}, "
            f"Granger forward p={forward:.4f}, reverse p={backward:.4f}."
        )
        return "NO RELIABLE LEAD", reason
