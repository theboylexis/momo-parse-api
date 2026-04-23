# Template Drift Benchmark for Regex-Based SMS Parsers

A reproducible benchmark that measures a regex-based mobile-money SMS parser's ability to withstand realistic telco-side format drift. Each telco-registered template is subjected to a catalogue of seven curated mutations that mirror format changes observed in production (verb swaps, currency-symbol drift, field reordering, whitespace bloat, SMS truncation, label abbreviation, promo injection). The parser must continue to recover the fields that downstream credit scoring consumes: `amount`, `tx_type`, `telco`, `balance`.

Implemented in [tests/test_drift.py](../tests/test_drift.py). Runs as part of the regular test suite.

---

## Why this benchmark exists

Rule-based SMS parsing is the dominant approach for mobile-money intelligence in low-bandwidth and low-trust environments because regex templates are auditable, cheap to run, and do not depend on server-side model deployment. Their central failure mode is well-known but rarely measured: **format drift**. Telcos revise their SMS templates without notice — a verb swap, a reordered clause, a swapped currency symbol — and a template that covered 100% of a transaction type yesterday may silently drop 30% of it today. In a credit-scoring pipeline, silent drops don't trigger errors: they corrupt aggregate indexes (savings rate, income stability, counterparty concentration) without any loud signal that something has changed.

Most parser test suites cover only the nominal case — "given this exact SMS, extract these fields." This benchmark closes the blind spot. It forces the parser to prove it can survive the specific drift patterns telcos actually produce, and documents those patterns in a form the broader alt-credit-scoring community can adopt.

---

## Mutation catalogue

Seven mutations, each modelled on an observed telco behaviour. All deterministic, all reversible (the clean SMS is preserved; the mutation is applied in isolation). Random character-level mutations are deliberately excluded — they represent noise, not the real threat surface.

| Mutation | Operational definition | Paper-framed intuition |
|---|---|---|
| `verb_swap` | Replace a transaction verb with a synonym not present in any current template (e.g. `sent to → moved to`, `Payment made for → Payment moved for`). | Telcos routinely revise action-verb phrasing between template versions. |
| `currency_drift` | Replace the `GHS` currency code with the cedi sign `GH¢`. | Inconsistent currency rendering across telcos and over time. |
| `field_reorder` | Move the `Fee` clause to appear before the `Balance` clause. | Trailing metadata is reordered across template revisions. |
| `whitespace_bloat` | Inject double spaces after currency markers and colon terminators. | A common telco-side typo; trips whitespace-tight regex patterns. |
| `truncation` | Cut the trailing marketing or reference tail, preserving amount and balance. | SMS 160-char limit or network-side truncation. |
| `tx_id_label` | Abbreviate the transaction-ID label (`Transaction ID: → Trn ID:`). | Internal reference labels are frequently shortened. |
| `promo_injection` | Insert a new marketing phrase mid-message. | Telcos inject campaign text without altering the template ID. |

Each mutation self-reports whether it applies to a given SMS; inapplicable cases are skipped, not failed — a mutation can only be tested on SMS where its trigger is present.

---

## Test protocol

For each (telco, template) registered with an `example` SMS and an amount-bearing `tx_type`, and for each mutation:

1. Parse the **clean** example to capture ground truth for `amount`, `tx_type`, and `balance`.
2. Apply the mutation to produce a drifted SMS.
3. Parse the drifted SMS.
4. Assert all of the following:
   - `telco` is preserved
   - `match_mode ∈ {exact, fuzzy}` — never a silent drop (`none`)
   - `amount` equals the ground-truth amount (to float precision)
   - `tx_type` equals the ground-truth `tx_type`
   - `confidence ∈ (0, 1]`
   - When `match_mode == fuzzy`, `confidence ≤ FUZZY_CONFIDENCE_CAP` (currently 0.6)

A second test asserts that `balance` survives specifically under `verb_swap` — balance is the single most-consumed field by the downstream Financial Health Index. A smoke test asserts that `promo_injection` never yields `match_mode == none` on any amount-bearing template.

Every failure message prints the mutation name, template ID, final match mode, attempted fields, and a snippet of the mutated SMS — so a regression points at exactly which template × mutation pair needs a template revision.

---

## Current scope

As of this writing:

