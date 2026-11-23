# Five parts of the project

Put one name on each part. That person explains that part of the code. Everyone should still be able to say what the project is testing and what the 21 November result was. The professor can ask a person about their own files in detail, and a short question about the result.

There are no classes. The code is variables, lists, dictionaries, for loops, if/elif/else, and functions.

## What everyone must be able to say

The question is: in past daily data, did the Polymarket Yes price move before gold (`GC=F`), the dollar index (`DX-Y.NYB`), or the Nasdaq (`^IXIC`)?

A positive lag means the odds moved first. Lag +2 means the change in the odds from two trading days earlier lines up with today's asset return. A negative lag means the asset moved first.

The markets are still open on purpose. The Yes price is still a probability. A closed market jumps to 0 or 1 when the outcome is filled in, and that jump is not a forecast. The meeting or the election being in the future is what we want. The test uses the past daily path of those still-open odds, up to 21 November 2026.

On 21 November 2026, 20:20 UTC, the run kept 5 Fed markets and 10 other events. That is 15 markets and 45 pairs. Every pair was `NO RELIABLE LEAD`. No pair was a lead, and no pair was too thin.

The strongest correlation was "Will the Fed increase interest rates by 50+ bps after the December 2026 meeting?" versus the Nasdaq: lag −4, correlation −0.438, 73 days, adjusted p-value 0.084. The lag is negative, so the odds did not lead.

The smallest adjusted p-value was "Will Jesus Christ return before 2027?" versus gold: 0.018, lag −1. That is below 0.05 and it is still not a lead, because the gold move lines up first.

Do not quote the 9 November figures (correlation 0.37, adjusted p 0.54, 66 days) as the current result. That was the same +25 bps December contract versus the Nasdaq, on a smaller 15-pair search. On 21 November that pair is lag +4, correlation 0.276, 76 days, adjusted p-value 1.000.

`python tests.py` printed 13 passed on 9 November. After three checks were added for the wider sample, it printed 16 passed, 0 failed. The README still records the 9 November count.

Telegram and Google Sheets do not affect the test. They only try to send the finished report. Both were left blank, so they were skipped.

---

## Person 1 — Downloading Polymarket and the three asset prices

**Files:** `config.py` (the tickers and the API settings), `polymarket.py`, `prices.py`.

**What you say you did:** You built the download step. You get the market questions and the daily Yes prices from Polymarket, and the daily gold, dollar, and Nasdaq prices from Yahoo Finance. If a download fails, you read the last saved file. You do not invent prices.

### The path through your code

`config.py` holds the three tickers: gold futures `GC=F`, the ICE dollar index `DX-Y.NYB`, and the Nasdaq Composite `^IXIC`. All three returned prices on 9 November and again on 21 November (344 prices, 343 returns).

`fetch_market_pages` calls `GET https://gamma-api.polymarket.com/markets`. Each request uses `limit=100`, `offset`, `order=volumeNum`, `ascending=false`, and `closed=false`. It loops for 8 pages, so at most 800 open markets, highest volume first. The list has no keyword argument, so the filtering happens later, in Person 2's code.

`fetch_event_pages` calls `GET https://gamma-api.polymarket.com/events` the same way, for 3 pages. The events list uses `order=volume`. It rejects `order=volumeNum`. That was checked live. Each event has a `markets` list. `markets_from_events` copies the parent event id onto those markets. If the events request fails, the wider sample falls back to non-keyword markets already in the market pages.

`parse_market` keeps `id`, `question`, `clobTokenIds`, `outcomes`, `volumeNum`, `liquidityNum`, `endDate`, `closed`, and the event id when the payload has one. `clobTokenIds` and `outcomes` arrive as JSON text. `parse_json_list` turns them into lists.

`yes_token_id` picks the token whose outcome is "Yes". If there is no Yes label, it uses the first token. The Yes price is the probability. A token id is the id of one outcome in the order book. It is not the market id.

