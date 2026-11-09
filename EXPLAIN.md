# How to explain this project

Read this before the demo. Each section says what the file does, then answers questions a professor is likely to ask. The code is ordinary Python: variables, lists, dictionaries, for loops, if/elif/else, and functions. There are no classes.

## What the program is testing

A positive lag means the odds moved first. Lag +2 means the odds change from two trading days earlier lines up with today's asset return. A negative lag means the asset moved first. The label `LEAD DETECTED` is used only when all of these are true:

- the best lag is positive
- the correlation p-value, after a Bonferroni correction, is below 0.05
- a Granger test says the odds help forecast the asset
- the reverse Granger test is not stronger
- there are at least 30 overlapping days and the market passed the liquidity filter

Anything else with enough data is `NO RELIABLE LEAD`. Too little data is `DATA TOO THIN`.

On 9 Nov 2026 every tested pair was `NO RELIABLE LEAD`. That is a real result, not a broken run.

## config.py

This file only holds settings: asset tickers, keywords, the minimum volume (100,000), the minimum number of daily odds points (30), the maximum lag (5), alpha (0.05), and how many market pages to download.

`KNOWN_EVENT` is blank on purpose. The team fills in a real past event. The program will not invent a Fed date or a surprise.

**Why these tickers?** They were downloaded with yfinance on 9 Nov 2026. `GC=F` (gold futures), `DX-Y.NYB` (dollar index) and `^IXIC` (Nasdaq Composite) all returned rows. No substitute was needed.

**Why is alpha 0.05?** It is the cutoff in the brief. A p-value below it is treated as unlikely if there were truly no link. It is not a proof.

## polymarket.py

`fetch_market_pages` calls `GET https://gamma-api.polymarket.com/markets` in a for loop. Each request uses `limit`, `offset`, `order=volumeNum`, `ascending=false` and `closed=false`. Those parameters are in the official list-markets docs. The live response is a list. The fields we keep are `id`, `question`, `clobTokenIds`, `outcomes`, `volumeNum`, `liquidityNum`, `endDate` and `closed`.

The list endpoint has no keyword argument. That was checked in the docs. `find_markets` therefore keeps a market only when the keyword appears in the question. We stop after 8 pages (800 markets). A full catalog scan would be slow, and offset paging is capped.

`clobTokenIds` and `outcomes` arrive as JSON text, not as Python lists. `parse_json_list` turns them into lists. On the markets checked live, the first outcome was "Yes" and the first token was the Yes token. We use the Yes token because the question is a Yes/No question and the Yes price is the probability.

`get_price_history` calls `GET https://clob.polymarket.com/prices-history`. The docs say `market` is required, and `interval` is one of `max`, `all`, `1m`, `1w`, `1d`, `6h`, `1h`. `fidelity` is the spacing in minutes. We send `interval=all` and `fidelity=1440` (one day). A live check on 9 Nov 2026 returned points from about 30 Sep 2025 through 9 Nov 2026 for the largest Fed market. The same token with `interval=max` returned only about one month. The docs do not promise that `all` plus `1440` works for every market. If a call fails or comes back empty, the function prints the error and reads `data/odds_<token>.csv`.

**What is a token id?** It is the long id of one outcome in the order book. It is not the market id.

**What if the request fails?** `try/except` prints a clear line and uses the cache. It does not invent prices.

## filters.py

`is_liquid` returns true only when the market is open and volume is at least `MIN_VOLUME` and the daily history is at least `MIN_POINTS`. The conditions use `and`, `or` and `not`.

`rank_by_volume` is a best-so-far loop. It walks the list, remembers the highest volume seen so far, takes that market, then repeats on what is left. `select_markets` keeps at most five liquid markets and records a reason for every rejection.

**Why reject closed markets?** A live monitor is about markets that are still trading. Closed markets would mix the resolution jump into the series.

## prices.py

`download_prices` uses yfinance with `auto_adjust=True`, so `Close` is the adjusted close. New yfinance builds put the ticker in a second column level. `close_from_frame` handles that and also a plain table, which is what the tests use.

`to_returns` walks the prices with a for loop. The step from 100 to 110 is `(110 - 100) / 100 * 100 = 10`. The lead test uses these percentage changes, not the price level. Empty downloads and failed downloads fall back to `data/price_<name>.csv`.

## align.py

`resample_daily` keeps the last odds print of each UTC date. Polymarket timestamps are Unix seconds. We label them in UTC. Yahoo's daily bars are the exchange date and have no clock time. We join on the date. We do not shift to US Eastern. A print just after midnight UTC can sit on the next date relative to the US close. That is a limit, and it is written in the function comment.

`odds_changes` is the first difference: today's odds minus yesterday's odds. `merge_series` inner-joins the two series and drops missing rows, then reports how many rows remain. Weekends drop out because the asset has no return that day.

`first_cross_date` is the "first time" loop. It remembers the first date the odds reach a threshold, and it does not replace that date later. The daily run prints the first date each selected market reached 50 percent.

