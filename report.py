# Charts, a text report, and optional Telegram or Google Sheet delivery.

import os
import time
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from dotenv import load_dotenv

import config

load_dotenv(os.path.join(config.BASE_DIR, ".env"))

LIMITS_TEXT = (
    "This tool shows whether odds led prices in past data. "
    "It does not prove causation, does not predict markets and is not investment advice. "
    "Thin markets are noisy and easy to move. "
    "A small sample can miss a real lead or invent one. "
    "Past results may not hold in the future. "
    "A single late swing in one market does not prove that prediction markets "
    "are unreliable in general."
)


# Why: the chart has to show every lag, with the chosen lag easy to see.
def make_lag_figure(asset_name, profile, best_lag, selected_lag=None):
    """Bar chart of correlation at each lag. Dark blue is the best lag."""
    labels = []
    values = []
    colors = []
    for row in profile:
        labels.append(str(row["lag"]))
        values.append(row["corr"])
        if row["lag"] == best_lag:
            colors.append("#1f4e79")
        elif selected_lag is not None and row["lag"] == selected_lag:
            colors.append("#b85c38")
        else:
            colors.append("#8fadc8")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Lag in trading days (positive means odds lead)")
    ax.set_ylabel("Correlation")
    ax.set_title(f"{asset_name}: best lag {best_lag}")
    fig.tight_layout()
    return fig


# Why: main.py still needs a PNG on disk. The demo page uses the figure itself.
def save_lag_chart(market_name, asset_name, profile, best_lag, path):
    """Save the lag chart. market_name is kept so older calls stay the same."""
    fig = make_lag_figure(asset_name, profile, best_lag)
    fig.savefig(path)
    plt.close(fig)


# Why: a person should be able to look at the two series, not only at a p-value.
def make_overlay_figure(odds, prices, title):
    """Plot daily odds and the asset price on two scales. Returns the figure."""
    fig, ax_left = plt.subplots(figsize=(9, 4))
    ax_right = ax_left.twinx()
    if odds is not None and len(odds) > 0:
        ax_left.plot(list(odds.index), list(odds.values), color="#1f4e79", label="Odds")
    if prices is not None and len(prices) > 0:
        ax_right.plot(list(prices.index), list(prices.values), color="#b85c38", label="Asset")
    ax_left.set_ylabel("Odds (Yes price)")
    ax_right.set_ylabel("Asset price")
    ax_left.set_title(title)
    fig.tight_layout()
    return fig


def save_overlay(odds, prices, title, path):
    """Save the odds-versus-price chart to path."""
    fig = make_overlay_figure(odds, prices, title)
    fig.savefig(path)
    plt.close(fig)


