"""
End-to-end demo: run a real SMS export through the full MomoParse pipeline
and print a human-readable Financial Health Report.

Reads an Android SMS Backup & Restore XML file, filters to MoMo senders,
runs each message through ``parser.parse`` + the ML categorizer, and then
calls ``enricher.analytics.compute_report`` — the same function serving
``POST /v1/report`` — to produce the user-facing report.

Prints the result to stdout in plain prose. No server needed.

Usage
-----
    python scripts/demo_report.py "C:/path/to/sms-export.xml"
    python scripts/demo_report.py "C:/path/to/sms-export.xml" --months 6
    python scripts/demo_report.py "C:/path/to/sms-export.xml" --write docs/demo_report.md
"""
from __future__ import annotations

import argparse
import sys
import warnings

warnings.filterwarnings("ignore")
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from categorizer.pipeline import categorize
from categorizer.taxonomy import BY_SLUG
from enricher.analytics import compute_report
from parser import parse as parse_sms

ROOT = Path(__file__).parent.parent
ALLOWED_SENDERS = {
    "MobileMoney", "MTN",
    "T-CASH", "Telecel", "VodafoneCash", "Vodafone",
}


@dataclass
class Message:
    """Minimal stand-in for api.models.SMSMessage. _parse_and_categorize uses
    .sms_text and .sender_id; .xml_date carries the Android-export timestamp
    so we can attach a date when the parser can't extract one from the body."""
    sms_text: str
    sender_id: str
    xml_date: str | None = None  # ISO-8601 date string or None


# ── XML loader ────────────────────────────────────────────────────────────────

def _load_xml(path: Path, *, since: datetime | None) -> list[Message]:
    """Read XML, yield Message objects for MoMo senders only."""
    tree = ET.parse(path)
    root = tree.getroot()
    messages: list[Message] = []
    for sms in root.findall("sms"):
        address = sms.get("address", "")
        if address not in ALLOWED_SENDERS:
            continue
        body = sms.get("body", "")
        date_ms = int(sms.get("date") or 0)
        dt: datetime | None = None
        if date_ms > 0:
            dt = datetime.fromtimestamp(date_ms / 1000, tz=timezone.utc)
            if since is not None and dt < since:
                continue
        elif since is not None:
            continue
        xml_date = dt.date().isoformat() if dt else None
        messages.append(Message(sms_text=body, sender_id=address,
                                xml_date=xml_date))
    return messages


# ── Report formatting ─────────────────────────────────────────────────────────

def _fmt_ghs(v: float | None) -> str:
    if v is None:
        return "GHS —"
    return f"GHS {v:,.2f}"


def _bar(value: float, total: float, width: int = 28) -> str:
    """Tiny ASCII bar for category breakdowns."""
    if total <= 0:
        return ""
    filled = int(round(width * value / total))
    return "█" * filled + "·" * (width - filled)