## leadlag.py

`cross_corr(x, y, lag)` correlates the odds series after `shift(lag)` with the asset return. `shift(2)` puts the value from two days ago on today's row. If that lines up with today's return, the odds led by two days.

`best_lag` loops from `-MAX_LAG` to `+MAX_LAG`. It keeps a lag only when the absolute correlation is larger than the best so far. It does not use `argmax`.

`corr_pvalue` turns a correlation into a two-sided p-value with a t statistic and `scipy.stats.t`. With n observations and correlation r, the statistic is `r * sqrt((n - 2) / (1 - r^2))`.

`granger_both_ways` calls `statsmodels.tsa.stattools.grangercausalitytests`. The library tests whether the second column helps forecast the first. For "odds lead the asset" the columns are asset, then odds. We keep the smallest p-value across lags 1 to 5. That minimum is easier to make look small than a test of one lag chosen in advance. The report says so. statsmodels 0.15 no longer accepts `verbose`. A near-perfect lag can make the regression singular; that warning is ignored, and a failure returns p = 1.

`adf_pvalue` is the Augmented Dickey-Fuller test. A small p-value means the series does not look like a random walk. Granger is built for stationary series. We run it on changes, which are the right object, and we still print the ADF p-value. On 9 Nov 2026 the December-meeting market versus the Nasdaq had an asset ADF p-value of 0.24, so that shorter return series did not look stationary. The verdict does not treat that pair as a lead anyway.

`bonferroni` multiplies each p-value by the number of tests and caps the result at 1. `analyse_all` stores one dictionary per pair. The key is `(market question, asset name)`. The number of tests is the number of pairs times the number of lags (11 when max lag is 5), because the lag was chosen by searching.

**Why correct for the lags?** If you test 11 lags and then quote the p-value of the winner, you will find "significant" correlations too often. The placebo test shows the raw rate. Over 30 shuffles it was about 0.10, above alpha. After multiplying by the 11 lags, the false-lead rate in that run was 0.00.

## verdict.py

`make_verdict` is a straight if / elif / else. Thin data, then a lead, otherwise no reliable lead. The tests assert one hand-built result for each label.

## tests.py

`python tests.py` runs every check.

- Parsing uses a made-up Gamma object and a made-up price-history payload. It does not need the network.
- Filters use made-up markets.
- Returns: 100 then 110 must give 10.
- Align uses three hand-written timestamps.
- Synthetic: the asset is the odds shifted by 2 plus tiny noise. `best_lag` must return 2.
- Reverse: the odds follow the asset by 2 days. The lag must be negative, and the verdict must not be `LEAD DETECTED`.
- Placebo: the odds are shifted by a large random amount. The printed rates are the point of the test.
- Known event: an empty `KNOWN_EVENT` prints that the program does not invent one. A separate synthetic window checks that a filled dictionary prints dates and a lag.
- Calibration: hand-made resolved rows. Two of three markets with odds from 60 to 80 percent resolve Yes, so the share is 2/3. The daily run does not download closed markets, so this check is not claiming a live calibration.

## report.py and main.py

`report.py` writes three kinds of pictures to `output/`: a bar chart of correlation by lag for each pair, an overlay of odds and the asset for the pair with the largest absolute correlation, and a verdict table. It also writes `report.txt` with f-strings.

Telegram uses `POST https://api.telegram.org/bot<token>/sendMessage`. Google Sheets uses `gspread` if a credentials file and a sheet id are in `.env`. Either failure is printed and swallowed.

`main.py` is the pipeline: page the markets, keep keyword matches, download the eight highest-volume odds histories, filter to five, download the three asset prices over the odds window, run the tests, write the report, try to send it. `--offline` never calls the network.

## What this run can and cannot say

Checked live on 9 Nov 2026:

- Five markets, three assets, fifteen pairs. All fifteen: `NO RELIABLE LEAD`.
- The long markets have about 250 overlapping trading days. The December 2026 meeting market has 66 or 67.
- The strongest correlation was +4 days, correlation 0.37, on that shorter Nasdaq pair. Adjusted p-value 0.54. Granger odds-to-asset p-value 0.005, but the Nasdaq returns in that window did not pass the stationarity check (ADF p = 0.24). We do not call it a lead.
- "Will no Fed rate cuts happen in 2026?" versus the dollar had a negative lag. The Granger test in the reverse direction was very small (p about 0.001). That says the dollar moved with, or before, those odds. It is not evidence that the odds led.

Cannot say:

- That prediction markets do not work. We only looked at daily Fed-related contracts in the top volume pages, against three assets, for leads of at most five trading days.
- That there is no link inside the same day. A daily last print cannot see an hourly lead.
- A live calibration of resolved markets. The daily path downloads open markets only.
- That Telegram or Google Sheets work on this machine. No token and no sheet were configured, so those steps were skipped on purpose.
