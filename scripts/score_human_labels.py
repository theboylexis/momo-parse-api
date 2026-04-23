"""
Compare human labels to the model's predictions on a hand-labeled sample.

Reads the CSV produced by ``scripts/sample_for_labeling.py`` after
``human_category`` has been filled in, and produces a paper-grade
accuracy report: per-class precision / recall / F1, confusion matrix,
the specific disagreements, and an overall agreement rate.

This is the *honest* categorizer accuracy metric — it's the first
number in the whole pipeline that isn't derived from rule-generated
labels. Documents the evaluation in ``docs/human_eval.md`` by default.

Usage
-----
    python scripts/score_human_labels.py labeling/sample.csv
    python scripts/score_human_labels.py labeling/sample.csv --write-md
"""
from __future__ import annotations

import argparse
import csv
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

from categorizer.taxonomy import SLUGS

ROOT = Path(__file__).parent.parent
DEFAULT_OUT = ROOT / "docs" / "human_eval.md"

VALID_SLUGS = set(SLUGS)


def _load_labeled(path: Path) -> tuple[list[dict], list[str]]:
    """Return (labeled_rows, issues) where issues is a list of human-readable
    problems (unlabeled rows, invalid slugs) worth surfacing before scoring."""
    if not path.exists():
        print(f"ERROR: {path} not found.", file=sys.stderr)
        sys.exit(1)

    rows: list[dict] = []
    issues: list[str] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            hc = (row.get("human_category") or "").strip()
            if not hc:
                issues.append(f"sample_id={row.get('sample_id')}: no human_category")
                continue
            if hc.upper() == "SKIP":
                continue
            if hc not in VALID_SLUGS:
                issues.append(
                    f"sample_id={row.get('sample_id')}: "
                    f"invalid human_category={hc!r} "
                    f"(did you typo? valid: {', '.join(sorted(VALID_SLUGS)[:4])}, ...)"
                )
                continue
            rows.append(row)
    return rows, issues


def _confusion(rows: list[dict], labels: list[str]) -> dict:
    """Build confusion matrix dict[actual][predicted] -> count."""
    cm: dict[str, dict[str, int]] = {a: {p: 0 for p in labels} for a in labels}
    for r in rows:
        a = r["human_category"]
        p = r["model_category"]
        if a in cm and p in cm[a]:
            cm[a][p] += 1
        elif a in cm:
            cm[a].setdefault(p, 0)
            cm[a][p] += 1
    return cm


def _per_class(rows: list[dict], labels: list[str]) -> dict:
    """Per-class precision / recall / f1 / support, computed from human
    labels as ground truth."""
    tp: dict[str, int] = {c: 0 for c in labels}
    fp: dict[str, int] = {c: 0 for c in labels}
    fn: dict[str, int] = {c: 0 for c in labels}
    support: dict[str, int] = {c: 0 for c in labels}

    for r in rows:
        a, p = r["human_category"], r["model_category"]
        if a == p:
            tp.setdefault(a, 0); tp[a] += 1
        else:
            fp.setdefault(p, 0); fp[p] += 1
            fn.setdefault(a, 0); fn[a] += 1
        support.setdefault(a, 0); support[a] += 1

    out: dict[str, dict] = {}
    for c in labels:
        p = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) else 0.0
        r = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        out[c] = {"precision": p, "recall": r, "f1": f1, "support": support[c]}
    return out