# Why: the demo needs one picture that lists every verdict.
def save_verdict_table(rows, path):
    """Save a table image. Each row is market, asset, lag, verdict."""
    fig, ax = plt.subplots(figsize=(14, max(2, 0.45 * (len(rows) + 1))))
    ax.axis("off")
    if len(rows) == 0:
        ax.text(0.5, 0.5, "No pairs to show", ha="center")
    else:
        table = ax.table(
            cellText=rows,
            colLabels=["Group", "Market", "Asset", "Lag", "Verdict"],
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _slug(text):
    """Turn a question into a short file name made of letters, numbers and underscores."""
    chars = []
    for char in text.lower():
        if char.isalnum():
            chars.append(char)
        elif char == " " and (len(chars) == 0 or chars[-1] != "_"):
            chars.append("_")
    slug = "".join(chars)
    if len(slug) > 40:
        slug = slug[:40]
    if slug == "":
        return "market"
    return slug


def _short(text, limit):
    """Cut a long market question so the chart and the report stay readable."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


# Why: the written report is what the owner reads, and what can be sent on Telegram.
def build_report(chosen, rejected, verdicts, when=None):
    """Build the daily text report with f-strings. verdicts is a list of dictionaries."""
    if when is None:
        when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"Prediction-market lead-lag report",
        f"Run time: {when}",
        f"Frequency: {config.FREQUENCY}. Max lag: {config.MAX_LAG} trading days. Alpha: {config.ALPHA}.",
        "",
        "Markets used:",
    ]
    if len(chosen) == 0:
        lines.append("- none")
    for market in chosen:
        group = market.get("group") or ""
        label = f"[{group}] " if group != "" else ""
        lines.append(
            f"- {label}{market.get('question', '')} | volume {market.get('volume', 0):.0f} | "
            f"points {market.get('n_points', 0)}"
        )
    lines.append("")
    lines.append("Markets rejected:")
    if len(rejected) == 0:
        lines.append("- none")
    for item in rejected:
        lines.append(f"- {item.get('question', '')}: {item.get('reason', '')}")
    lines.append("")
    lines.append("Verdicts:")
    if len(verdicts) == 0:
        lines.append("- none")
    for row in verdicts:
        group = row.get("group") or ""
        label = f"[{group}] " if group != "" else ""
        core_note = ""
        core_p = row.get("core_adjusted_p")
        if group == "core" and core_p is not None:
            core_note = f" Core-only adjusted p={core_p:.3f} (does not change the verdict)."
        lines.append(
            f"- {label}{row['market']} vs {row['asset']}: {row['verdict']}. {row['reason']} "
            f"n={row['n_obs']}, corr={row['corr']:.3f}, "
            f"ADF odds p={row['adf_odds_p']:.3f}, ADF asset p={row['adf_asset_p']:.3f}."
            f"{core_note}"
        )
    lines.append("")
    lines.append(
        "The correlation p-value is calculated at the lag with the largest correlation. "
        "The adjusted p-value multiplies by every kept pair and by the number of lags searched. "
        "That full-sample figure is the one the verdict uses. "
        "Core markets also print a core-only adjusted p-value, using only the Fed-style pairs. "
        "The core-only figure keeps that slice comparable. It does not change the verdict. "
        "The Granger p-value is the smallest one across lags, so it is easier to look significant "
        "than a test of one lag chosen in advance."
    )
    lines.append("")
    lines.append("Limits:")
    lines.append(LIMITS_TEXT)
    return "\n".join(lines)


# Telegram refuses a message longer than this. The report is split on line breaks.
TELEGRAM_LIMIT = 3900
# How long one sendMessage call may sit with no reply, and how many times to try.
TELEGRAM_TIMEOUT = 60
TELEGRAM_TRIES = 3
# A 429 does not clear if we call again. The next real try waits this long.
TELEGRAM_COOLDOWN = 600

# First row of the Google Sheet. One later row is one market-asset pair.
SHEET_HEADER = ["date", "group", "market", "asset", "verdict", "lag", "n_obs"]


# Why: the full report is too long for a chat. Telegram gets the counts, plus any real lead.
def telegram_summary(rows):
    """Build one short message from sheet rows. The full report stays in output/report.txt."""
    if rows is None or len(rows) == 0:
        return "Lead-lag update\nNo pairs to report."
    counts = {"LEAD DETECTED": 0, "NO RELIABLE LEAD": 0, "DATA TOO THIN": 0}
    leads = []
    stamp = str(rows[0][0])
    for row in rows:
        verdict = str(row[4])
        if verdict in counts:
            counts[verdict] = counts[verdict] + 1
        else:
            counts[verdict] = counts.get(verdict, 0) + 1
        if verdict == "LEAD DETECTED":
            leads.append(row)
    lines = [
        f"Lead-lag update {stamp}",
        (
            f"{len(rows)} pairs. Leads: {counts['LEAD DETECTED']}. "
            f"No reliable lead: {counts['NO RELIABLE LEAD']}. "
            f"Too thin: {counts['DATA TOO THIN']}."
        ),
    ]
    if len(leads) == 0:
        lines.append("No pair passed the lead rule.")
    else:
        shown = 0
        for row in leads:
            if shown == 5:
                break
            question = str(row[2])
            if len(question) > 80:
                question = question[:77] + "..."
            lines.append(f"LEAD: {question} vs {row[3]}, lag {row[5]}, n={row[6]}")
            shown = shown + 1
        extra = len(leads) - shown
        if extra > 0:
            lines.append(f"And {extra} more leads.")
    lines.append("Full results stay in output/report.txt.")
    return "\n".join(lines)


# Why: a 45-pair report is longer than one Telegram message.
def telegram_chunks(text, limit=TELEGRAM_LIMIT):
    """Split text into pieces Telegram will accept. Break on a newline when possible."""
    if text is None or text == "":
        return []
    chunks = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
        if remaining.startswith("\n"):
            remaining = remaining[1:]
    if remaining != "":
        chunks.append(remaining)
    return chunks


# Why: sending the report is optional. A missing token must not stop the program.
def send_telegram(text, token=None, chat_id=None):
    """Post the report to Telegram. Return False, and do not raise, when it cannot."""
    if token is None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "") or ""
    if chat_id is None:
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "") or ""
    token = str(token).strip()
    chat_id = str(chat_id).strip()
    if token == "" or chat_id == "":
        print("Telegram skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty.")
        return False
    paused = _cooldown_until()
    if time.time() < paused:
        print(_cooldown_message(paused))
        return False
    chunks = telegram_chunks(text)
    if len(chunks) == 0:
        print("Telegram skipped: the report text was empty.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    sent = 0
    for index, chunk in enumerate(chunks):
        body = chunk
        if len(chunks) > 1:
            body = f"({index + 1}/{len(chunks)})\n{chunk}"
        posted = _post_telegram(url, chat_id, body, index + 1)
        if not posted:
            return False
        sent = sent + 1
        if index + 1 < len(chunks):
            time.sleep(1)
    _clear_cooldown()
    print(f"Telegram message sent in {sent} part(s).")
    return True


def _post_telegram(url, chat_id, body, part_number):
    """POST one message. Retry a timeout or a 429. Return True when Telegram accepts it."""
    attempt = 1
    while attempt <= TELEGRAM_TRIES:
        try:
            response = requests.post(
                url,
                data={"chat_id": chat_id, "text": body},
                timeout=TELEGRAM_TIMEOUT,
            )
        except requests.RequestException:
            if attempt == TELEGRAM_TRIES:
                print(f"Telegram failed on part {part_number}: no reply from api.telegram.org.")
                return False
            print(f"Telegram part {part_number} got no reply. Trying again.")
            time.sleep(5)
            attempt = attempt + 1
            continue
        if response.status_code == 429:
            # Calling again restarts Telegram's block, so this run stops and waits locally.
            wait = TELEGRAM_COOLDOWN
            try:
                asked = int(response.json().get("parameters", {}).get("retry_after", TELEGRAM_COOLDOWN))
            except (ValueError, TypeError):
                asked = TELEGRAM_COOLDOWN
            if asked > wait:
                wait = asked
            paused = _set_cooldown(wait)
            print(_cooldown_message(paused))
            return False
        if response.status_code >= 400:
            print(f"Telegram failed on part {part_number}: HTTP {response.status_code}.")
            return False
        return True
    print(f"Telegram failed on part {part_number} after {TELEGRAM_TRIES} tries.")
    return False


def _cooldown_path():
    """Local clock for the Telegram block. This file is not sent anywhere."""
    return os.path.join(config.OUTPUT_DIR, "telegram_cooldown.txt")


def _cooldown_until():
    """Return the epoch time when Telegram may be called again. 0 means no pause."""
    path = _cooldown_path()
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return float(handle.read().strip())
    except (OSError, ValueError):
        return 0


def _set_cooldown(seconds):
    """Remember not to call Telegram until this many seconds from now."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    until = time.time() + seconds
    with open(_cooldown_path(), "w", encoding="utf-8") as handle:
        handle.write(str(until))
    return until


def _clear_cooldown():
    """Drop the pause after a message is accepted."""
    path = _cooldown_path()
    if os.path.exists(path):
        os.remove(path)


def _cooldown_message(until):
    """Tell the user the local time when one more try is safe."""
    when = datetime.fromtimestamp(until).strftime("%H:%M")
    return f"Telegram is paused until {when}. Another try before then restarts the block."


def _credentials_path(path):
    """A relative credentials path is looked up next to config.py."""
    if os.path.isabs(path):
        return path
    return os.path.join(config.BASE_DIR, path)


# Why: a sheet is a second copy of the verdicts. Login failures must not crash the run.
def append_sheet(rows, credentials_file=None, sheet_id=None):
    """Append one row per pair to a Google Sheet. Return False if it cannot."""
    if credentials_file is None:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "") or ""
    if sheet_id is None:
        sheet_id = os.getenv("GOOGLE_SHEET_ID", "") or ""
    if credentials_file == "" or sheet_id == "":
        print("Google Sheet skipped: GOOGLE_CREDENTIALS_FILE or GOOGLE_SHEET_ID is empty.")
        return False
    credentials_file = _credentials_path(credentials_file)
    if not os.path.exists(credentials_file):
        print(f"Google Sheet skipped: credentials file not found at {credentials_file}.")
        return False
    try:
        import gspread

        client = gspread.service_account(filename=credentials_file)
        sheet = client.open_by_key(sheet_id).sheet1
        first = sheet.row_values(1)
        if len(first) == 0:
            sheet.append_row(SHEET_HEADER)
        for row in rows:
            values = []
            for value in row:
                values.append(str(value))
            sheet.append_row(values)
        print(f"Appended {len(rows)} rows to the Google Sheet.")
        return True
    except Exception as exc:
        print(f"Google Sheet failed: {exc}")
        return False