`get_price_history` calls `GET https://clob.polymarket.com/prices-history` with `interval=all` and `fidelity=1440` (one day, in minutes). On 9 November, `interval=all` returned about a year for the largest Fed market. `interval=max` on the same token returned about a month. The saved file is `data/odds_<token>.csv`.

`download_prices` uses yfinance with `auto_adjust=True`, so Close is the adjusted close. New yfinance builds put the ticker in a second column level. `close_from_frame` handles that, and also a plain table, which is what the tests use. `to_returns` walks the prices in a loop. From 100 to 110 the return is `(110 - 100) / 100 * 100 = 10`. The lead test uses these percentage changes, not the price level. Saved files are `data/price_Gold.csv`, `data/price_Dollar.csv`, and `data/price_Nasdaq.csv`.

### Questions you should be ready for

**Why these three tickers?** They are the assets the project compares with the odds. They were checked with yfinance. No substitute was needed.

**Why only open markets?** `closed=false` is on the request. A resolved market's price jumps to 0 or 1. Person 2 also rejects any closed market that still gets through.

**Why is there no keyword on the API call?** The list-markets docs have no keyword argument. We download the high-volume pages and match the question text ourselves.

**Why `interval=all` and not `max`?** On the token we checked, `max` was only about a month. `all` with fidelity 1440 was about a year. The docs do not promise that for every market. An empty or failed history falls back to the CSV.

**What if the Wi-Fi dies during the talk?** The demo is on cached files. A failed request prints the error and reads `data/market_pages.json`, `data/event_pages.json`, or the odds CSV. It does not fill in a made-up price.

**What is volumeNum versus volume?** The market list sorts on `volumeNum`. The events list sorts on `volume`. Using `volumeNum` on the events URL returns a validation error.

---

## Person 2 — Deciding which markets get tested

**Files:** `filters.py`, and `collect_markets` plus `download_top_odds` in `main.py`. The keyword list and the quotas live in `config.py`: `MARKET_KEYWORDS`, `MIN_VOLUME`, `MIN_POINTS`, `MAX_SELECTED`, `MAX_EXTRA_SELECTED`, `MAX_CORE_DOWNLOADS`, `MAX_WIDER_DOWNLOADS`.

**What you say you did:** You decide which of the downloaded markets are allowed into the test. Fed-style markets are reserved. Other events are added beside them, one contract per event. Thin markets and closed markets are rejected, and every rejection has a written reason.

### The path through your code

`MARKET_KEYWORDS` is `Fed`, `rate cut`, `recession`, and `inflation`. `is_core_question` is true when one of those words is in the question. Those markets are tagged `core`. Everything else is `wider`.

`collect_markets` pages the markets and the events once, merges them by market id, and does not let a core market be overwritten into the wider pool. On 21 November that produced 97 core keyword markets and 323 wider headlines. It skipped 4,112 closed wider markets before downloading their history.

`is_liquid` returns true only when the market is open, volume is at least 100,000, and the daily history has at least 30 points. The conditions use `and`, `or`, and `not`. A closed market returns the reason "market is closed".

`rank_by_volume` is a best-so-far loop. It does not call `sort`. It walks the list, remembers the highest volume, takes that market, and repeats on what is left.

`headline_by_event` keeps the highest-volume market in each event. A market with no event id stands alone. One election can contain many outcomes. Taking all of them would fill the extra slots with one story. The Fed markets are not cut down this way. Several Fed questions can stay in the core together.

`select_markets` fills the core quota first, up to 5 (`MAX_SELECTED`), then the wider quota, up to 10 (`MAX_EXTRA_SELECTED`). A larger politics or crypto market cannot take a Fed slot. Odds are downloaded before this cut: up to 8 core names and 15 wider headlines. The liquidity rule needs the history, so the download cap is wider than the final quota.

The five core markets that were kept, highest volume first:

1. Will there be no change in Fed interest rates after the December 2026 meeting?
2. Will the Fed increase interest rates by 25 bps after the December 2026 meeting?
3. Will no Fed rate cuts happen in 2026?
4. Will the Fed decrease interest rates by 25 bps after the December 2026 meeting?
5. Will the Fed increase interest rates by 50+ bps after the December 2026 meeting?

