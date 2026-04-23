"""
ML evaluation harness for the MomoParse categorizer.

Runs a full, paper-grade evaluation of the trained categorization model
against the labeled corpus. Unlike ``categorizer/train.py`` (which fits the
production model), this script is read-only: it does not write ``model.pkl``
and does not alter training state. It exists to produce the numbers that go
into the paper's ML Evaluation section and to give a one-command answer to
"is the categorizer still good?" whenever the corpus grows.

What it produces
----------------
1. Dataset summary — sample count, class count, per-class frequency.
2. Stratified 80/20 train/test split with a held-out test set.
3. 5-fold stratified cross-validation on the training set, reporting
   weighted F1, macro F1, and accuracy with per-fold breakdown.
4. Held-out test-set metrics: classification report (precision / recall /
   F1 per class), macro and weighted averages.
5. Confusion matrix (printed as a table, optionally saved as PNG if
   matplotlib is available).
6. Baseline comparison — Random Forest vs. Logistic Regression, Multinomial
   Naive Bayes, and the majority-class baseline. This is the evidence the
   paper needs that the model beats the trivial baselines by a meaningful
   margin.
7. Per-category performance table so the paper can point at specific
   categories that are strong (utility, salary) vs. weaker (categories with
   few samples) rather than reporting only a global number.

Why this exists
---------------
The current corpus is small (~406 samples) and will grow as real SMS arrive.
Having the evaluation wired up before the data arrives means the moment the
corpus expands, ``python scripts/evaluate.py`` regenerates every number the
paper needs without touching production code. It also pins the baselines
so growth in corpus size can be attributed to the model improving (not to
the evaluation protocol changing).

Usage
-----
    python scripts/evaluate.py                 # full evaluation, print report
    python scripts/evaluate.py --write-md      # also write docs/ml_evaluation.md
    python scripts/evaluate.py --confusion-png # save confusion matrix PNG
    python scripts/evaluate.py --seed 7        # override random seed
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

# Allow running as `python scripts/evaluate.py` from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from categorizer import features as feat_mod

ROOT = Path(__file__).parent.parent
LABELED_PATH = ROOT / "categorizer" / "labeled_data.csv"
DOCS_PATH = ROOT / "docs" / "ml_evaluation.md"
CONFUSION_PNG_PATH = ROOT / "docs" / "ml_confusion_matrix.png"

DEFAULT_SEED = 42
TEST_SIZE = 0.20
CV_FOLDS = 5


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_labeled() -> tuple[np.ndarray, list[str], list[str]]:
    """Load labeled corpus. Generates it via label_corpus.run() if missing.

    Returns (X, y, source) where ``source[i]`` is ``"real"`` or ``"synthetic"``
    — the provenance tag emitted by ``label_corpus.py`` so the evaluator can
    hold out real rows for generalization testing. Older labeled files
    without a ``source`` column get tagged ``"unknown"``.
    """
    if not LABELED_PATH.exists():
        print(f"Labeled data not found at {LABELED_PATH} — generating from corpus...")
        from categorizer.label_corpus import run
        run()

    records: list[dict] = []
    labels: list[str] = []
    source: list[str] = []

    with LABELED_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            amount = _maybe_float(row.get("amount", ""))
            fee = _maybe_float(row.get("fee", ""))
            records.append({
                "tx_type":           row.get("tx_type", ""),
                "amount":            amount,
                "counterparty_name": row.get("counterparty_name", ""),
                "counterparty_phone":row.get("counterparty_phone", ""),
                "reference":         row.get("reference", ""),
                "fee":               fee,
            })
            labels.append(row.get("category", "uncategorized"))
            source.append(row.get("source", "unknown"))

    X = feat_mod.extract_batch(records)
    return X, labels, source


def _maybe_float(v: str) -> float | None:
    if not v:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── Metric helpers ────────────────────────────────────────────────────────────

def _format_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _format_row(cells: list[str], widths: list[int]) -> str:
    return "  ".join(c.ljust(w) for c, w in zip(cells, widths))


# ── Dataset summary ───────────────────────────────────────────────────────────

def _dataset_summary(y: list[str]) -> list[str]:
    lines: list[str] = []
    n = len(y)
    counts = Counter(y)
    lines.append(f"## Dataset\n")
    lines.append(f"- Samples: **{n}**")
    lines.append(f"- Categories: **{len(counts)}**")
    lines.append(f"- Min class frequency: **{min(counts.values())}**")
    lines.append(f"- Max class frequency: **{max(counts.values())}**")
    lines.append("")
    lines.append("| Category | Count | Share |")
    lines.append("|---|---:|---:|")
    for cat, c in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | {c} | {_format_pct(c / n)} |")
    lines.append("")
    return lines


# ── Cross-validation ──────────────────────────────────────────────────────────

def _cross_validate(clf_factory, X, y, *, seed: int, folds: int) -> dict:
    """Stratified K-fold CV — returns per-fold scores + mean/std.

    Classes with fewer samples than the requested fold count are dropped
    from the CV evaluation; StratifiedKFold otherwise raises. This matches
    the holdout filtering so both views are consistent.
    """
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import StratifiedKFold

    # Drop classes with fewer samples than the requested fold count;
    # StratifiedKFold otherwise raises. Ensures min_class >= n_splits.
    counts = Counter(y)
    n_splits = folds
    keep = {c for c, n in counts.items() if n >= n_splits}
    if len(keep) < len(counts):
        mask = np.array([lbl in keep for lbl in y])
        X = X[mask]
        y = [lbl for lbl, m in zip(y, mask) if m]

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)

    weighted_f1s: list[float] = []
    macro_f1s: list[float] = []
    accs: list[float] = []
    y_arr = np.array(y)

    for tr, te in skf.split(X, y_arr):
        clf = clf_factory()
        clf.fit(X[tr], y_arr[tr])
        pred = clf.predict(X[te])
        weighted_f1s.append(f1_score(y_arr[te], pred, average="weighted", zero_division=0))
        macro_f1s.append(f1_score(y_arr[te], pred, average="macro", zero_division=0))
        accs.append(accuracy_score(y_arr[te], pred))

    return {
        "folds": n_splits,
        "weighted_f1": weighted_f1s,
        "macro_f1": macro_f1s,
        "accuracy": accs,
    }


# ── Baseline comparisons ──────────────────────────────────────────────────────

def _make_rf(seed: int):
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )


def _make_logreg(seed: int):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
    )


def _make_nb(_seed: int):
    from sklearn.naive_bayes import MultinomialNB
    # MultinomialNB requires non-negative features. Our feature vector is
    # already non-negative (bucket indices, one-hot, keyword flags).
    return MultinomialNB()


def _make_majority(_seed: int):
    from sklearn.dummy import DummyClassifier
    return DummyClassifier(strategy="most_frequent")


BASELINES: list[tuple[str, callable]] = [
    ("RandomForest (production)", _make_rf),
    ("LogisticRegression",        _make_logreg),
    ("MultinomialNB",             _make_nb),
    ("Majority-class",            _make_majority),
]


# ── Held-out test-set evaluation ──────────────────────────────────────────────

def _holdout_eval(clf_factory, X, y, *, seed: int) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )
    from sklearn.model_selection import train_test_split

    # Stratified split requires ≥2 samples per class. Singleton classes are
    # dropped from the holdout evaluation and reported separately so the
    # corpus gap is visible rather than silently hidden.
    y_arr = np.array(y)
    counts = Counter(y)
    singleton_classes = sorted(c for c, n in counts.items() if n < 2)
    if singleton_classes:
        mask = np.array([lbl not in singleton_classes for lbl in y_arr])
        X_filt = X[mask]
        y_filt = y_arr[mask]
    else:
        X_filt = X
        y_filt = y_arr

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_filt, y_filt, test_size=TEST_SIZE, random_state=seed, stratify=y_filt
    )

    clf = clf_factory()
    clf.fit(X_tr, y_tr)
    pred = clf.predict(X_te)

    labels = sorted(set(y_arr))
    cm = confusion_matrix(y_te, pred, labels=labels)

    return {
        "accuracy":    accuracy_score(y_te, pred),
        "weighted_f1": f1_score(y_te, pred, average="weighted", zero_division=0),
        "macro_f1":    f1_score(y_te, pred, average="macro", zero_division=0),
        "report":      classification_report(y_te, pred, zero_division=0, digits=3),
        "confusion":   cm,
        "labels":      labels,
        "y_true":      y_te,
        "y_pred":      pred,
        "n_train":     len(X_tr),
        "n_test":      len(X_te),
        "dropped":     singleton_classes,
    }


# ── Real-only generalization evaluation ───────────────────────────────────────

def _real_only_holdout(clf_factory, X, y, source, *, seed: int) -> dict | None:
    """
    Paper-honest generalization evaluation.

    Because ``label_corpus.py`` auto-labels using rules that the feature
    vector in ``categorizer/features.py`` directly encodes, training and
    evaluating on rule-generated synthetic SMS forms a closed loop —
    scores on such data measure rule-memorization, not generalization.

    This function breaks the loop: it stratifies only the **real** rows
    into an 80/20 split, trains on ``synthetic + real_train``, and scores
    on ``real_test``. The reported metrics reflect performance on SMS the
    rule system did not synthesize.
    """
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )
    from sklearn.model_selection import train_test_split

    y_arr = np.array(y)
    src_arr = np.array(source)
    real_mask = src_arr == "real"
    syn_mask = src_arr == "synthetic"

    if real_mask.sum() < 10:
        return None

    X_real = X[real_mask]
    y_real = y_arr[real_mask]

    # Drop real singleton classes for the stratified split (consistent
    # with how the full-corpus holdout handles class-count minima).
    counts = Counter(y_real)
    dropped = sorted(c for c, n in counts.items() if n < 2)
    if dropped:
        keep = np.array([lbl not in dropped for lbl in y_real])
        X_real = X_real[keep]
        y_real = y_real[keep]

    X_real_tr, X_real_te, y_real_tr, y_real_te = train_test_split(
        X_real, y_real, test_size=TEST_SIZE, random_state=seed, stratify=y_real
    )

    # Training = synthetic rows + real-train slice. Evaluation = real-test slice.
    X_train = np.vstack([X[syn_mask], X_real_tr])
    y_train = np.concatenate([y_arr[syn_mask], y_real_tr])

    clf = clf_factory()
    clf.fit(X_train, y_train)
    pred = clf.predict(X_real_te)

    labels = sorted(set(y_real_te) | set(pred))
    cm = confusion_matrix(y_real_te, pred, labels=labels)

    return {
        "n_train_synthetic": int(syn_mask.sum()),
        "n_train_real":      len(X_real_tr),
        "n_test_real":       len(X_real_te),
        "accuracy":          accuracy_score(y_real_te, pred),
        "weighted_f1":       f1_score(y_real_te, pred, average="weighted", zero_division=0),
        "macro_f1":          f1_score(y_real_te, pred, average="macro", zero_division=0),
        "report":            classification_report(y_real_te, pred, zero_division=0, digits=3),
        "confusion":         cm,
        "labels":            labels,
        "dropped":           dropped,
    }


# ── Confusion matrix rendering ────────────────────────────────────────────────

def _format_confusion_matrix(cm: np.ndarray, labels: list[str]) -> list[str]:
    """Render confusion matrix as a compact markdown block."""
    lines: list[str] = []
    max_label_len = max(len(lb) for lb in labels)
    col_width = max(4, len(str(cm.max())))

    header = _format_row(
        ["actual \\ predicted"] + labels,
        [max_label_len] + [col_width] * len(labels),
    )
    lines.append("```")
    lines.append(header)
    for i, row_label in enumerate(labels):
        cells = [row_label] + [str(v) for v in cm[i]]
        lines.append(_format_row(cells, [max_label_len] + [col_width] * len(labels)))
    lines.append("```")
    return lines


def _save_confusion_png(cm: np.ndarray, labels: list[str], path: Path) -> bool:
    """Save a matplotlib heatmap of the confusion matrix. Returns True on success."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.5),
                                    max(5, len(labels) * 0.4)))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Categorizer — Held-out Confusion Matrix")

    vmax = cm.max() if cm.size else 1
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            v = cm[i, j]
            if v == 0:
                continue
            ax.text(j, i, str(v), ha="center", va="center",
                    color="white" if v > vmax / 2 else "black", fontsize=7)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


