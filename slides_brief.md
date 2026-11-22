# Slide brief: ECON3086 prediction-market lead-lag monitor

Give this file to the agent building the slides. Use only the numbers in this file. Do not invent markets, correlations, or dates.

The audience is a professor and classmates. Use plain sentences. The talk is a historical check. It is not investment advice and it does not prove causation.

Two runs are recorded below. The 21 November 2026 run is the current result. It includes the Fed core and the wider events. The 9 November 2026 run is the earlier Fed-only result. Where the same pair appears in both, use the 21 November numbers for the current claim and mention 9 November only as the earlier, smaller search.

Source of the current numbers: `output/report.txt`, run time 2026-11-21 20:20 UTC. Price window: 2025-07-14 to 2026-11-23. Gold, the dollar index, and the Nasdaq each returned 344 prices and 343 returns.

## Project in one sentence

In past daily data, did Polymarket odds move before gold futures (`GC=F`), the US dollar index (`DX-Y.NYB`), or the Nasdaq Composite (`^IXIC`)?

A positive lag means the odds moved first. Lag +2 means the odds change from two trading days earlier lines up with today's asset return. A negative lag means the asset moved first.

## What was built

Ordinary Python: variables, lists, dictionaries, loops, if/elif/else, and functions. No classes.

- `python main.py` downloads Polymarket and Yahoo Finance, writes `data/`, and writes charts plus `output/report.txt`.
- `python main.py --offline` uses saved files only.
- `python tests.py` checks the code. After the wider-sample changes it printed 16 passed, 0 failed.
- `streamlit run demo_app.py` is the talk page. It calls the same functions as the command line. Start on cached files. Fetch live only for a fresh download.
- Telegram and Google Sheets are optional. A blank token or sheet id is skipped. The program keeps going.

## How a run chooses markets

1. Download the highest-volume open markets, 8 pages of 100, from the Polymarket markets list. That list has no keyword search, so the program reads the question text.
2. Download the highest-volume open events, 3 pages. Each event contains markets. Events are ordered by `volume`. Markets are ordered by `volumeNum`.
3. **Core:** questions containing Fed, rate cut, recession, or inflation. Up to 5 are tested. They are reserved, so a larger politics or crypto market cannot push them out.
4. **Wider:** other liquid open events, one headline contract per event, up to 10 more. One election can contain many outcomes. Taking every outcome would fill the extra slots with one story.
5. A market is kept only if it is open, volume is at least 100,000, and the daily odds history has at least 30 points. Closed markets are left out because the jump to resolution would sit in the series.
6. The Yes price is the probability. Daily spacing is 1,440 minutes. The last print of each UTC date is kept.
7. Gold, the dollar, and the Nasdaq are turned into percentage changes. A move from 100 to 110 is a 10 percent return. The test uses changes, not price levels.
8. The series are joined on the date. Weekends drop out because the asset has no return that day.
9. Every kept market is tested against every asset at lags from −5 to +5 trading days. The lag with the largest absolute correlation is kept.

On this run the catalog had 97 core keyword markets and 323 wider headlines. 4,112 closed wider markets were skipped. The test itself used 15 markets and 45 pairs.

## The three labels

`LEAD DETECTED` requires all of these:

- the best lag is positive
- the correlation p-value, after a Bonferroni correction across every kept pair and all 11 lags, is below 0.05
- a Granger test says the odds help forecast the asset
- the reverse Granger test is not stronger
- there are at least 30 overlapping days and the market passed the liquidity filter

Anything else with enough data is `NO RELIABLE LEAD`. Too little data is `DATA TOO THIN`.

This run has 45 pairs and 11 lags, so the correction multiplies by 495 tests. A raw p-value has to be smaller than about 0.0001 before the adjusted p-value falls below 0.05. That is why most adjusted p-values print as 1.000.

Core markets also print a core-only adjusted p-value, using only the 15 Fed pairs times 11 lags (165 tests). That number is for comparison with the earlier Fed-only run. It does not decide the label.