The ten wider markets that were kept:

1. Will the U.S. invade Iran before 2027?
2. Will Jesus Christ return before 2027?
3. Will LeBron James win the 2028 US Presidential Election?
4. Will Oprah Winfrey win the 2028 Democratic presidential nomination?
5. Will China invade Taiwan by end of 2026?
6. Will the US confirm that aliens exist before 2027?
7. Will Shakhtar Donetsk win the 2026-27 UEFA Champions League Championship?
8. Will Byron Donalds win the 2028 Republican presidential nomination?
9. Will Trump acquire Greenland before 2027?
10. Will Benjamin Netanyahu be the next Prime Minister of Israel?

There were 88 questions containing "Fed". Only the five above were tested. Inflation markets and "US recession by end of 2026?" were in the keyword list and lost the download race to higher-volume Fed contracts. They were not tested. On 9 November, "inflation" had matched nothing in the top 800. On 21 November those questions were present and still outside the eight core downloads.

### Questions you should be ready for

**Why not test all 88 Fed markets?** The daily run is capped so it stays readable. The core quota is 5. The next Fed names were liquid and were rejected as "outside the core quota" or "outside the download limit".

**Why keep a smaller Fed market when a bigger non-Fed market is in the list?** The two quotas are separate. Core is filled first. That is `select_markets`. A test asserts that a lower-volume Fed market is kept beside a larger Bitcoin market.

**Why one wider market per event?** `headline_by_event`. A second contract from the same event is rejected with "another market in the same event has higher volume" when a different event is available. A test checks that.

**Why are the questions about things that have not happened yet?** Because we ask for open markets. The event is unresolved, so the price is still a probability. The comparison is still on past daily changes.

**Why include LeBron, Jesus, and a football club?** They are liquid open events outside the Fed keywords. They are a contrast. They are not expected to lead gold, the dollar, or the Nasdaq. They also came back `NO RELIABLE LEAD`, and several of them have 200 to 300 overlapping days, so the label is not from an empty sample.

**Why is 100,000 the volume cutoff?** Thin markets move on a few trades. A "lead" there would not be evidence. 30 days is the same cutoff the verdict uses for "enough overlap".

---

## Person 3 — Lining up the dates and running the lead-lag test

**Files:** `align.py`, `leadlag.py`. The lag and alpha settings are in `config.py`: `MAX_LAG = 5`, `ALPHA = 0.05`.

**What you say you did:** You put the odds changes and the asset returns on the same dates, search lags from −5 to +5, turn the best correlation into a p-value, correct for the search, and run Granger both ways.

### The path through your code

`resample_daily` keeps the last odds print of each UTC date. Polymarket timestamps are Unix seconds. Yahoo's daily bars are the exchange date and have no clock time. We join on the date. We do not shift the clock to US Eastern. A print just after midnight UTC can sit on the next date relative to the US close.

`odds_changes` is today's odds minus yesterday's odds. A move from 0.40 to 0.45 is +0.05. This is not a percentage. The asset side is a percentage, from Person 1. `merge_series` inner-joins them and drops missing rows. Weekends drop out because the asset has no return that day.

`cross_corr(x, y, lag)` correlates the odds after `shift(lag)` with the asset return. `shift(2)` puts the value from two days ago on today's row. If that lines up with today's return, the odds led by two days.

`best_lag` loops from −5 to +5. It keeps a lag when the absolute correlation is larger than the best so far. It does not use `argmax`.

`corr_pvalue` is a two-sided p-value from a t statistic. With correlation r and n observations, `t = r * sqrt((n - 2) / (1 - r^2))`, then `scipy.stats.t`.

`analyse_all` stores one dictionary per pair. The key is `(market question, asset name)`. This run has 45 pairs. It also searches 11 lags and keeps the winner, so the Bonferroni count is `45 * 11 = 495`. `bonferroni` multiplies each p-value by 495 and caps the result at 1. A raw p-value has to be smaller than about 0.0001 before the adjusted p-value falls below 0.05. That is why most adjusted p-values print as 1.000.

