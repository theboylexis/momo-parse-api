"""
Sample real SMS rows for human labeling.

Reads ``categorizer/labeled_data.csv``, filters to ``source=real``,
stratifies by the model's predicted category (so rare categories are
represented), and writes a CSV with the model's prediction pre-filled
for Alex to agree/disagree with in any spreadsheet tool.

Output columns
--------------
- ``sample_id``            — stable row number, 1..N
- ``sms_text``              — raw SMS body (may contain name_<hex> /
                              ph_<hex> tokens if the source was imported
                              via scripts/import_sms_xml.py)
- ``tx_type``               — parser's structured tx_type
- ``amount``                — parsed amount
- ``counterparty_name``     — hashed counterparty identifier
- ``reference``             — any reference field the parser extracted
- ``model_category``        — the categorizer's prediction
- ``human_category``        — BLANK; fill in with the correct slug
- ``notes``                 — BLANK; optional free-text

After labeling, run:
    python scripts/score_human_labels.py <path-to-labeled-csv>

Usage
-----
    python scripts/sample_for_labeling.py                 # default: 150 rows
    python scripts/sample_for_labeling.py --n 200         # larger sample
    python scripts/sample_for_labeling.py --seed 7        # reproducible pick
    python scripts/sample_for_labeling.py --out labeling/sample.csv
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import warnings
warnings.filterwarnings("ignore")

from categorizer.pipeline import categorize
from categorizer.taxonomy import SLUGS
from parser import parse as parse_sms

ROOT = Path(__file__).parent.parent
LABELED_PATH = ROOT / "categorizer" / "labeled_data.csv"
DEFAULT_OUT = ROOT / "labeling" / "sample.csv"

DEFAULT_N = 150
DEFAULT_SEED = 42
MIN_PER_CATEGORY = 3  # floor per model category if enough rows exist

OUTPUT_COLUMNS = [
    "sample_id", "sms_text", "tx_type", "amount",
    "counterparty_name", "reference",
    "model_category", "human_category", "notes",
]


def _maybe_float(v: str) -> float | None:
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _load_real_rows() -> tuple[list[dict], dict[str, int]]:
    """
    Load rows with ``source == 'real'`` and **re-run the current parser +
    categorizer on each SMS body**. This ensures ``model_category`` reflects
    what the production model would predict *today*, not what an earlier
    rule-labeler cached — important because recent parser fixes (failure
    filter, fuzzy signal gating, new templates) change which SMS parse and
    how they categorize.

    Returns (kept_rows, counts) where counts reports how many rows were
    skipped at each gate so the output log is self-documenting.
    """
    if not LABELED_PATH.exists():
        print(f"ERROR: {LABELED_PATH} not found.\n"
              f"Run: python -m categorizer.label_corpus", file=sys.stderr)
        sys.exit(1)

    kept: list[dict] = []
    counts = {"seen": 0, "not_real": 0, "parse_none": 0, "no_amount": 0, "kept": 0}

    with LABELED_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            counts["seen"] += 1
            if row.get("source") != "real":
                counts["not_real"] += 1
                continue

            sms_text = row.get("raw_sms", "")
            if not sms_text:
                counts["parse_none"] += 1
                continue

            r = parse_sms(sms_text)
            if r.match_mode == "none":
                counts["parse_none"] += 1
                continue
            if r.amount is None:
                # Wallet-balance checks and similar zero-amount SMS aren't
                # useful for categorization-accuracy evaluation.
                counts["no_amount"] += 1
                continue

            cat_slug, cat_conf = categorize(
                tx_type=r.tx_type,
                amount=r.amount,
                reference=r.reference,
                counterparty_name=r.counterparty_name,
                counterparty_phone=r.counterparty_phone,
                fee=r.fee,
            )

            kept.append({
                "raw_sms":           sms_text,
                "tx_type":           r.tx_type,
                "amount":            r.amount,
                "counterparty_name": r.counterparty_name or "",
                "reference":         r.reference or "",
                "category":          cat_slug,
                "category_confidence": cat_conf,
            })
            counts["kept"] += 1

    return kept, counts


def _stratified_sample(
    rows: list[dict], n: int, seed: int, min_per_cat: int
) -> list[dict]:
    """
    Stratify by model-predicted category. First pulls ``min_per_cat`` from
    every category that has at least that many rows; then fills the
    remainder proportionally across the total pool.
    """
    rng = random.Random(seed)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    picked: list[dict] = []
    picked_ids: set[int] = set()

    # Floor pass: at least min_per_cat from every non-tiny category.
    for cat, cat_rows in by_cat.items():
        k = min(min_per_cat, len(cat_rows))
        chosen = rng.sample(cat_rows, k)
        for r in chosen:
            picked.append(r)
            picked_ids.add(id(r))

    # Fill to n with a proportional random sample from the remainder.
    remainder = [r for r in rows if id(r) not in picked_ids]
    rng.shuffle(remainder)
    need = max(0, n - len(picked))
    picked.extend(remainder[:need])

    # Stable order by (category, tx_type) for easier review.
    picked.sort(key=lambda r: (r["category"], r.get("tx_type", "")))
    return picked[:n]


def _write_labeling_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            w.writerow({
                "sample_id":          i,
                "sms_text":           r.get("raw_sms", ""),
                "tx_type":            r.get("tx_type", ""),
                "amount":             r.get("amount", ""),
                "counterparty_name":  r.get("counterparty_name", ""),
                "reference":          r.get("reference", ""),
                "model_category":     r.get("category", ""),
                "human_category":     "",
                "notes":              "",
            })


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--n", type=int, default=DEFAULT_N,
                    help=f"Target sample size (default {DEFAULT_N})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"Random seed (default {DEFAULT_SEED})")
    ap.add_argument("--min-per-cat", type=int, default=MIN_PER_CATEGORY,
                    help=f"Floor per model category (default {MIN_PER_CATEGORY})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"Output CSV path (default {DEFAULT_OUT.relative_to(ROOT)})")
    args = ap.parse_args()

    print("Re-parsing and re-categorizing real corpus rows through the current "
          "pipeline\n(this reflects the model's predictions as of today, not "
          "stale labels)...\n")
    real_rows, counts = _load_real_rows()
    print(f"Rows seen in labeled_data.csv:      {counts['seen']}")
    print(f"  Skipped (source != real):         {counts['not_real']}")
    print(f"  Skipped (parse match_mode=none):  {counts['parse_none']}")
    print(f"  Skipped (no amount extracted):    {counts['no_amount']}")
    print(f"  Kept for sampling:                {counts['kept']}")

    from collections import Counter
    cat_counts = Counter(r["category"] for r in real_rows)
    print("\nLive model category distribution:")
    for cat, n in cat_counts.most_common():
        print(f"  {cat:<30} {n}")

    sample = _stratified_sample(real_rows, args.n, args.seed, args.min_per_cat)
    print(f"\nSampled {len(sample)} rows (target {args.n}, seed {args.seed}).")

    sample_cats = Counter(r["category"] for r in sample)
    print("\nSample category distribution:")
    for cat, n in sample_cats.most_common():
        print(f"  {cat:<30} {n}")

    _write_labeling_csv(sample, args.out)
    print(f"\n-> Wrote {args.out}")
    print("\nValid categories to use in `human_category`:")
    for s in SLUGS:
        print(f"  {s}")
    print("\nFill in `human_category` for every row in a spreadsheet editor,")
    print("then run:")
    print(f"  python scripts/score_human_labels.py {args.out}")


if __name__ == "__main__":
    main()