Alpha is 0.05 because that is the cutoff in the brief. A p-value below it is treated as unlikely if there were truly no link. It is not a proof.

The Granger p-value in the report is the smallest across lags 1 to 5, so it is easier to look small than a test of one lag chosen in advance. Granger is run on changes. The Augmented Dickey-Fuller p-value is printed because Granger is built for series that do not wander like a random walk.

A placebo check shuffles the odds away from the asset. Over 30 shuffles, the raw best-lag false-lead rate was about 0.10. After correcting for the 11 lags, that rate was 0.00.

A synthetic series where the asset really is the odds shifted by 2 days must return lag +2. A series where the odds follow the asset must return a negative lag and must not be labelled `LEAD DETECTED`.

## Current result, 21 November 2026

15 markets, 3 assets, 45 pairs. Every pair is `NO RELIABLE LEAD`. No pair is `LEAD DETECTED`. No pair is `DATA TOO THIN`.

The strongest absolute correlation in the whole sample is still a Fed market, and the lag is negative: the December 2026 "+50 bps or more" contract versus the Nasdaq, lag −4, correlation −0.438, 73 days. The odds did not lead.

### Core markets kept

| Market | Volume | Daily odds points |
| --- | ---: | ---: |
| Will there be no change in Fed interest rates after the December 2026 meeting? | 12,780,737 | 109 |
| Will the Fed increase interest rates by 25 bps after the December 2026 meeting? | 11,089,711 | 108 |
| Will no Fed rate cuts happen in 2026? | 9,785,046 | 383 |
| Will the Fed decrease interest rates by 25 bps after the December 2026 meeting? | 8,732,831 | 104 |
| Will the Fed increase interest rates by 50+ bps after the December 2026 meeting? | 8,651,846 | 104 |

Inflation markets and "US recession by end of 2026?" were in the keyword list. They lost the core download race to these higher-volume Fed contracts, so they were not tested. On 9 November, "inflation" had matched nothing in the top 800. On 21 November those inflation questions are present, and they are still outside the eight core downloads.

### Wider markets kept

One headline contract from each event. These are the ten highest-volume headlines that also cleared volume and history.

| Market | Volume | Daily odds points | What it is |
| --- | ---: | ---: | --- |
| Will the U.S. invade Iran before 2027? | 81,033,288 | 375 | geopolitics |
| Will Jesus Christ return before 2027? | 69,772,389 | 344 | long-shot belief |
| Will LeBron James win the 2028 US Presidential Election? | 55,189,674 | 460 | election long shot |
| Will Oprah Winfrey win the 2028 Democratic presidential nomination? | 54,733,911 | 470 | election long shot |
| Will China invade Taiwan by end of 2026? | 47,326,366 | 458 | geopolitics |
| Will the US confirm that aliens exist before 2027? | 47,162,531 | 329 | long-shot belief |
| Will Shakhtar Donetsk win the 2026-27 UEFA Champions League Championship? | 46,495,916 | 129 | sport |
| Will Byron Donalds win the 2028 Republican presidential nomination? | 44,989,093 | 461 | election |
| Will Trump acquire Greenland before 2027? | 36,106,785 | 306 | politics |
| Will Benjamin Netanyahu be the next Prime Minister of Israel? | 35,691,003 | 337 | politics |

Next wider names that were liquid but outside the quota of 10: Richard Grenell as leader of Venezuela at the end of 2026, the Iranian regime falling before 2027, Putin out by 31 December 2026, the Clarity Act signed in 2026, and a hantavirus pandemic in 2026. They were not tested.

### Core pair results

Every row is `NO RELIABLE LEAD`. "Core-only p" does not decide the label. "Forward" is Granger odds-to-asset. "Reverse" is Granger asset-to-odds.