Core pairs also store `core_adjusted_p`, using only the 15 Fed pairs times 11 lags, which is 165. That number keeps the Fed slice comparable with the earlier five-market run. It does not decide the label. Person 4's verdict uses `adjusted_p`.

`granger_both_ways` calls `statsmodels.tsa.stattools.grangercausalitytests`. The library tests whether the second column helps forecast the first. For "odds lead the asset" the columns are asset, then odds. We keep the smallest p-value across lags 1 to 5. That minimum is easier to make look small than a test of one lag chosen in advance. statsmodels 0.15 no longer accepts `verbose`. A near-perfect lag can make the regression singular. That warning is ignored, and a failure returns p = 1.

`adf_pvalue` is the Augmented Dickey-Fuller test. A small p-value means the series does not look like a random walk. Granger is built for stationary series. We run it on changes, which are the right object, and we still print the ADF p-value. On the short December-versus-Nasdaq windows the asset ADF p-value was 0.493 or 0.787, so those return series did not look stationary. The verdict does not call them leads anyway.

### The numbers that come out of your test

Strongest absolute correlation: +50 bps or more, December 2026, versus Nasdaq. Lag −4, correlation −0.438, 73 days, adjusted p 0.084, core-only p 0.028, Granger forward 0.394, reverse 0.013, ADF asset 0.787.

Smallest adjusted p-value: Jesus Christ return before 2027 versus gold. Lag −1, correlation −0.265, 238 days, adjusted p 0.018, Granger forward 0.539, reverse about 0.

Fed pair with a positive lag and a moderate correlation: +25 bps, December 2026, versus Nasdaq. Lag +4, correlation 0.276, 76 days, adjusted p 1.000, Granger forward 0.134, ADF asset 0.493.

Dollar moving first: "Will no Fed rate cuts happen in 2026?" versus the dollar. Lag −1, correlation 0.196, 263 days, adjusted p 0.723, core-only p 0.241, reverse Granger 0.0015, forward 0.614.

A small Granger p-value that is still not a lead: Byron Donalds versus the Nasdaq. Lag +2, correlation 0.139, 319 days, Granger forward 0.004, adjusted p 1.000.

### Questions you should be ready for

**Why correct for the lags?** If you test 11 lags and quote the p-value of the winner, you will find "significant" correlations too often. A placebo check shuffles the odds away from the asset. Over 30 shuffles the raw best-lag false-lead rate was about 0.10. After multiplying by the 11 lags, that rate was 0.00.

**Why is alpha 0.05?** It is the cutoff in the brief. A p-value below it is treated as unlikely if there were truly no link. It is not a proof.

**Why did the +25 bps Nasdaq result change since 9 November?** Then it was correlation 0.37, adjusted p 0.54, 66 days, on 15 pairs. Now it is correlation 0.276, adjusted p 1.000, 76 days, and the correction covers 45 pairs. More days and a stricter correction. Do not mix the two.

**Why is adjusted p 0.018 not a lead?** Person 4 requires the lag to be positive. That pair's lag is −1. The reverse Granger p-value is about 0, so gold lines up first.

**Why is core-only p 0.028 not a lead?** The verdict ignores it. The full-sample p-value is 0.084. The lag is also −4, the reverse Granger test is stronger, and the Nasdaq ADF p-value on that window is 0.787.

**Why can Granger be 0.004 and the label still be no lead?** The Granger number is the smallest of five lags, and the label also needs the corrected correlation p-value below 0.05. On Byron Donalds versus the Nasdaq that corrected p-value is 1.000.

**What does shift(2) do?** It moves the odds change from two days ago onto today's row. Correlation with today's asset return is then the test of a two-day lead.

---

## Person 4 — The label, and the tests that the code is doing what it says

**Files:** `verdict.py`, `tests.py`. You also own the known-event note in `tests.py` (`known_event_report`) and the empty `KNOWN_EVENT` in `config.py`.

