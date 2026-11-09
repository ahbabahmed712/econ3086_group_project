# Prediction-market lead-lag monitor

Course project for ECON3086. The program asks a narrow question: in past daily data, did Polymarket odds on Fed, rate-cut, recession or inflation markets move before gold, the US dollar index, or the Nasdaq?

It does not prove that odds cause prices, and it is not investment advice.

## Setup

Python 3.10 or newer.

```text
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, use `cp .env.example .env`. Leave the Telegram and Google values blank unless you want delivery. Blank values are skipped. The program does not crash.

## Run

From this folder:

```text
python main.py
python main.py --offline
python tests.py
```

The first command calls Polymarket and Yahoo Finance, writes CSV files under `data/`, and writes charts plus `output/report.txt`. The offline command uses those files only. `tests.py` prints PASS or FAIL for each check. On 9 Nov 2026 it printed `13 passed, 0 failed`.

A full online run on that date finished in well under three minutes.

## Example result (9 Nov 2026)

Five open Fed markets were tested against gold (`GC=F`), the dollar index (`DX-Y.NYB`) and the Nasdaq Composite (`^IXIC`). All three tickers returned prices.

Every pair was labelled **NO RELIABLE LEAD**.

The closest pair was "Will the Fed increase interest rates by 25 bps after the December 2026 meeting?" against the Nasdaq: best lag +4 trading days, correlation 0.37, 66 overlapping days. The correlation p-value, after correcting for the pairs and the lags that were searched, was 0.54. That is not below 0.05, so it is not called a lead. The long Fed markets had about 250 overlapping trading days. That is enough to see a moderate daily link. It is still one historical path.

The word "inflation" matched nothing in the top 800 open markets by volume. One recession market was found and was below the download cutoff.

## Daily schedule

Windows Task Scheduler, once a day, action:

```text
Program: python
Arguments: main.py
Start in: the folder that contains main.py
```

A cron line on macOS or Linux, running at 07:10, looks like this:

```text
10 7 * * * cd /path/to/this/folder && python main.py
```

## Limits

Odds leading prices in a past sample is not causation and not a forecast. Thin markets are easy to push around. A late swing in one contract does not say that prediction markets fail in general. Details are in `output/report.txt` and in `EXPLAIN.md`.