| Market | Asset | Lag | Corr | Days | Adjusted p | Core-only p | Forward | Reverse | ADF asset |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No change, December 2026 meeting | Gold | −5 | −0.290 | 76 | 1.000 | 1.000 | 0.055 | 0.063 | 0.001 |
| No change, December 2026 meeting | Dollar | +1 | −0.198 | 76 | 1.000 | 1.000 | 0.049 | 0.171 | 0.000 |
| No change, December 2026 meeting | Nasdaq | +4 | −0.221 | 76 | 1.000 | 1.000 | 0.188 | 0.492 | 0.493 |
| +25 bps, December 2026 meeting | Gold | −5 | 0.278 | 76 | 1.000 | 1.000 | 0.074 | 0.074 | 0.001 |
| +25 bps, December 2026 meeting | Dollar | +1 | 0.230 | 76 | 1.000 | 1.000 | 0.044 | 0.098 | 0.000 |
| +25 bps, December 2026 meeting | Nasdaq | +4 | 0.276 | 76 | 1.000 | 1.000 | 0.134 | 0.613 | 0.493 |
| No Fed rate cuts in 2026 | Gold | −3 | 0.116 | 263 | 1.000 | 1.000 | 0.202 | 0.074 | 0.000 |
| No Fed rate cuts in 2026 | Dollar | −1 | 0.196 | 263 | 0.723 | 0.241 | 0.614 | 0.002 | 0.000 |
| No Fed rate cuts in 2026 | Nasdaq | −1 | −0.106 | 263 | 1.000 | 1.000 | 0.859 | 0.087 | 0.000 |
| −25 bps, December 2026 meeting | Gold | −5 | −0.220 | 73 | 1.000 | 1.000 | 0.137 | 0.124 | 0.003 |
| −25 bps, December 2026 meeting | Dollar | +1 | −0.203 | 73 | 1.000 | 1.000 | 0.084 | 0.366 | 0.006 |
| −25 bps, December 2026 meeting | Nasdaq | −3 | 0.164 | 73 | 1.000 | 1.000 | 0.215 | 0.190 | 0.787 |
| +50 bps or more, December 2026 meeting | Gold | +5 | −0.267 | 73 | 1.000 | 1.000 | 0.053 | 0.274 | 0.003 |
| +50 bps or more, December 2026 meeting | Dollar | −2 | −0.279 | 73 | 1.000 | 1.000 | 0.541 | 0.078 | 0.006 |
| +50 bps or more, December 2026 meeting | Nasdaq | −4 | −0.438 | 73 | 0.084 | 0.028 | 0.394 | 0.013 | 0.787 |

### Wider pair results

Every row is `NO RELIABLE LEAD`. Wider markets have no core-only p-value.

