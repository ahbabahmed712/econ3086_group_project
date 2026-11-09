# Charts, a text report, and optional Telegram or Google Sheet delivery.

import os
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
def save_lag_chart(market_name, asset_name, profile, best_lag, path):
    """Bar chart of correlation at each lag. The best lag is drawn in a darker colour."""
    labels = []
    values = []
    colors = []
    for row in profile:
        labels.append(str(row["lag"]))
        values.append(row["corr"])
        if row["lag"] == best_lag:
            colors.append("#1f4e79")
        else:
            colors.append("#8fadc8")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Lag in trading days (positive means odds lead)")
    ax.set_ylabel("Correlation")
    ax.set_title(f"{asset_name}: best lag {best_lag}")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# Why: a person should be able to look at the two series, not only at a p-value.
def save_overlay(odds, prices, title, path):
    """Plot daily odds and the asset price on the same dates, with two scales."""
    fig, ax_left = plt.subplots(figsize=(9, 4))
    ax_right = ax_left.twinx()
    ax_left.plot(list(odds.index), list(odds.values), color="#1f4e79", label="Odds")
    ax_right.plot(list(prices.index), list(prices.values), color="#b85c38", label="Asset")
    ax_left.set_ylabel("Odds (Yes price)")
    ax_right.set_ylabel("Asset price")
    ax_left.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# Why: the demo needs one picture that lists every verdict.
def save_verdict_table(rows, path):
    """Save a table image. Each row is market, asset, lag, verdict."""
    fig, ax = plt.subplots(figsize=(12, max(2, 0.45 * (len(rows) + 1))))
    ax.axis("off")
    if len(rows) == 0:
        ax.text(0.5, 0.5, "No pairs to show", ha="center")
    else:
        table = ax.table(cellText=rows, colLabels=["Market", "Asset", "Lag", "Verdict"], loc="center")
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
        lines.append(
            f"- {market.get('question', '')} | volume {market.get('volume', 0):.0f} | "
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
        lines.append(
            f"- {row['market']} vs {row['asset']}: {row['verdict']}. {row['reason']} "
            f"n={row['n_obs']}, corr={row['corr']:.3f}, "
            f"ADF odds p={row['adf_odds_p']:.3f}, ADF asset p={row['adf_asset_p']:.3f}."
        )
    lines.append("")
    lines.append(
        "The correlation p-value is calculated at the lag with the largest correlation. "
        "The adjusted p-value multiplies by the number of pairs and by the number of lags searched. "
        "The Granger p-value is the smallest one across lags, so it is easier to look significant "
        "than a test of one lag chosen in advance."
    )
    lines.append("")
    lines.append("Limits:")
    lines.append(LIMITS_TEXT)
    return "\n".join(lines)


# Why: sending the report is optional. A missing token must not stop the program.
def send_telegram(text, token=None, chat_id=None):
    """Post the report to Telegram. Return False, and do not raise, when it cannot."""
    if token is None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "") or ""
    if chat_id is None:
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "") or ""
    if token == "" or chat_id == "":
        print("Telegram skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is empty.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            data={"chat_id": chat_id, "text": text[:4000]},
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        print("Telegram message sent.")
        return True
    except requests.RequestException as exc:
        print(f"Telegram failed: {exc}")
        return False


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
    try:
        import gspread

        client = gspread.service_account(filename=credentials_file)
        sheet = client.open_by_key(sheet_id).sheet1
        for row in rows:
            sheet.append_row(row)
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
