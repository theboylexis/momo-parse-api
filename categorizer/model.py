"""
Layer 2 — ML categorization model.

Uses a Random Forest classifier trained on features extracted from parsed
transactions. The trained model is persisted to categorizer/model.pkl so it
can be loaded at API startup without retraining.

Train:  python -m categorizer.train
"""
from __future__ import annotations

import os
import pickle
from typing import Optional

import numpy as np

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
_model = None  # lazy-loaded singleton


def _load() -> object:
    global _model
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found: {_MODEL_PATH}. "
                "Run `python -m categorizer.train` to train the model."
            )
        with open(_MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model


def predict(features: np.ndarray) -> tuple[str, float]:
    """
    Predict category for a single feature vector.
    Returns (category_slug, confidence) where confidence is the
    max class probability from the Random Forest.
    """
    clf = _load()
    X = features.reshape(1, -1)
    proba = clf.predict_proba(X)[0]
    idx = int(np.argmax(proba))
    slug = clf.classes_[idx]
    confidence = float(proba[idx])
    return slug, confidence


def is_trained() -> bool:
    return os.path.exists(_MODEL_PATH)


def save(clf) -> None:
    with open(_MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    global _model
    _model = clf