| Market | Asset | Lag | Corr | Days | Adjusted p | Forward | Reverse |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| U.S. invade Iran before 2027 | Gold | −3 | 0.141 | 259 | 1.000 | 0.825 | 0.027 |
| U.S. invade Iran before 2027 | Dollar | −1 | 0.185 | 259 | 1.000 | 0.285 | 0.003 |
| U.S. invade Iran before 2027 | Nasdaq | −1 | −0.163 | 259 | 1.000 | 0.372 | 0.001 |
| Jesus Christ return before 2027 | Gold | −1 | −0.265 | 238 | 0.018 | 0.539 | 0.000 |
| Jesus Christ return before 2027 | Dollar | −4 | −0.164 | 238 | 1.000 | 0.577 | 0.026 |
| Jesus Christ return before 2027 | Nasdaq | +1 | −0.088 | 238 | 1.000 | 0.157 | 0.801 |
| LeBron James, 2028 election | Gold | −1 | 0.210 | 318 | 0.085 | 0.220 | 0.000 |
| LeBron James, 2028 election | Dollar | +2 | −0.150 | 318 | 1.000 | 0.029 | 0.147 |
| LeBron James, 2028 election | Nasdaq | −4 | −0.080 | 318 | 1.000 | 0.376 | 0.361 |
| Oprah Winfrey, 2028 Democratic nomination | Gold | +3 | 0.128 | 327 | 1.000 | 0.060 | 0.096 |
| Oprah Winfrey, 2028 Democratic nomination | Dollar | +2 | −0.170 | 327 | 1.000 | 0.007 | 0.029 |
| Oprah Winfrey, 2028 Democratic nomination | Nasdaq | 0 | −0.118 | 327 | 1.000 | 0.099 | 0.381 |
| China invade Taiwan by end of 2026 | Gold | +1 | −0.092 | 316 | 1.000 | 0.102 | 0.609 |
| China invade Taiwan by end of 2026 | Dollar | −2 | −0.067 | 316 | 1.000 | 0.418 | 0.418 |
| China invade Taiwan by end of 2026 | Nasdaq | +2 | −0.077 | 316 | 1.000 | 0.342 | 0.323 |
| US confirm aliens exist before 2027 | Gold | −2 | 0.120 | 226 | 1.000 | 0.423 | 0.147 |
| US confirm aliens exist before 2027 | Dollar | +5 | −0.141 | 226 | 1.000 | 0.309 | 0.282 |
| US confirm aliens exist before 2027 | Nasdaq | +2 | 0.105 | 226 | 1.000 | 0.102 | 0.748 |
| Shakhtar Donetsk, 2026-27 Champions League | Gold | +5 | −0.156 | 91 | 1.000 | 0.046 | 0.114 |
| Shakhtar Donetsk, 2026-27 Champions League | Dollar | −3 | −0.094 | 91 | 1.000 | 0.261 | 0.172 |
| Shakhtar Donetsk, 2026-27 Champions League | Nasdaq | −1 | −0.098 | 91 | 1.000 | 0.801 | 0.063 |
| Byron Donalds, 2028 Republican nomination | Gold | 0 | 0.135 | 319 | 1.000 | 0.125 | 0.439 |
| Byron Donalds, 2028 Republican nomination | Dollar | −4 | −0.092 | 319 | 1.000 | 0.194 | 0.423 |
| Byron Donalds, 2028 Republican nomination | Nasdaq | +2 | 0.139 | 319 | 1.000 | 0.004 | 0.513 |
| Trump acquire Greenland before 2027 | Gold | +4 | −0.125 | 210 | 1.000 | 0.141 | 0.307 |
| Trump acquire Greenland before 2027 | Dollar | +3 | 0.138 | 210 | 1.000 | 0.025 | 0.067 |
| Trump acquire Greenland before 2027 | Nasdaq | −2 | 0.128 | 210 | 1.000 | 0.953 | 0.131 |
| Netanyahu next Prime Minister of Israel | Gold | −3 | 0.095 | 232 | 1.000 | 0.442 | 0.491 |
| Netanyahu next Prime Minister of Israel | Dollar | +3 | −0.205 | 232 | 0.914 | 0.004 | 0.371 |
| Netanyahu next Prime Minister of Israel | Nasdaq | +1 | −0.117 | 232 | 1.000 | 0.077 | 0.223 |

## What those numbers mean

**No reliable daily lead in this sample.** Across 5 Fed markets and 10 other liquid events, and across gold, the dollar, and the Nasdaq, no pair passed every lead check.

**The closest correlation is the asset side, not the odds.** "+50 bps or more" after the December 2026 meeting versus the Nasdaq: lag −4, correlation −0.438, 73 days. Full-sample adjusted p-value 0.084. Core-only adjusted p-value 0.028. The core-only figure is below 0.05, and it still does not make a lead. The lag is negative, the reverse Granger p-value (0.013) is smaller than the forward p-value (0.394), and the Nasdaq returns in that 73-day window do not look stationary (ADF p-value 0.787). The full-sample adjusted p-value, which is the one the verdict uses, is 0.084.