**What you say you did:** You turn one pair's numbers into a label a person can read, and you wrote the checks that fail if the parser, the filter, the lag, or the label is wrong.

### The path through your code

`make_verdict` is a straight if / elif / else.

`LEAD DETECTED` requires all of these:

- at least 30 overlapping days and the market passed the filter
- the best lag is positive
- `adjusted_p` is below 0.05
- Granger odds-to-asset p-value is below 0.05
- the reverse Granger p-value is not smaller than the forward one

Anything else with enough data is `NO RELIABLE LEAD`. Too little data, or a failed filter, is `DATA TOO THIN`.

`adjusted_p` is Person 3's full-sample figure. You do not look at `core_adjusted_p`.

`python tests.py` runs 16 checks. The three that were added for the wider sample are:

- a lower-volume Fed market is kept when a larger non-Fed market is present
- a second contract from the same event does not take another wider slot
- the full-sample adjusted p-value uses every pair, and the core-only p-value uses only the core pairs

The older checks:

- Parsing uses a made-up Gamma object and a made-up price history. It does not need the network.
- Filters use made-up markets: one liquid, one thin, one closed.
- Returns: 100 then 110 must give 10.
- Align uses three hand-written timestamps. The last print of the day is kept.
- Synthetic: the asset is the odds shifted by 2 plus tiny noise. `best_lag` must return 2.
- Reverse: the odds follow the asset by 2 days. The lag must be negative, and the verdict must not be `LEAD DETECTED`.
- Placebo: 30 shuffles. Raw false-lead rate about 0.10. After the 11-lag correction, about 0.00.
- Known event: an empty `KNOWN_EVENT` prints that the program does not invent one. A separate synthetic window checks that a filled dictionary prints dates and a lag.
- Calibration: two of three hand-made markets with odds from 60 to 80 percent resolve Yes, so the share is 2/3. The daily run does not download closed markets, so this check is not a live calibration.
- The report text contains the limits paragraph. Empty Telegram and Google secrets do not raise.

On 9 November the same file printed 13 passed, because those three wider-sample checks were not there yet. The README still says 13. The current file prints 16 passed, 0 failed.

`KNOWN_EVENT` is blank on purpose: name, date, the text to find in the question, the asset, and a window of 5 days are all empty strings. The program will not invent a Fed date or a surprise. The team can fill in one real past event later.

### Questions you should be ready for

**Why was every pair no reliable lead? Is the code broken?** The synthetic test builds a real two-day lead and the function returns lag 2. The reverse test refuses to call a lead. The 21 November labels are what those rules return on the real pairs. A lead needs every check at once. One small Granger p-value is not enough.

**Walk through the +50 bps Nasdaq pair.** Lag −4, so the first lead check fails. Adjusted p 0.084, so the p-value check fails too. Reverse Granger 0.013 is stronger than forward 0.394. Label: `NO RELIABLE LEAD`.

**Walk through Jesus versus gold.** Adjusted p 0.018 is below 0.05. Lag is −1, so it is not a lead. Reverse Granger is about 0. The asset lines up first.

**What is DATA TOO THIN?** Fewer than 30 overlapping days, or the market failed the liquidity filter. None of the 45 tested pairs got that label. The Champions League contract was the shortest wider series, at 91 days.

**Why is the calibration test not a live result?** It uses four hand-written rows. The daily path downloads open markets only, so we cannot yet say "odds of 70 percent resolved Yes 70 percent of the time."

**What if the professor says the README and the test count disagree?** The README sentence is dated 9 November: 13 passed. Three checks were added after that. The suite now has 16.

---

## Person 5 — The report, the demo page, and the daily run

**Files:** `report.py`, `demo_app.py`, and `run` / `load_analysis` in `main.py`.

**What you say you did:** You wire the steps into one run, write the charts and `output/report.txt`, and build the Streamlit page the talk uses. You also added the optional Telegram and Google Sheet delivery, which is skipped when the secrets are blank.