def _render_report(
    path: Path, rows: list[dict], issues: list[str]
) -> list[str]:
    total = len(rows)
    if total == 0:
        return ["# Human-label evaluation\n", "_No rows with valid human_category — nothing to score._"]

    correct = sum(1 for r in rows if r["human_category"] == r["model_category"])
    accuracy = correct / total

    labels = sorted({r["human_category"] for r in rows} | {r["model_category"] for r in rows})
    metrics = _per_class(rows, labels)
    cm = _confusion(rows, labels)

    lines: list[str] = []
    lines.append("# Human-Label Evaluation — Categorizer Agreement\n")
    lines.append(
        f"Source: `{path.relative_to(ROOT) if path.is_absolute() else path}`  \n"
        f"Rows scored: **{total}** (human_category filled, not SKIP, valid slug)\n"
    )

    if issues:
        lines.append("## Data-quality notes")
        for it in issues[:30]:
            lines.append(f"- {it}")
        if len(issues) > 30:
            lines.append(f"- _(…{len(issues) - 30} more)_")
        lines.append("")

    lines.append("## Headline\n")
    lines.append(f"- Overall agreement (accuracy): **{accuracy * 100:.1f}%** "
                 f"({correct}/{total})")

    # Macro averages computed over categories that have human support > 0
    supported = [c for c in labels if metrics[c]["support"] > 0]
    if supported:
        macro_p = sum(metrics[c]["precision"] for c in supported) / len(supported)
        macro_r = sum(metrics[c]["recall"]    for c in supported) / len(supported)
        macro_f = sum(metrics[c]["f1"]        for c in supported) / len(supported)
        lines.append(f"- Macro precision: **{macro_p:.3f}**")
        lines.append(f"- Macro recall:    **{macro_r:.3f}**")
        lines.append(f"- Macro F1:        **{macro_f:.3f}**")
    lines.append("")

    lines.append("## Per-category metrics\n")
    lines.append("| Category | Support (human) | Precision | Recall | F1 |")
    lines.append("|---|---:|---:|---:|---:|")
    for c in sorted(labels, key=lambda k: -metrics[k]["support"]):
        m = metrics[c]
        if m["support"] == 0 and not any(
            r["model_category"] == c for r in rows
        ):
            continue
        lines.append(
            f"| {c} | {m['support']} | "
            f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |"
        )
    lines.append("")

    lines.append("## Confusion matrix (rows = human, cols = model)\n")
    col_w = max(4, max((len(c) for c in labels), default=4))
    header = "actual \\ predicted".ljust(col_w) + "  " + "  ".join(
        c.ljust(col_w) for c in labels
    )
    lines.append("```")
    lines.append(header)
    for a in labels:
        row_vals = [str(cm.get(a, {}).get(p, 0)).ljust(col_w) for p in labels]
        lines.append(a.ljust(col_w) + "  " + "  ".join(row_vals))
    lines.append("```\n")

    # Disagreements worth reviewing
    disagreements = [r for r in rows if r["human_category"] != r["model_category"]]
    if disagreements:
        lines.append(f"## Disagreements ({len(disagreements)})\n")
        lines.append("These are the rows where the model disagrees with the "
                     "human label. Review them for categorizer-rule or "
                     "labeling issues.\n")
        lines.append("| sample_id | human | model | amount | sms_text (snippet) |")
        lines.append("|---|---|---|---:|---|")
        for r in disagreements[:40]:
            sms = (r.get("sms_text") or "").replace("|", "/")
            if len(sms) > 90:
                sms = sms[:90] + "…"
            lines.append(
                f"| {r['sample_id']} | {r['human_category']} | "
                f"{r['model_category']} | {r.get('amount', '')} | {sms} |"
            )
        if len(disagreements) > 40:
            lines.append(f"\n_(…{len(disagreements) - 40} more disagreements)_")
        lines.append("")

    lines.append("## Paper framing\n")
    lines.append(
        "This is the first categorizer-accuracy number in the pipeline "
        "that is not derived from rule-generated labels. Human labeling "
        "was performed by a single annotator (Alex); inter-annotator "
        "agreement (Cohen's κ) on a held-out slice with a second "
        "annotator remains outstanding work, flagged as item #20 in "
        "[docs/improvements.md](improvements.md). The accuracy here is "
        "therefore a lower-bound generalization estimate — subject to "
        "labeler bias — and is honest in a way the auto-labeled "
        "evaluation in [ml_evaluation.md](ml_evaluation.md) cannot be.\n"
    )

    return lines


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("csv_path", type=Path,
                    help="Path to the labeled CSV (from sample_for_labeling.py)")
    ap.add_argument("--write-md", action="store_true",
                    help=f"Also write report to {DEFAULT_OUT.relative_to(ROOT)}")
    args = ap.parse_args()

    rows, issues = _load_labeled(args.csv_path)
    report = "\n".join(_render_report(args.csv_path, rows, issues))
    print(report)

    if args.write_md:
        DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT.write_text(report, encoding="utf-8")
        print(f"\n-> Written to {DEFAULT_OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