**The December +25 bps market versus the Nasdaq is the Fed pair with a positive lag and a moderate correlation.** Lag +4, correlation 0.276, 76 days, adjusted p-value 1.000, Granger forward 0.134. The Nasdaq returns in that window have ADF p-value 0.493. This is the same contract that was the closest pair on 9 November. It is still not a lead. See the earlier-run section for the old numbers.

**"No Fed rate cuts in 2026" versus the dollar still lines up with the dollar moving first.** Lag −1, correlation 0.196, 263 days. Full-sample adjusted p-value 0.723. Core-only adjusted p-value 0.241. Reverse Granger p-value 0.0015. Forward Granger p-value 0.614. The dollar moved with, or before, those odds.

**The smallest adjusted p-value in the whole 45-pair search is not a lead.** "Will Jesus Christ return before 2027?" versus gold: lag −1, correlation −0.265, 238 days, adjusted p-value 0.018, Granger forward 0.539, reverse about 0.000. The p-value is below 0.05 and the lag is negative, so the gold return lined up before the odds. The reverse Granger test agrees. This is the useful contrast in the wider sample: a liquid contract that is not a Fed question can show a tight statistical alignment, and that alignment can run from the asset toward the odds.

**A small Granger p-value by itself is not a lead.** Examples that stay `NO RELIABLE LEAD` because the corrected correlation p-value is large:

- Byron Donalds versus the Nasdaq: lag +2, correlation 0.139, 319 days, Granger forward 0.004, adjusted p-value 1.000.
- Netanyahu versus the dollar: lag +3, correlation −0.205, 232 days, Granger forward 0.004, adjusted p-value 0.914.
- Oprah Winfrey versus the dollar: lag +2, correlation −0.170, 327 days, Granger forward 0.007, reverse 0.029, adjusted p-value 1.000.
- LeBron James versus the dollar: lag +2, correlation −0.150, 318 days, Granger forward 0.029, adjusted p-value 1.000.

**The wider events do not show a cleaner lead than the Fed markets.** Iran, Taiwan, Greenland, the election long shots, the Champions League contract, and the aliens contract are all `NO RELIABLE LEAD` against all three assets. Several of the long geopolitics and election series have 200 to 300 overlapping days, so the "no lead" label is not an empty-sample label. The Champions League contract is the short one in the wider set, at 91 days, and it still clears the 30-day minimum.

**Several short December Fed windows fail the stationarity check on the Nasdaq.** No-change, +25 bps, −25 bps, and +50 bps versus the Nasdaq have asset ADF p-values of 0.493 or 0.787. The longer "no cuts in 2026" Nasdaq window has ADF p-value 0.000. The verdict does not treat the short Nasdaq windows as leads anyway.

## Earlier result, 9 November 2026

This was the Fed-only run, before the wider events were added. Five open Fed markets, three assets, 15 pairs. Every pair was `NO RELIABLE LEAD`.

- Closest pair then: "Will the Fed increase interest rates by 25 bps after the December 2026 meeting?" versus the Nasdaq. Lag +4, correlation 0.37, 66 overlapping days, adjusted p-value 0.54. Granger odds-to-asset p-value 0.005. ADF p-value on the Nasdaq returns 0.24.
- Longer Fed markets then had about 250 overlapping trading days.
- "Will no Fed rate cuts happen in 2026?" versus the dollar had a negative lag. Reverse Granger p-value about 0.001.
- The word "inflation" matched nothing in the top 800 open markets that day. One recession market was found and was below the download cutoff.

On 21 November the same +25 bps versus Nasdaq pair is lag +4, correlation 0.276, 76 days, adjusted p-value 1.000. Two things changed. The overlap grew from 66 days to 76, and the correction now covers 45 pairs instead of 15. Do not quote 0.37 or 0.54 as the current result.

## What the slides may say

The 21 November sample, five Fed markets plus ten other liquid events, did not show a reliable daily lead of at most five trading days into gold, the dollar, or the Nasdaq.

Also fair to say:

