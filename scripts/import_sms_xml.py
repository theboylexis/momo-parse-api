"""
Import a consented SMS XML export (Android SMS Backup & Restore) into
``corpus/real_sms_corpus.csv`` with personal identifiers pseudonymized.

The input file is an Android-format XML backup that lives **outside** the
repository (e.g. on the Desktop). The repository never stores the raw XML.
What gets written to the committed corpus CSV is:

- the SMS text, with **names and phone numbers replaced by short
  deterministic hashes** (``name_<10hex>`` / ``ph_<10hex>``) and balances
  redacted to ``[redacted]`` (consistent with the existing real-corpus
  convention);
- parser-extracted fields (``telco``, ``tx_type``, ``amount``, ...) with
  ``counterparty_name`` and ``counterparty_phone`` also replaced by the
  same hashed tokens.

This enforces the data-minimization claim in ``docs/data_minimization.md``:
no raw PII from third-party counterparties reaches public git history.

Subcommands
-----------
``import``
    Read an SMS-Backup-&-Restore XML file, parse each message, filter out
    marketing/noise (``match_mode == none``), dedupe by transaction ID
    against what's already in the corpus, hash identifiers, and append
    new rows to ``corpus/real_sms_corpus.csv``.

``redact-existing``
    Rewrite the *existing* rows in ``corpus/real_sms_corpus.csv`` so they
    match the same hashing rules as newly imported rows. Makes the full
    corpus consistent after the first import run.

Usage
-----
    python scripts/import_sms_xml.py import "C:/path/to/sms-export.xml"
    python scripts/import_sms_xml.py import "C:/path/to/export.xml" --dry-run
    python scripts/import_sms_xml.py redact-existing
    python scripts/import_sms_xml.py redact-existing --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

# Allow running as `python scripts/import_sms_xml.py` from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import parse as parse_sms

ROOT = Path(__file__).parent.parent
CORPUS_PATH = ROOT / "corpus" / "real_sms_corpus.csv"

CORPUS_FIELDS = [
    "raw_sms", "telco", "tx_type", "amount", "counterparty_name",
    "counterparty_phone", "balance", "fee", "tx_id", "reference",
    "dest_network",
]

# Sender IDs we consider in-scope. Everything else is filtered out.
# T-CASH is the Telecel MoMo shortcode on handsets (it's what tests/helpers
# pass as sender_id for Telecel). Missing it here dropped every Telecel
# message in the first import run.
ALLOWED_SENDERS = {
    "MobileMoney", "MTN",
    "T-CASH", "Telecel", "VodafoneCash", "Vodafone",
}

HASH_LEN = 10  # chars of hex → 40 bits, plenty for a few-thousand-row corpus

# A phone-number regex tight enough to avoid matching amounts or tx IDs.
# Ghana numbers: 233XXXXXXXXX (12 digits) or 0XXXXXXXXX (10 digits).
_PHONE_RE = re.compile(r"\b(?:233\d{9}|0\d{9})\b")

# Balance-redaction regex — strips actual amounts from ``(Current|Available)
# Balance: GHS X,XXX.XX`` while leaving the structure intact.
_BALANCE_RE = re.compile(
    r"((?:Current|Available|New|Your new)\s*Balance[^:]*:\s*GHS?\s*)[-+]?\d[\d,]*\.?\d*",
    re.IGNORECASE,
)


# ── Hashing ───────────────────────────────────────────────────────────────────

def _hash_name(name: str) -> str:
    norm = re.sub(r"\s+", " ", name.strip().upper())
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:HASH_LEN]
    return f"name_{digest}"


def _hash_phone(phone: str) -> str:
    norm = re.sub(r"\D", "", phone)
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:HASH_LEN]
    return f"ph_{digest}"


# ── Redaction ─────────────────────────────────────────────────────────────────

def _redact_body(body: str, *, name: str | None, phone: str | None) -> str:
    """Replace the parser-extracted name/phone anywhere in the body, redact
    balance numerics, and replace any remaining Ghana-format phone number."""
    text = body

    if name:
        # Case-insensitive replace of the full name, preserving surrounding
        # whitespace/punctuation.
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        text = pattern.sub(_hash_name(name), text)

    if phone:
        text = text.replace(phone, _hash_phone(phone))

    # Catch any phone numbers that the parser didn't surface via
    # counterparty_phone (e.g. phones in Reference fields).
    text = _PHONE_RE.sub(lambda m: _hash_phone(m.group(0)), text)

    # Redact balances (consistent with existing corpus convention).
    text = _BALANCE_RE.sub(r"\1[redacted]", text)

    return text


# ── XML parsing ───────────────────────────────────────────────────────────────

@dataclass
class XmlSms:
    address: str
    body: str
    date: str  # unix millis as string


def _iter_xml(path: Path) -> Iterator[XmlSms]:
    tree = ET.parse(path)
    root = tree.getroot()
    for sms in root.findall("sms"):
        yield XmlSms(
            address=sms.get("address", ""),
            body=sms.get("body", ""),
            date=sms.get("date", ""),
        )


# ── Corpus helpers ────────────────────────────────────────────────────────────

def _load_existing_rows() -> tuple[list[dict], set[str]]:
    """Return (existing rows, set of tx_ids we already have)."""
    if not CORPUS_PATH.exists():
        return [], set()
    with CORPUS_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tx_ids = {r["tx_id"] for r in rows if r.get("tx_id")}
    return rows, tx_ids


def _write_rows(rows: list[dict]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CORPUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CORPUS_FIELDS})


# ── Row builders ──────────────────────────────────────────────────────────────

def _row_from_parse(body: str, parsed) -> dict | None:
    """Build a corpus row from a parser result, with PII hashed. Returns
    None for messages the parser couldn't classify (marketing, etc.)."""
    if parsed.match_mode == "none":
        return None

    name = parsed.counterparty_name
    phone = parsed.counterparty_phone
    redacted = _redact_body(body, name=name, phone=phone)

    # Hash the reference too — it sometimes contains the counterparty name
    # and phone again.
    reference = parsed.reference or ""
    if name and reference:
        reference = re.sub(re.escape(name), _hash_name(name),
                           reference, flags=re.IGNORECASE)
    if phone and reference:
        reference = reference.replace(phone, _hash_phone(phone))
    reference = _PHONE_RE.sub(lambda m: _hash_phone(m.group(0)), reference)

    return {
        "raw_sms":            redacted,
        "telco":              parsed.telco,
        "tx_type":            parsed.tx_type,
        "amount":             parsed.amount if parsed.amount is not None else "",
        "counterparty_name":  _hash_name(name) if name else "",
        "counterparty_phone": _hash_phone(phone) if phone else "",
        "balance":            "",  # redacted — not retained in corpus
        "fee":                getattr(parsed, "fee", None) or "",
        "tx_id":              parsed.tx_id or "",
        "reference":          reference,
        "dest_network":       getattr(parsed, "dest_network", None) or parsed.telco,
    }


