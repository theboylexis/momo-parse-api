"""
Train the ML categorization model and print accuracy benchmarks.

Usage:
    python -m categorizer.train

Outputs:
    categorizer/model.pkl       — trained RandomForest
    categorizer/labeled_data.csv — auto-labeled training data (if not already present)
"""
from __future__ import annotations

import csv
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(__file__))
LABELED_PATH = os.path.join(os.path.dirname(__file__), "labeled_data.csv")


def _load_data() -> tuple[np.ndarray, list[str]]:
    from categorizer import features as feat_mod

    if not os.path.exists(LABELED_PATH):
        print("Labeled data not found — generating from corpus...")
        from categorizer.label_corpus import run
        run()

    records: list[dict] = []
    labels: list[str] = []

    with open(LABELED_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            amount = None
            try:
                v = row.get("amount", "")
                if v:
                    amount = float(v)
            except (ValueError, TypeError):
                pass

            fee = None
            try:
                v = row.get("fee", "")
                if v:
                    fee = float(v)
            except (ValueError, TypeError):
                pass

            records.append({
                "tx_type":           row.get("tx_type", ""),
                "amount":            amount,
                "counterparty_name": row.get("counterparty_name", ""),
                "counterparty_phone":row.get("counterparty_phone", ""),
                "reference":         row.get("reference", ""),
                "fee":               fee,
            })
            labels.append(row.get("category", "uncategorized"))

    X = feat_mod.extract_batch(records)
    return X, labels


def train():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    from categorizer import model as model_mod

    print("Loading labeled data...")
    X, y = _load_data()
    y_arr = np.array(y)

    print(f"Dataset: {len(y)} samples, {len(set(y))} categories")
    print("\nCategory distribution:")
    from collections import Counter
    for cat, count in sorted(Counter(y).items(), key=lambda x: -x[1]):
        pct = count / len(y) * 100
        print(f"  {cat:<35} {count:>4}  ({pct:.1f}%)")

    # ── Train final model ─────────────────────────────────────────────────────
    print("\nTraining Random Forest...")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    # ── 5-fold cross-validation ───────────────────────────────────────────────
    # Only run CV if we have enough samples per class
    min_class_count = min(Counter(y).values())
    n_splits = min(5, min_class_count)

    if n_splits >= 2:
        print(f"\nRunning {n_splits}-fold cross-validation...")
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(clf, X, y_arr, cv=skf, scoring="f1_weighted", n_jobs=-1)
        print(f"  Cross-val weighted F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        cv_min = cv_scores.min()
        if cv_min < 0.70:
            print(f"  WARNING: lowest fold F1 = {cv_min:.3f} — more labeled data recommended")
    else:
        print("  Skipping CV (too few samples per class for stratified split)")

    # Fit on full dataset
    clf.fit(X, y_arr)

    # ── Full-data classification report ──────────────────────────────────────
    y_pred = clf.predict(X)
    print("\nClassification report (train set — for inspection, not validation):")
    print(classification_report(y_arr, y_pred, zero_division=0))

    # ── Feature importance ────────────────────────────────────────────────────
    from categorizer.features import FEATURE_NAMES
    importances = clf.feature_importances_
    top_n = 10
    top_idx = np.argsort(importances)[::-1][:top_n]
    print(f"\nTop {top_n} feature importances:")
    for i in top_idx:
        name = FEATURE_NAMES[i] if i < len(FEATURE_NAMES) else f"feat_{i}"
        print(f"  {name:<35} {importances[i]:.4f}")

    # ── Save ──────────────────────────────────────────────────────────────────
    model_mod.save(clf)
    print(f"\nModel saved -> {model_mod._MODEL_PATH}")


if __name__ == "__main__":
    train()