# Why: main should call one function and get files plus the text back.
def write_outputs(chosen, rejected, results, verdict_rows, odds_for_plot, prices_for_plot):
    """Save charts and report.txt. Return the report text."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    for key, result in results.items():
        market_name, asset_name = key
        file_name = f"lag_{asset_name}_{_slug(market_name)}.png"
        path = os.path.join(config.OUTPUT_DIR, file_name)
        save_lag_chart(market_name, asset_name, result["lag_profile"], result["best_lag"], path)
    if odds_for_plot is not None and prices_for_plot is not None:
        save_overlay(
            odds_for_plot["series"],
            prices_for_plot["series"],
            _short(odds_for_plot["title"], 80),
            os.path.join(config.OUTPUT_DIR, "overlay_strongest.png"),
        )
    table_rows = []
    for row in verdict_rows:
        table_rows.append(
            [
                row.get("group") or "",
                _short(row["market"], 42),
                row["asset"],
                str(row["lag"]),
                row["verdict"],
            ]
        )
    save_verdict_table(table_rows, os.path.join(config.OUTPUT_DIR, "verdict_table.png"))
    text = build_report(chosen, rejected, verdict_rows)
    report_path = os.path.join(config.OUTPUT_DIR, "report.txt")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"Wrote {report_path}")
    return text
