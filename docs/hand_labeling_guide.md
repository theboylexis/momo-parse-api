# Hand-Labeling Guide — Human-Label Evaluation

This is the workflow for producing the first honest categorizer-accuracy number in the pipeline. Every other ML evaluation so far has used rule-generated labels, which means the model scores well by rediscovering the labeling rules that fed the features (see the closed-loop section in [ml_evaluation.md](ml_evaluation.md)). Only human labels break that loop.

You are annotator 1. A second annotator (for Cohen's κ / inter-annotator agreement) is future work — flagged as item #20 in [improvements.md](improvements.md). For the paper's v1, single-annotator accuracy is a meaningful lower-bound number and is honest if presented as such.

---

## Workflow at a glance

```
1. Generate sample          →  python scripts/sample_for_labeling.py
2. Label in spreadsheet     →  labeling/sample.csv  (fill in human_category)
3. Score                    →  python scripts/score_human_labels.py labeling/sample.csv --write-md
4. Commit the scored report →  docs/human_eval.md
```

Expect ~1.5–2 hours of focused labeling for 150 rows.

---

## Step 1 — Generate the sample

```bash
python scripts/sample_for_labeling.py
```

This pulls ~150 rows from the real corpus, re-runs each SMS through the current parser + categorizer (so the model's predictions reflect today's code, not stale labels), stratifies by predicted category so rare classes get at least 3 rows each, and writes `labeling/sample.csv`.

Override the defaults if needed:

```bash
python scripts/sample_for_labeling.py --n 200 --seed 7
```

---

## Step 2 — Label

Open `labeling/sample.csv` in your spreadsheet tool of choice (Excel, LibreOffice Calc, Google Sheets). For each row:

1. Read `sms_text`. Names and phone numbers appear as `name_<hex>` and `ph_<hex>` — they've been hashed at import, so you're labeling on structure and semantic cues, not the identity of the counterparty.
2. Look at the model's guess in `model_category`.
3. In `human_category`, write **the slug** (not the human-readable label) of what you think the correct category is. One of:

| Slug | When to use |
|---|---|
| `sales_revenue` | Payment received for goods or services sold — you were the seller |
| `supplier_payment` | Payment sent to a vendor for supplies |
| `wages_salary` | Salary / wage / stipend (received or sent) |
| `transport` | Uber, Bolt, trotro, taxi, fuel, fare |
| `airtime_data` | MoMo airtime or data bundle purchase |
| `utilities` | ECG, GWCL, water, electricity, internet, WiFi |
| `rent` | Rent, landlord, accommodation, room |
| `loan_disbursement` | Loan funds received |
| `loan_repayment` | Loan repayment sent |
| `cash_deposit` | Cash deposited at an agent into the wallet |
| `cash_withdrawal` | Cash withdrawn at an agent from the wallet |
| `personal_transfer_sent` | Money sent to a person (not a merchant) |
| `personal_transfer_received` | Money received from a person (not a merchant) |
| `merchant_payment` | Paid to a registered merchant, store, business, service provider |
| `fee_charge` | Standalone transaction fee, tax, or platform charge |
| `uncategorized` | Cannot tell confidently — use when the SMS genuinely doesn't indicate a category |

If a row isn't a real transaction (marketing text that somehow got through, notification-only, unparseable), write `SKIP` in `human_category` and it's excluded from scoring.

`notes` is optional — useful when the model's wrong and you want to remember why you disagreed.

**Tips:**

- **Be strict but fair.** If the SMS says `Reference: rent` and the counterparty name is a person, `rent` beats `personal_transfer_sent`. If it says `to GHANA WATER`, it's `utilities` not `personal_transfer_sent`.
- **Trust the taxonomy definitions above.** When torn between two slugs, pick the one whose description fits best.
- **Airtime is specifically MoMo airtime.** A payment to "MTN VODAFONE PUSH" or "Ecobank" is *merchant_payment*, not airtime — even if MTN formats the SMS like an airtime SMS.
- **When you really can't tell, use `uncategorized`.** This is more honest than forcing a label.

---

## Step 3 — Score

Save the spreadsheet back to the same CSV file (keep encoding as UTF-8). Then:

```bash
python scripts/score_human_labels.py labeling/sample.csv --write-md
```

This prints and writes [docs/human_eval.md](human_eval.md) with:

- Overall agreement (accuracy) between your labels and the model
- Macro precision / recall / F1
- Per-category breakdown — which categories the model does well on vs. badly on
- Confusion matrix (rows = your labels, cols = model's predictions)
- The specific disagreements — each row where you and the model differ, with SMS snippet, so you can review and decide whether the model is wrong or whether *you* should relabel

If you find disagreements that look like labeling mistakes on your end, correct them in the CSV and re-run the scorer — it's iterative.

---

## What the number means, honestly

The resulting "agreement rate" is a *single-annotator* accuracy estimate. It is:

- **Lower-bound honest** — if you agreed on X%, that's the floor under how accurate the categorizer is on your interpretation of the taxonomy.
- **Not inter-annotator agreement** — that requires a second independent labeler and is still outstanding (item #20 in [improvements.md](improvements.md)).
- **Not a general-population number** — labeler bias (your interpretation of edge cases) directly shapes it. A second annotator from a different background may label some edges differently.

For the paper, cite it as "single-annotator agreement on a stratified 150-row real-SMS sample" and flag the κ gap clearly in the limitations section. That framing is defensible.

---

## When to regenerate the sample

Rerun `sample_for_labeling.py` if:

- The parser or categorizer changed substantially (new templates, new rules, retrained model)
- The corpus expanded with a new data source
- You want a larger sample for stronger statistics

Each regeneration is seed-reproducible: pin the seed if you want to re-label the exact same sample, change the seed if you want a fresh draw.