# ── Subcommand: import ────────────────────────────────────────────────────────

def cmd_import(xml_path: Path, *, dry_run: bool) -> None:
    if not xml_path.exists():
        print(f"ERROR: {xml_path} not found", file=sys.stderr)
        sys.exit(1)

    existing_rows, existing_tx_ids = _load_existing_rows()
    print(f"Existing corpus: {len(existing_rows)} rows "
          f"({len(existing_tx_ids)} with tx_id)")

    total = 0
    skipped_sender = 0
    skipped_unparsed = 0
    skipped_no_tx = 0
    skipped_dupe = 0
    new_rows: list[dict] = []

    for sms in _iter_xml(xml_path):
        total += 1
        if sms.address not in ALLOWED_SENDERS:
            skipped_sender += 1
            continue

        parsed = parse_sms(sms.body, sender_id=sms.address)
        if parsed.match_mode == "none":
            skipped_unparsed += 1
            continue

        if not parsed.tx_id:
            # Without a tx_id we can't dedupe; skip to avoid duplicate risk
            # on re-imports. The current templates all capture tx_id for
            # real transactions.
            skipped_no_tx += 1
            continue

        if parsed.tx_id in existing_tx_ids:
            skipped_dupe += 1
            continue

        row = _row_from_parse(sms.body, parsed)
        if row is None:
            skipped_unparsed += 1
            continue

        new_rows.append(row)
        existing_tx_ids.add(parsed.tx_id)

    print("")
    print(f"XML messages scanned:           {total}")
    print(f"  Skipped (wrong sender):       {skipped_sender}")
    print(f"  Skipped (unparsed):           {skipped_unparsed}")
    print(f"  Skipped (no tx_id):           {skipped_no_tx}")
    print(f"  Skipped (already in corpus):  {skipped_dupe}")
    print(f"  New rows to append:           {len(new_rows)}")

    if dry_run:
        print("\n--dry-run: no changes written.")
        return

    merged = existing_rows + new_rows
    _write_rows(merged)
    print(f"\n-> Wrote {len(merged)} rows to {CORPUS_PATH}")