- The sample is one historical path.
- The long series have about 200 to 330 overlapping trading days. The December meeting contracts have about 73 to 76.
- Thin markets are easy to push around. These tested markets are not thin: the volume cutoff is 100,000, and the kept contracts have volumes in the millions.
- One late swing does not say prediction markets fail in general.
- Sports, election long shots, and belief markets were included on purpose. They are liquid, and they are a contrast to the Fed contracts. They also show no reliable lead.
- Polymarket prints are labelled in UTC. Yahoo bars are the exchange date and have no clock time. A print just after midnight UTC can sit on the next date relative to the US close.
- A daily last print cannot see a lead inside the same day.
- The sample is still open markets from the paged lists. It is not the whole catalog. Closed markets stay out.
- `KNOWN_EVENT` is blank on purpose. The program will not invent a Fed date or a surprise.

## What the slides must not say

- That prediction markets do not work.
- That the odds caused the asset prices, or that anyone should trade.
- That any pair was a lead. None was.
- That the Jesus-versus-gold adjusted p-value of 0.018 is a lead. The lag is −1.
- That the +50 bps versus Nasdaq core-only p-value of 0.028 is a lead. The verdict uses 0.084, the lag is −4, and the reverse Granger test is stronger.
- That a Granger p-value of 0.004, or 0.007, is a lead by itself.
- That the 9 November figures (correlation 0.37, adjusted p 0.54, 66 days) are the current December-versus-Nasdaq result.
- That inflation and recession were tested on 21 November. They were found and then left out by the download cap.
- That the program looked inside the same day, or at closed markets, or at the whole Polymarket catalog.
- That Telegram or Google Sheets were checked on this machine. They were left blank and skipped.

## Suggested slides

1. Title. Prediction-market lead-lag monitor. ECON3086. Did Polymarket odds move before gold, the dollar, or the Nasdaq?
2. Question. Positive lag means odds moved first. Negative lag means the asset moved first. Historical check, not a trading rule.
3. Data. Polymarket Yes prices, daily. Gold futures, dollar index, Nasdaq. Open markets only. Volume at least 100,000 and at least 30 daily points.
4. Sample. Core: 5 Fed markets. Wider: 10 other events, one contract each. Name Iran, Taiwan, Greenland, and one election or sport contract so the wider set is visible. 15 markets, 45 pairs.
5. Method. Odds change and asset return, lags −5 to +5, correlation, Bonferroni across 495 tests, Granger both ways, then one of three labels.
6. Result. 21 November 2026. All 45 pairs: `NO RELIABLE LEAD`.
7. Strongest correlation. +50 bps or more versus the Nasdaq: lag −4, correlation −0.438, adjusted p 0.084, core-only p 0.028, 73 days. Not a lead, because the lag is negative and the reverse test is stronger.
8. The trap in the wider sample. Jesus Christ return versus gold: adjusted p 0.018, lag −1, reverse Granger about 0. A small p-value with a negative lag means the asset lined up first.
9. Fed pair people will remember. +25 bps versus the Nasdaq: lag +4, correlation 0.276, 76 days, adjusted p 1.000. The 9 November version of this pair was correlation 0.37 and adjusted p 0.54 on 15 pairs. Say the current search is the larger one.
10. Dollar before the odds. No Fed rate cuts in 2026 versus the dollar: lag −1, 263 days, reverse Granger 0.0015.
11. Why a small Granger p-value is not enough. Byron Donalds versus the Nasdaq, Granger forward 0.004, adjusted correlation p-value 1.000.
12. Limits. Not causation. Not the whole catalog. Not intraday. Not closed markets. Not a forecast. Inflation and recession were in the catalog and were not in the tested five.

## Demo, about two minutes

Open the Streamlit page on cached files. The 21 November cache is what `python main.py` just wrote.

