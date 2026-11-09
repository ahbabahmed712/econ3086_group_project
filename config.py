# Settings for the lead-lag monitor. Plain variables and dictionaries only.

import os

# Folder that contains this file. Every other path is built from here.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Yahoo Finance tickers. Checked on 9 Nov 2026: all three returned prices.
# Gold is the front gold futures contract. Dollar is the ICE dollar index.
# Nasdaq is the Nasdaq Composite index.
ASSETS = {"Gold": "GC=F", "Dollar": "DX-Y.NYB", "Nasdaq": "^IXIC"}

# Words we look for in the Polymarket question text.
MARKET_KEYWORDS = ["Fed", "rate cut", "recession", "inflation"]

# A market must clear both hurdles before we test it.
MIN_VOLUME = 100000
MIN_POINTS = 30

# How many trading days of lead or lag we search. Positive means odds lead.
MAX_LAG = 5

# A p-value below this is treated as statistically noticeable.
ALPHA = 0.05

# The test is run on daily changes, not on intraday prints.
FREQUENCY = "daily"

# Gamma GET /markets has no keyword argument, so we page through the
# highest-volume open markets and filter the question text ourselves.
# Docs: https://docs.polymarket.com/api-reference/markets/list-markets
MARKET_PAGE_SIZE = 100
MAX_MARKET_PAGES = 8

# How many high-volume names we download odds for. Keeps the demo short.
MAX_DOWNLOADS = 8

# At most this many markets go into the lead-lag test.
MAX_SELECTED = 5

# CLOB price history. Docs: https://docs.polymarket.com/api-reference/markets/get-prices-history
# interval is one of max, all, 1m, 1w, 1d, 6h, 1h. fidelity is in minutes.
# Live check on 9 Nov 2026: interval=all and fidelity=1440 returned about a year
# of points. interval=max on the same token returned only about one month.
PRICE_HISTORY_INTERVAL = "all"
PRICE_HISTORY_FIDELITY = 1440

REQUEST_TIMEOUT = 30

# The team fills this in with a real past event. Empty strings mean "not chosen".
# This program does not invent the event name, the date, or the surprise.
KNOWN_EVENT = {
    "name": "",
    "date": "",
    "market_question_contains": "",
    "asset_name": "",
    "window_days": 5,
}