# ── Subcommand: redact-existing ───────────────────────────────────────────────

def cmd_redact_existing(*, dry_run: bool) -> None:
    existing_rows, _ = _load_existing_rows()
    if not existing_rows:
        print(f"No corpus at {CORPUS_PATH} — nothing to redact.")
        return

    name_hashed = 0
    phone_hashed = 0
    sms_body_updated = 0
    ref_updated = 0

    updated: list[dict] = []
    for row in existing_rows:
        new = dict(row)
        name = (row.get("counterparty_name") or "").strip()
        phone = (row.get("counterparty_phone") or "").strip()

        # counterparty columns: if already hashed, leave alone.
        if name and not name.startswith("name_"):
            new["counterparty_name"] = _hash_name(name)
            name_hashed += 1
        if phone and not phone.startswith("ph_"):
            new["counterparty_phone"] = _hash_phone(phone)
            phone_hashed += 1

        # Redact the raw_sms body, reusing the *original* name/phone values
        # so substrings match.
        body_before = row.get("raw_sms", "")
        body_after = _redact_body(
            body_before,
            name=name if name and not name.startswith("name_") else None,
            phone=phone if phone and not phone.startswith("ph_") else None,
        )
        if body_after != body_before:
            new["raw_sms"] = body_after
            sms_body_updated += 1

        # Redact the reference column too.
        ref_before = row.get("reference", "")
        ref_after = ref_before
        if name and not name.startswith("name_") and ref_before:
            ref_after = re.sub(re.escape(name), _hash_name(name),
                               ref_after, flags=re.IGNORECASE)
        if phone and not phone.startswith("ph_") and ref_after:
            ref_after = ref_after.replace(phone, _hash_phone(phone))
        ref_after = _PHONE_RE.sub(lambda m: _hash_phone(m.group(0)), ref_after)
        if ref_after != ref_before:
            new["reference"] = ref_after
            ref_updated += 1

        updated.append(new)

    print(f"Existing rows:              {len(existing_rows)}")
    print(f"  counterparty_name hashed: {name_hashed}")
    print(f"  counterparty_phone hashed:{phone_hashed}")
    print(f"  raw_sms body rewritten:   {sms_body_updated}")
    print(f"  reference rewritten:      {ref_updated}")

    if dry_run:
        print("\n--dry-run: no changes written.")
        return

    _write_rows(updated)
    print(f"\n-> Rewrote {len(updated)} rows in {CORPUS_PATH}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_import = sub.add_parser("import", help="Import an XML SMS export")
    ap_import.add_argument("xml_path", type=Path,
                           help="Path to the SMS-Backup-&-Restore XML file")
    ap_import.add_argument("--dry-run", action="store_true",
                           help="Report counts but don't write to corpus")

    ap_redact = sub.add_parser(
        "redact-existing", help="Retroactively hash PII in existing corpus rows"
    )
    ap_redact.add_argument("--dry-run", action="store_true",
                           help="Report counts but don't write")

    args = ap.parse_args()

    if args.cmd == "import":
        cmd_import(args.xml_path, dry_run=args.dry_run)
    elif args.cmd == "redact-existing":
        cmd_redact_existing(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