Point at 15 markets and 45 pairs, and at zero leads. Open the +50 bps December market against the Nasdaq and read lag −4, correlation −0.438, adjusted p 0.084. Then open "Will Jesus Christ return before 2027?" against gold and read adjusted p 0.018 with lag −1. Say the verdict does not change when a different lag button is clicked. The dropdown does not rerun the tests.

## Answers if the professor asks

**Did you prove prediction markets do not work?** No. The check is daily, open contracts, three assets, and leads of at most five trading days. The wider set adds politics, geopolitics, sport, and long-shot contracts. It is still not the whole catalog.

**Why these three assets?** They are the series the project tests, and all three downloaded. On 21 November each returned 344 prices.

**Why the Yes price?** The questions are Yes/No. The Yes price is the probability.

**Why reject closed markets?** The monitor is about markets still trading. The jump to 0 or 1 at resolution would mix into the series. This run skipped 4,112 closed wider markets.

**Why is alpha 0.05?** It is the cutoff in the brief.

**Why is the Jesus-versus-gold p-value below 0.05 and still not a lead?** The best lag is −1. A lead requires the odds to move first. The reverse Granger p-value is about 0, so the gold side is the one that lines up first.

**Why is the core-only p-value 0.028 on the +50 bps Nasdaq pair and the label still no lead?** The verdict uses the full-sample adjusted p-value, 0.084. The lag is also −4, the reverse Granger test is stronger, and the short Nasdaq return series has ADF p-value 0.787.

**Why can Granger be 0.004 when the label is still no reliable lead?** The label also needs a corrected correlation p-value below 0.05. On Byron Donalds versus the Nasdaq that corrected p-value is 1.000. The Granger figure is the smallest across five lags, so it is the easier number to make look small.

**What happened to the 9 November result of correlation 0.37 and p 0.54?** That was the same +25 bps December contract versus the Nasdaq, on 66 days, with a correction across 15 pairs. The 21 November overlap is 76 days and the correction is across 45 pairs. The current numbers are lag +4, correlation 0.276, adjusted p 1.000.

**What is a token id?** The id of one outcome in the order book. It is not the market id.

**What if the API fails during the talk?** The page is on cached files. The pipeline prints the error and reads the last saved file. It does not invent prices.

## Numbers to copy exactly

Current run, 2026-11-21 20:20 UTC:

- 15 markets, 45 pairs, every pair `NO RELIABLE LEAD`
- Correction: 45 pairs times 11 lags = 495 tests
- Core-only correction, not used for the label: 15 pairs times 11 lags = 165 tests
- Strongest correlation: +50 bps or more, December 2026, versus Nasdaq. Lag −4, correlation −0.438, 73 days, adjusted p 0.084, core-only p 0.028, Granger forward 0.394, reverse 0.013, ADF asset 0.787
- Smallest adjusted p-value: Jesus Christ return before 2027 versus gold. Lag −1, correlation −0.265, 238 days, adjusted p 0.018, Granger forward 0.539, reverse about 0
- +25 bps, December 2026, versus Nasdaq: lag +4, correlation 0.276, 76 days, adjusted p 1.000, Granger forward 0.134, ADF asset 0.493
- No Fed rate cuts in 2026 versus the dollar: lag −1, correlation 0.196, 263 days, adjusted p 0.723, core-only p 0.241, reverse Granger 0.0015
- Byron Donalds versus Nasdaq: lag +2, correlation 0.139, 319 days, Granger forward 0.004, adjusted p 1.000

Earlier run, 9 November 2026, Fed only:

- 15 pairs, every pair `NO RELIABLE LEAD`
- +25 bps versus Nasdaq then: lag +4, correlation 0.37, 66 days, adjusted p 0.54, Granger 0.005, ADF asset 0.24
- Placebo over 30 shuffles: raw false-lead rate about 0.10, about 0.00 after the 11-lag correction

Thresholds: volume 100,000, 30 daily points, max lag 5, alpha 0.05. Quotas: up to 5 core markets and up to 10 wider events.