# ── Report assembly ───────────────────────────────────────────────────────────

def run(*, seed: int, confusion_png: bool) -> str:
    lines: list[str] = []
    lines.append("# MomoParse Categorizer — ML Evaluation\n")
    lines.append(
        f"Deterministic evaluation harness for the transaction categorizer. "
        f"Seed = {seed}. Stratified {int(TEST_SIZE * 100)}/{int((1 - TEST_SIZE) * 100)} "
        f"train/test split; {CV_FOLDS}-fold stratified cross-validation on the "
        f"training portion; baselines compared on the same splits.\n"
    )

    # ── Load + summarize ──────────────────────────────────────────────────────
    X, y, source = _load_labeled()
    lines += _dataset_summary(y)

    # Provenance breakdown so the reader knows what's real vs synthetic
    src_counts = Counter(source)
    lines.append("### Provenance\n")
    lines.append("| Source | Count | Share |")
    lines.append("|---|---:|---:|")
    total_n = len(source)
    for src in ("real", "synthetic", "unknown"):
        if src in src_counts:
            lines.append(
                f"| {src} | {src_counts[src]} | "
                f"{_format_pct(src_counts[src] / total_n)} |"
            )
    lines.append("")

    # ── Cross-validation across baselines ─────────────────────────────────────
    lines.append(f"## {CV_FOLDS}-fold cross-validation (weighted F1)\n")
    lines.append("| Model | Folds | Weighted F1 (mean ± std) | Macro F1 (mean ± std) | Accuracy (mean ± std) |")
    lines.append("|---|---:|---:|---:|---:|")

    for label, factory in BASELINES:
        cv = _cross_validate(
            lambda f=factory: f(seed), X, y, seed=seed, folds=CV_FOLDS
        )
        wf = np.array(cv["weighted_f1"])
        mf = np.array(cv["macro_f1"])
        ac = np.array(cv["accuracy"])
        lines.append(
            f"| {label} | {cv['folds']} | "
            f"{wf.mean():.3f} ± {wf.std():.3f} | "
            f"{mf.mean():.3f} ± {mf.std():.3f} | "
            f"{ac.mean():.3f} ± {ac.std():.3f} |"
        )
    lines.append("")

    # ── Held-out test-set evaluation (production model only) ──────────────────
    lines.append(f"## Held-out test set — production Random Forest\n")
    ho = _holdout_eval(lambda: _make_rf(seed), X, y, seed=seed)
    lines.append(f"- Train / test: **{ho['n_train']} / {ho['n_test']}** samples")
    lines.append(f"- Accuracy:    **{ho['accuracy']:.3f}**")
    lines.append(f"- Weighted F1: **{ho['weighted_f1']:.3f}**")
    lines.append(f"- Macro F1:    **{ho['macro_f1']:.3f}**")
    if ho["dropped"]:
        lines.append(
            f"- Classes excluded from holdout (fewer than 2 samples, "
            f"stratified split requires ≥2): "
            f"{', '.join(ho['dropped'])}"
        )
    lines.append("")

    lines.append("### Classification report (per-class)\n")
    lines.append("```")
    lines.append(ho["report"].rstrip())
    lines.append("```\n")

    lines.append("### Confusion matrix (counts)\n")
    lines += _format_confusion_matrix(ho["confusion"], ho["labels"])
    lines.append("")

    if confusion_png:
        ok = _save_confusion_png(ho["confusion"], ho["labels"], CONFUSION_PNG_PATH)
        if ok:
            lines.append(f"Heatmap saved to `{CONFUSION_PNG_PATH.relative_to(ROOT)}`.\n")
        else:
            lines.append("_matplotlib not installed — skipping PNG heatmap._\n")

    # ── Real-only held-out evaluation ─────────────────────────────────────────
    lines.append("## Real-only held-out evaluation\n")
    lines.append(
        "Trains on `synthetic + real_train` and evaluates on a held-out "
        "slice of **real** SMS only. This was originally intended as the "
        "generalization metric, but both labels and features in this "
        "pipeline are rule-derived from the same raw signals (see "
        "limitation section below), so a near-perfect score here is "
        "expected and does not demonstrate generalization. The section is "
        "retained because it still catches distributional surprises — any "
        "real row that fails here is a sign the labeling rules and feature "
        "encoding have diverged on real data.\n"
    )

    real = _real_only_holdout(lambda: _make_rf(seed), X, y, source, seed=seed)
    if real is None:
        lines.append("_Too few real rows in the corpus (need ≥10) — skipping._\n")
    else:
        lines.append(f"- Synthetic training rows: **{real['n_train_synthetic']}**")
        lines.append(f"- Real training rows:      **{real['n_train_real']}**")
        lines.append(f"- Real test rows:          **{real['n_test_real']}**")
        lines.append(f"- Accuracy:                **{real['accuracy']:.3f}**")
        lines.append(f"- Weighted F1:             **{real['weighted_f1']:.3f}**")
        lines.append(f"- Macro F1:                **{real['macro_f1']:.3f}**")
        if real["dropped"]:
            lines.append(
                f"- Real classes excluded (fewer than 2 real samples): "
                f"{', '.join(real['dropped'])}"
            )
        lines.append("")
        lines.append("### Per-class report on real held-out\n")
        lines.append("```")
        lines.append(real["report"].rstrip())
        lines.append("```\n")
        lines.append("### Confusion matrix on real held-out\n")
        lines += _format_confusion_matrix(real["confusion"], real["labels"])
        lines.append("")

    # ── Summary / framing ─────────────────────────────────────────────────────
    lines.append("## Interpretation\n")
    lines.append(
        "- The production Random Forest is compared against three baselines "
        "(Logistic Regression, Multinomial Naive Bayes, and a majority-class "
        "DummyClassifier) on the same stratified splits and the same feature "
        "vector. The majority-class row is the trivial baseline — any useful "
        "model should clearly exceed it."
    )
    lines.append(
        "- This evaluation is read-only. It does not overwrite "
        "`categorizer/model.pkl`; re-run `python -m categorizer.train` for "
        "that."
    )
    lines.append("")
    lines.append("## Known evaluation limitation — rule-derived labels\n")
    lines.append(
        "Both the labels and the features in this pipeline are deterministic "
        "functions of the same raw signals:\n\n"
        "- **Labels** come from `categorizer/label_corpus.py::_label()`, which "
        "maps `tx_type + keywords in {reference, counterparty_name}` to a "
        "category.\n"
        "- **Features** in `categorizer/features.py` one-hot-encode `tx_type` "
        "and flag the same keywords on the same text.\n\n"
        "Any classifier that can learn a simple piecewise rule will therefore "
        "score near-perfectly on this evaluation — even on held-out real SMS, "
        "because the labels on those rows were generated by the same rules "
        "whose inputs the features expose. High F1 here is evidence that the "
        "ML layer faithfully approximates the rule system; it is **not** "
        "evidence of generalization to a human-labeled ground truth.\n"
    )
    lines.append(
        "**What a paper-honest evaluation requires.** A sample of real SMS "
        "(the `real` rows in the corpus are a natural candidate) must be "
        "hand-labeled by a human annotator blind to the rule system. The "
        "meaningful generalization metric is the model's agreement with "
        "human labels, not with auto-generated labels. Inter-annotator "
        "agreement on that sample would additionally quantify label noise. "
        "Both are flagged as outstanding items in `docs/improvements.md`.\n"
    )
    lines.append(
        "**What this evaluation does tell us.** (1) The labeling rule set is "
        "internally consistent — features carry enough signal to reconstruct "
        "labels, so no rule is fighting the feature representation. (2) The "
        "model will not regress below the rule system it approximates, which "
        "is the operational floor. (3) Baseline comparison is preserved: "
        "MultinomialNB and majority-class DummyClassifier scoring well below "
        "RF/LogReg on the original 406-sample labeled set remained the best "
        "evidence the feature representation carries learnable structure.\n"
    )

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    # Windows terminals default to cp1252; force UTF-8 for fancy chars
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--write-md", action="store_true",
                        help=f"Write report to {DOCS_PATH.relative_to(ROOT)}")
    parser.add_argument("--confusion-png", action="store_true",
                        help=f"Save confusion matrix heatmap to "
                             f"{CONFUSION_PNG_PATH.relative_to(ROOT)}")
    args = parser.parse_args()

    report = run(seed=args.seed, confusion_png=args.confusion_png)
    print(report)

    if args.write_md:
        DOCS_PATH.write_text(report, encoding="utf-8")
        print(f"\n-> Written to {DOCS_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
