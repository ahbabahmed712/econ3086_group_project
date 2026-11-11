# Visual demo page. It calls the same pipeline as main.py.
# Cached files are the default so the presentation still works if the API is down.

import matplotlib.pyplot as plt
import pandas
import streamlit as st

import config
from main import load_analysis, strongest_key
from report import LIMITS_TEXT, make_lag_figure, make_overlay_figure


# Why: changing a dropdown should not recompute every Granger test.
def get_bundle(offline):
    """Return the analysis for this data source. Compute it once per page session."""
    key = "cached_bundle" if offline else "live_bundle"
    if key not in st.session_state:
        st.session_state[key] = load_analysis(offline=offline)
    return st.session_state[key]


def market_by_name(chosen, question):
    """Find the selected market dictionary. Return None if the name is missing."""
    for market in chosen:
        if market.get("question") == question:
            return market
    return None


def correlation_at(profile, lag):
    """Read the correlation the program already stored for one lag."""
    for row in profile:
        if row["lag"] == lag:
            return row["corr"]
    return 0.0


def show_verdict(label):
    """Colour the verdict so the audience can see it from the back of the room."""
    if label == "LEAD DETECTED":
        st.success(label)
    elif label == "DATA TOO THIN":
        st.error(label)
    else:
        st.warning(label)


def show_pair(bundle, question, asset_name, selected_lag):
    """Draw the numbers and charts for one market-asset pair."""
    result = bundle["results"].get((question, asset_name))
    if result is None:
        st.write("This pair is not in the results.")
        return
    show_verdict(result["verdict"])
    st.write(result["reason"])
    lag_col, corr_col, n_col, p_col = st.columns(4)
    lag_col.metric("Best lag (days)", result["best_lag"])
    corr_col.metric("Correlation", f"{result['corr']:.3f}")
    n_col.metric("Overlapping days", result["n_obs"])
    p_col.metric("Adjusted p-value", f"{result['adjusted_p']:.3f}")
    core_p = result.get("core_adjusted_p")
    if result.get("group") == "core" and core_p is not None:
        st.caption(
            f"Group: core. Full-sample adjusted p is {result['adjusted_p']:.3f} and decides the verdict. "
            f"Core-only adjusted p is {core_p:.3f}. That uses only the Fed-style pairs."
        )
    elif result.get("group"):
        st.caption(f"Group: {result.get('group')}. The verdict uses the full-sample adjusted p-value.")
    picked = correlation_at(result["lag_profile"], selected_lag)
    st.caption(
        f"Highlighted lag {selected_lag}: correlation {picked:.3f}. "
        f"Dark blue is the best lag ({result['best_lag']}). "
        "Orange is the lag you picked, when it is different."
    )
    left, right = st.columns(2)
    lag_fig = make_lag_figure(asset_name, result["lag_profile"], result["best_lag"], selected_lag)
    with left:
        st.pyplot(lag_fig)
    plt.close(lag_fig)
    market = market_by_name(bundle["chosen"], question)
    prices = bundle["price_levels"].get(asset_name)
    odds = None if market is None else market.get("daily_odds")
    title = f"{question[:70]} vs {asset_name}"
    overlay = make_overlay_figure(odds, prices, title)
    with right:
        st.pyplot(overlay)
    plt.close(overlay)
    st.write(
        f"Granger odds-to-asset p = {result['granger_odds_to_asset_p']:.4f}. "
        f"Reverse p = {result['granger_asset_to_odds_p']:.4f}. "
        f"ADF odds p = {result['adf_odds_p']:.3f}. "
        f"ADF asset p = {result['adf_asset_p']:.3f}."
    )


def main():
    """Build the page: summary table, then one pair the speaker can click through."""
    st.set_page_config(page_title="Lead-lag monitor", layout="wide")
    st.title("Did Polymarket odds move first?")
    st.write(
        "Core Fed, rate-cut, recession and inflation markets, plus other liquid Polymarket events, "
        "versus gold, the dollar index and the Nasdaq. "
        "A positive lag means the odds moved first. This is not investment advice."
    )
    source = st.sidebar.radio(
        "Data source",
        ["Cached files (use this in the demo)", "Fetch live"],
    )
    offline = source.startswith("Cached")
    if not offline:
        st.sidebar.warning("Live mode calls Polymarket and Yahoo. Use cached files if the room Wi-Fi fails.")
        if st.sidebar.button("Fetch live data"):
            st.session_state["live_bundle"] = load_analysis(offline=False)
        if "live_bundle" not in st.session_state:
            st.info("Press 'Fetch live data', or switch back to cached files.")
            return
    with st.spinner("Loading the lead-lag results..."):
        bundle = get_bundle(offline)
    rows = bundle["verdict_rows"]
    if len(rows) == 0:
        st.error("No pairs to show. Run python main.py once so the cache exists, then reload this page.")
        return
    lead_count = 0
    thin_count = 0
    for row in rows:
        if row["verdict"] == "LEAD DETECTED":
            lead_count = lead_count + 1
        if row["verdict"] == "DATA TOO THIN":
            thin_count = thin_count + 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Markets kept", len(bundle["chosen"]))
    c2.metric("Pairs tested", len(rows))
    c3.metric("Leads detected", lead_count)
    c4.metric("Too thin", thin_count)
    table = pandas.DataFrame(rows)
    table["corr"] = table["corr"].round(3)
    table["adjusted_p"] = table["adjusted_p"].round(3)
    if "core_adjusted_p" not in table.columns:
        table["core_adjusted_p"] = pandas.NA
    table["core_adjusted_p"] = pandas.to_numeric(table["core_adjusted_p"], errors="coerce").round(3)
    if "group" not in table.columns:
        table["group"] = ""
    show_cols = ["group", "market", "asset", "verdict", "lag", "corr", "n_obs", "adjusted_p", "core_adjusted_p"]
    st.dataframe(table[show_cols], width="stretch", hide_index=True)
    questions = []
    for market in bundle["chosen"]:
        questions.append(market["question"])
    default_key = strongest_key(bundle["results"])
    default_q = questions[0]
    default_asset = "Gold"
    if default_key is not None:
        default_q = default_key[0]
        default_asset = default_key[1]
    st.subheader("Look at one pair")
    question = st.selectbox("Market", questions, index=questions.index(default_q))
    asset_name = st.selectbox("Asset", list(config.ASSETS.keys()), index=list(config.ASSETS.keys()).index(default_asset))
    lag_choices = list(range(-config.MAX_LAG, config.MAX_LAG + 1))
    selected_lag = st.radio(
        "Lag to highlight",
        lag_choices,
        index=lag_choices.index(0),
        horizontal=True,
    )
    show_pair(bundle, question, asset_name, selected_lag)
    with st.expander("Markets that were rejected"):
        if len(bundle["rejected"]) == 0:
            st.write("None.")
        for item in bundle["rejected"]:
            st.write(f"{item.get('question', '')}: {item.get('reason', '')}")
    with st.expander("What this tool cannot tell you"):
        st.write(LIMITS_TEXT)


if __name__ == "__main__":
    main()