def _format_report(data: dict, *, n_messages_in: int, n_parsed: int) -> str:
    lines: list[str] = []
    summary = data["summary"]
    indexes = data["financial_indexes"]
    score = data["financial_health_score"]
    confidence = data["data_confidence"]
    months = data["months"]

    lines.append("=" * 64)
    lines.append(" MOMOPARSE — FINANCIAL HEALTH REPORT (end-to-end demo)")
    lines.append("=" * 64)
    lines.append("")
    lines.append(f"SMS messages read from export:       {n_messages_in}")
    lines.append(f"Parsed as valid transactions:        {n_parsed}")
    lines.append(f"Data confidence:                     {confidence}")
    dr = summary.get("date_range") or {}
    lines.append(f"Date range covered:                  "
                 f"{dr.get('start') or '—'} → {dr.get('end') or '—'}")
    lines.append(f"Months of activity:                  {len(months)}")
    lines.append("")

    # ── Headline ──────────────────────────────────────────────────────────────
    band = indexes.get("score_band") or {}
    band_label = band.get("label", "")
    lines.append("-" * 64)
    headline = f" FINANCIAL HEALTH SCORE:  {score} / 100"
    if band_label:
        headline += f"   —   {band_label}"
    lines.append(headline)
    lines.append("-" * 64)
    if band.get("description"):
        lines.append(f" {band['description']}")
    sw = indexes.get("scoring_window") or {}
    if sw:
        if sw.get("mode") == "rolling":
            lines.append(
                f" Scoring window: last {sw.get('months')} months "
                f"({sw.get('start')} -> {sw.get('end')})"
                + (f" — {sw.get('transactions_excluded')} older tx excluded"
                   if sw.get("transactions_excluded") else "")
            )
        else:
            lines.append(" Scoring window: lifetime (all provided data)")
    lines.append("")

    # ── Score drivers ─────────────────────────────────────────────────────────
    drivers = indexes.get("score_drivers", []) or []
    if drivers:
        lines.append("What's driving the score:")
        lines.append("")
        for d in drivers:
            lines.append(
                f"  {d['index']:<30}  "
                f"contributes  {d['contribution_pp']:>2} pts  "
                f"(normalized {d['normalized']:.2f})"
            )
        lines.append("")

    # ── Cash flow totals ──────────────────────────────────────────────────────
    lines.append("Cash flow:")
    lines.append(f"  Total income:     {_fmt_ghs(summary['total_income']):>18}")
    lines.append(f"  Total expenses:   {_fmt_ghs(summary['total_expenses']):>18}")
    lines.append(f"  Net:              {_fmt_ghs(summary['net_cash_flow']):>18}")
    sav = data["savings_analysis"]
    lines.append(f"  Savings rate:     {sav.get('savings_rate', 0.0):>17.1f} %")
    lines.append("")

    # ── Category breakdown (top 8) ────────────────────────────────────────────
    cats = summary.get("category_breakdown") or {}
    if cats:
        total = sum(v.get("amount", 0) for v in cats.values()) or 1
        ordered = sorted(
            cats.items(), key=lambda kv: -(kv[1].get("amount") or 0)
        )[:8]
        lines.append("Top categories by amount:")
        for name, v in ordered:
            amt = v.get("amount", 0)
            cnt = v.get("count", 0)
            lines.append(
                f"  {name:<28} {_fmt_ghs(amt):>16} "
                f"({cnt} tx)   {_bar(amt, total)}"
            )
        lines.append("")

    # ── Monthly timeline (compact) ────────────────────────────────────────────
    if months:
        lines.append("Monthly timeline (last 12 months shown):")
        for m in months[-12:]:
            lines.append(
                f"  {m['month']}  income {_fmt_ghs(m['income']):>14}  "
                f"expense {_fmt_ghs(m['expenses']):>14}  "
                f"savings {m['savings_rate']:>5.1f}%"
            )
        lines.append("")

    # ── Insights ──────────────────────────────────────────────────────────────
    insights = data.get("insights") or []
    if insights:
        lines.append("Insights:")
        for i in insights:
            title = i.get("title", i.get("type", "insight"))
            detail = i.get("detail", i.get("message", ""))
            lines.append(f"  - {title}: {detail}")
        lines.append("")

    # ── Recommendations ───────────────────────────────────────────────────────
    recs = data.get("recommendations") or []
    if recs:
        lines.append("Recommendations:")
        for r in recs:
            title = r.get("title", "")
            detail = r.get("detail", r.get("message", ""))
            if title:
                lines.append(f"  - {title}: {detail}")
            else:
                lines.append(f"  - {detail}")
        lines.append("")

    # ── Interpretation for Alex (plain English) ───────────────────────────────
    lines.append("=" * 64)
    lines.append(" HOW TO READ THIS")
    lines.append("=" * 64)
    lines.append(
        "\n"
        "The score is 0-100 — higher is 'healthier'. Think of it as a\n"
        "credit-risk proxy: a lender seeing 70+ has evidence of regular\n"
        "income, stable spending, and reasonable savings; 40 or below\n"
        "means the pattern of transactions looks volatile or cash-poor.\n"
        "\n"
        "The five drivers above decompose that number. Each sub-index is\n"
        "normalized to [0, 1] and multiplied by its weight, then summed\n"
        "to 100. The top driver is the strongest reason the score is\n"
        "where it is; the bottom driver is the main thing to improve.\n"
        "\n"
        "Data confidence tells the lender how much to trust the score.\n"
        "Less than 3 months of data → confidence drops fast.\n"
    )

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("xml_path", type=Path, help="Path to SMS XML export")
    ap.add_argument("--months", type=int, default=None,
                    help="Only include SMS from the last N months "
                         "at the XML-parsing stage (default: all). This "
                         "is a pre-filter; the score itself is windowed "
                         "separately via --score-window.")
    ap.add_argument("--score-window", type=int, default=6,
                    help="MFH scoring window in months (default 6). "
                         "Pass 0 for lifetime scoring. Matches the API's "
                         "window_months parameter on /v1/report.")
    ap.add_argument("--write", type=Path, default=None,
                    help="Also write the report to this path (e.g. "
                         "docs/demo_report.md)")
    args = ap.parse_args()

    if not args.xml_path.exists():
        print(f"ERROR: {args.xml_path} not found", file=sys.stderr)
        sys.exit(1)

    since: datetime | None = None
    if args.months:
        since = datetime.now(tz=timezone.utc) - timedelta(days=30 * args.months)

    messages = _load_xml(args.xml_path, since=since)
    if not messages:
        print("No MoMo messages found in the export.", file=sys.stderr)
        sys.exit(1)

    # Parse + categorize + aggregate, with two corrections the standard API
    # path does not apply because it doesn't know about the XML envelope:
    #   1. Attach the Android-export timestamp when the parser can't recover
    #      a date from the SMS body — prevents the undated-smearing artifact.
    #   2. Dedupe by transaction_id — MoMo frequently sends two SMS per
    #      transaction (MTN-branded and MoMo-branded) with identical tx_ids,
    #      which would otherwise double-count income and expense.
    tx_dicts: list[dict] = []
    seen_tx_ids: set[str] = set()
    n_dupes = 0
    n_unparsed = 0
    for msg in messages:
        r = parse_sms(msg.sms_text, sender_id=msg.sender_id)
        if r.match_mode == "none":
            n_unparsed += 1
            continue
        if r.tx_id and r.tx_id in seen_tx_ids:
            n_dupes += 1
            continue
        if r.tx_id:
            seen_tx_ids.add(r.tx_id)
        cat_slug, cat_conf = categorize(
            tx_type=r.tx_type, amount=r.amount, reference=r.reference,
            counterparty_name=r.counterparty_name,
            counterparty_phone=r.counterparty_phone, fee=r.fee,
        )
        tx_dicts.append({
            "tx_type": r.tx_type,
            "amount": r.amount,
            "category": cat_slug,
            "category_label": BY_SLUG[cat_slug].label if cat_slug in BY_SLUG else None,
            "category_confidence": cat_conf,
            "counterparty_name": r.counterparty_name,
            "counterparty_phone": r.counterparty_phone,
            "reference": r.reference,
            "date": r.date or msg.xml_date,  # XML timestamp as fallback
            "fee": r.fee,
            "telco": r.telco,
            "tx_id": r.tx_id,
        })

    n_parsed = len(tx_dicts)
    print(f"[demo] Unparsed/marketing: {n_unparsed}   "
          f"Duplicate tx_ids skipped: {n_dupes}   "
          f"Unique transactions: {n_parsed}", file=sys.stderr)
    score_window = None if args.score_window == 0 else args.score_window
    data = compute_report(tx_dicts, window_months=score_window)

    report = _format_report(data, n_messages_in=len(messages), n_parsed=n_parsed)
    print(report)

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(report, encoding="utf-8")
        print(f"\n-> Also written to {args.write}", file=sys.stderr)


if __name__ == "__main__":
    main()