### The path through your code

`load_analysis` is the pipeline the page and the command line share. There is no second copy of the statistics in the demo.

The order in `run` is: collect markets, download the capped odds histories, select the two quotas, download the three asset prices over the odds window, run `analyse_all`, label each pair, write the outputs, then try to deliver.

`write_outputs` saves three kinds of pictures under `output/`: a bar chart of correlation by lag for each pair, one overlay of odds and the asset for the pair with the largest absolute correlation, and a verdict table. It also writes `report.txt`. The overlay on this run is the +50 bps December market versus the Nasdaq.

The report tags each kept market `core` or `wider`. For a core pair it also prints the core-only adjusted p-value and says that number does not change the verdict.

`demo_app.py` is `streamlit run demo_app.py`. The sidebar starts on cached files. "Fetch live" is a button, so opening the page does not call the API by itself. `st.session_state` stores the results on the first load, so changing the market dropdown does not run Granger again. The lag buttons only highlight a lag that was already computed. Dark blue on the chart is the best lag. Orange is the lag you picked when it is different. The verdict box is green for a lead, amber for no reliable lead, and red for too thin.

The page currently shows 15 markets kept, 45 pairs, 0 leads, 0 too thin. The table has a group column.

`send_telegram` posts the report text if `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set. The text is cut at 4,000 characters. `append_sheet` appends one row per pair: date, group, market, asset, verdict, lag, overlapping days. Either failure is printed and swallowed. On this machine both were empty, so both printed "skipped". They are not part of the lead-lag test.

A daily run can be Task Scheduler on Windows, or cron at 07:10: `cd` into this folder and run `python main.py`. `--offline` never calls the network.

### Questions you should be ready for

**Why Streamlit?** It turns the same functions into a page you can click through. The calculation stays in the other files. If the room Wi-Fi fails, cached files still open.

**Show me one pair.** Open a core market against the Nasdaq, read the best lag, the correlation, the days, and the adjusted p-value. Click another lag. The verdict does not change. Then open a wider market and say the group column is `wider`.

**Does the demo recompute when I change the dropdown?** No. The bundle is stored in `st.session_state` on the first load.

**Why Telegram and Sheets?** They are a second copy of a report that has already been written to disk. Blank secrets are skipped. A failed send does not change a label.

**What can this run not say?** It cannot say prediction markets do not work. It is daily, open contracts, three assets, and leads of at most five trading days. It cannot see a lead inside the same day. It is not the whole Polymarket catalog. It does not use closed markets. It is not causation and not a forecast.

**Where is the written result?** `output/report.txt`, run time 2026-11-21 20:20 UTC. The price window is 2025-07-14 to 2026-11-23.

---

## If the professor asks the wrong person

Give the short answer, then point at the person who owns the file.

| Question | Short answer | Owner |
| --- | --- | --- |
| Where do the odds come from? | Polymarket Yes price, daily, cached if the call fails. | Person 1 |
| Why these five Fed markets? | Highest volume among the liquid core names. The quota is 5. | Person 2 |
| Why a positive lag? | `shift` puts an older odds change on today's asset return. | Person 3 |
| Why is p = 0.018 not a lead? | The lag is negative. The label needs the odds to move first. | Person 4 |
| Why 16 tests and the README says 13? | README is the 9 November run. Three wider-sample checks were added later. | Person 4 |
| What does the page show? | 15 markets, 45 pairs, 0 leads, cached files. | Person 5 |

## One sentence each person can use to start

1. I download the Polymarket odds and the gold, dollar, and Nasdaq prices, and I fall back to the saved file if the request fails.
2. I choose the five Fed markets and the ten other events, and I reject closed, thin, and duplicate contracts with a written reason.
3. I line the series up by date, search lags from minus five to plus five, and correct the p-value because we searched.
4. I turn those numbers into one of three labels, and the tests check that a real lead is found and a reverse lead is not.
5. I write the report and the demo page from those labels, and the page shows 15 markets, 45 pairs, and no lead.