- **26 amount-bearing templates** across MTN (n=10) and Telecel (n=16)
- **7 mutations**, each applied where triggers are present
- **209 collected test cases** in total (26 × 7 drift cases + 26 balance-under-verb-swap cases + 1 universal promo smoke test)

The test suite is parametrized with pytest's product of `_TEMPLATE_CASES × _MUTATIONS`, so new templates added to `configs/*.json` are automatically covered and new mutations added to `_MUTATIONS` automatically apply to every template. This makes the benchmark extensible without amending the test body.

---

## Pass criteria and the fuzzy fallback

A parser passes the benchmark when every (template, mutation) pair succeeds under the invariants above. Passes are allowed via either exact regex match **or** the parser's fuzzy fallback path — the benchmark does not prescribe *how* the parser recovers, only that it recovers the downstream-critical fields.

The fuzzy fallback is capped at confidence ≤ 0.6 by design: a fuzzy recovery is a signal that an exact template should be revised, and the cap ensures downstream consumers can filter fuzzy transactions if they require high-confidence input. Every fuzzy fallback additionally emits a structured `parse.fuzzy_fallback` telemetry event so production drift is observable and aggregatable, not just testable.

---

## How to run

```bash
python -m pytest tests/test_drift.py -v
```

To collect without running (for case counts):

```bash
python -m pytest tests/test_drift.py --collect-only -q
```

---

## Reproducibility

- **Deterministic.** No randomness in the mutations or the test ordering. Same input SMS → same mutated SMS → same parse result.
- **Self-contained.** Depends only on the public `parser` package and the JSON template configs in `configs/`.
- **Version-pinned.** The benchmark's behaviour moves with the parser; pinning the `momoparse` package version pins the benchmark.

To re-create the exact benchmark results reported in a given paper version, check out that commit and re-run — no external data, no downloaded fixtures, no network dependencies.

---

## Limitations

1. **Curated, not generative.** The mutation set is fixed, modelled on observed telco drift. It does not cover every conceivable format change; it covers the ones we have reason to believe occur in production.
2. **Not a fuzzer.** Character-level noise and adversarial SMS are out of scope. This is a drift benchmark, not a robustness-to-noise benchmark.
3. **Ghana-specific.** The mutation catalogue is drawn from MTN and Telecel SMS formats. Telcos in other jurisdictions may exhibit different drift patterns.
4. **Does not test the ML categorizer.** The benchmark stops at `tx_type`; whether a correctly-extracted transaction gets correctly categorized is a separate concern evaluated in [ml_benchmark.md](ml_benchmark.md).
5. **No per-mutation severity weighting.** All mutations are treated equally; in practice some (truncation, promo injection) are more common than others. Real-world drift rates would need production telemetry to calibrate.

---

## Future work

- **Expand telco coverage.** Add MoMo platforms from other jurisdictions (e.g. Safaricom M-Pesa, Airtel Money) to test generalization of the mutation catalogue itself.
- **Automated mutation discovery.** Mine the `parse.fuzzy_fallback` telemetry stream in production to surface drift patterns the benchmark does not yet cover, then formalize them into new `_MUTATIONS` entries.
- **Severity weighting from production frequencies.** Weight each mutation by its observed rate in production, so the overall pass rate reflects real user exposure.
- **Cross-parser comparison.** Package the benchmark as an importable artifact so other MoMo-SMS parsers (open source and commercial) can be evaluated on the same mutation set.

---

## Paper framing (section 7 — Validation)

> We introduce a deterministic drift benchmark that subjects every telco-registered template to seven curated mutations modelling observed format-drift patterns: verb substitution, currency-symbol drift, field reordering, whitespace bloat, SMS truncation, label abbreviation, and promo injection. The benchmark asserts that parser output preserves the fields consumed by downstream credit scoring (`amount`, `tx_type`, `telco`, `balance`) under every applicable mutation. At the time of writing, the benchmark comprises 209 test cases across 26 amount-bearing templates and passes in full. The benchmark is parametrized over the template configuration directory, so the case count grows automatically as new templates are registered, and over the mutation catalogue, so new drift patterns can be added without modifying test logic. This is, to our knowledge, the first published drift benchmark specifically targeting regex-based mobile-money SMS parsers — a class of system whose silent-failure mode (format drift producing silent drops rather than loud errors) has been qualitatively acknowledged in the alt-credit-scoring literature but not systematically measured.
