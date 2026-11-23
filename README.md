# Prediction-market lead-lag monitor

Course project for ECON3086. The program asks a narrow question: in past daily data, did Polymarket odds move before gold, the US dollar index, or the Nasdaq? The core sample is still Fed, rate-cut, recession and inflation markets. On top of that, the run keeps other liquid open events, such as politics or crypto, one headline contract per event.

It does not prove that odds cause prices, and it is not investment advice.

## Setup

Python 3.10 or newer.

```text
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, use `cp .env.example .env`. Leave the Telegram and Google values blank unless you want delivery. Blank values are skipped. The program does not crash.

## Telegram and Google Sheets

These copy a report that is already written to `output/report.txt`. Fill `.env`, then run `python main.py --offline` or, if that report already exists, `python main.py --deliver`.

Telegram:

1. In Telegram, open `@BotFather`, send `/newbot`, and copy the token into `TELEGRAM_BOT_TOKEN`.
2. Send any message to that new bot.
3. Open `https://api.telegram.org/bot<token>/getUpdates` and copy the `chat.id` number into `TELEGRAM_CHAT_ID`.

Google Sheets:

1. In Google Cloud, create a project and turn on the Google Sheets API.
2. Create a service account and download its JSON key. Save the file as `google-credentials.json` in this folder. Do not commit it.
3. Create a spreadsheet and share it with the service-account email as an Editor.
4. Copy the long id from the sheet URL (`/d/<id>/edit`) into `GOOGLE_SHEET_ID`.
5. Set `GOOGLE_CREDENTIALS_FILE=google-credentials.json`.

The first row of an empty sheet is `date, group, market, asset, verdict, lag, n_obs`. Each later row is one market-asset pair. Telegram gets a short count of leads, not the full report. The full text stays in `output/report.txt`.

## Run

From this folder:

```text
python main.py
python main.py --offline
python tests.py
streamlit run demo_app.py
```

`demo_app.py` is the live-demo page. It opens in the browser. Leave the sidebar on **Cached files** so the talk still works if the Wi-Fi or the API fails. Use the market box, the asset box, and the lag buttons to walk through one pair. Choose **Fetch live** only when you want a fresh download.

The first command calls Polymarket and Yahoo Finance, writes CSV files under `data/`, and writes charts plus `output/report.txt`. The offline command uses those files only. `tests.py` prints PASS or FAIL for each check. On 9 Nov 2026 it printed `13 passed, 0 failed`.

A full online run on that date finished in well under three minutes.

## Example result (9 Nov 2026)

That run, before the wider sample, tested five open Fed markets against gold (`GC=F`), the dollar index (`DX-Y.NYB`) and the Nasdaq Composite (`^IXIC`). All three tickers returned prices. A current run still keeps up to five of those core markets, then adds up to ten other liquid events.

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

Odds leading prices in a past sample is not causation and not a forecast. Thin markets are easy to push around. A late swing in one contract does not say that prediction markets fail in general. The wider sample is still only the paged open events, not the whole catalog. Details are in `output/report.txt` and in `EXPLAIN.md`.
