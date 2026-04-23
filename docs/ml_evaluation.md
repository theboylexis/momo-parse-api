# MomoParse Categorizer — ML Evaluation

Deterministic evaluation harness for the transaction categorizer. Seed = 42. Stratified 20/80 train/test split; 5-fold stratified cross-validation on the training portion; baselines compared on the same splits.

## Dataset

- Samples: **7194**
- Categories: **15**
- Min class frequency: **14**
- Max class frequency: **1608**

| Category | Count | Share |
|---|---:|---:|
| uncategorized | 1608 | 22.4% |
| personal_transfer_sent | 1156 | 16.1% |
| personal_transfer_received | 1114 | 15.5% |
| airtime_data | 967 | 13.4% |
| cash_withdrawal | 804 | 11.2% |
| utilities | 437 | 6.1% |
| loan_repayment | 436 | 6.1% |
| merchant_payment | 432 | 6.0% |
| supplier_payment | 58 | 0.8% |
| wages_salary | 51 | 0.7% |
| sales_revenue | 36 | 0.5% |
| rent | 31 | 0.4% |
| transport | 26 | 0.4% |
| loan_disbursement | 24 | 0.3% |
| cash_deposit | 14 | 0.2% |

### Provenance

| Source | Count | Share |
|---|---:|---:|
| real | 994 | 13.8% |
| synthetic | 6200 | 86.2% |

## 5-fold cross-validation (weighted F1)

| Model | Folds | Weighted F1 (mean ± std) | Macro F1 (mean ± std) | Accuracy (mean ± std) |
|---|---:|---:|---:|---:|
| RandomForest (production) | 5 | 1.000 ± 0.000 | 0.999 ± 0.002 | 1.000 ± 0.000 |
| LogisticRegression | 5 | 1.000 ± 0.000 | 0.999 ± 0.002 | 1.000 ± 0.000 |
| MultinomialNB | 5 | 0.995 ± 0.001 | 0.995 ± 0.002 | 0.995 ± 0.001 |
| Majority-class | 5 | 0.082 ± 0.000 | 0.024 ± 0.000 | 0.224 ± 0.000 |

## Held-out test set — production Random Forest

- Train / test: **5755 / 1439** samples
- Accuracy:    **1.000**
- Weighted F1: **1.000**
- Macro F1:    **1.000**

### Classification report (per-class)

```
                            precision    recall  f1-score   support

              airtime_data      1.000     1.000     1.000       194
              cash_deposit      1.000     1.000     1.000         3
           cash_withdrawal      1.000     1.000     1.000       161
         loan_disbursement      1.000     1.000     1.000         5
            loan_repayment      1.000     1.000     1.000        87
          merchant_payment      1.000     1.000     1.000        86
personal_transfer_received      1.000     1.000     1.000       223
    personal_transfer_sent      1.000     1.000     1.000       231
                      rent      1.000     1.000     1.000         6
             sales_revenue      1.000     1.000     1.000         7
          supplier_payment      1.000     1.000     1.000        12
                 transport      1.000     1.000     1.000         5
             uncategorized      1.000     1.000     1.000       322
                 utilities      1.000     1.000     1.000        87
              wages_salary      1.000     1.000     1.000        10

                  accuracy                          1.000      1439
                 macro avg      1.000     1.000     1.000      1439
              weighted avg      1.000     1.000     1.000      1439
```

### Confusion matrix (counts)

```
actual \ predicted          airtime_data  cash_deposit  cash_withdrawal  loan_disbursement  loan_repayment  merchant_payment  personal_transfer_received  personal_transfer_sent  rent  sales_revenue  supplier_payment  transport  uncategorized  utilities  wages_salary
airtime_data                194   0     0     0     0     0     0     0     0     0     0     0     0     0     0   
cash_deposit                0     3     0     0     0     0     0     0     0     0     0     0     0     0     0   
cash_withdrawal             0     0     161   0     0     0     0     0     0     0     0     0     0     0     0   
loan_disbursement           0     0     0     5     0     0     0     0     0     0     0     0     0     0     0   
loan_repayment              0     0     0     0     87    0     0     0     0     0     0     0     0     0     0   
merchant_payment            0     0     0     0     0     86    0     0     0     0     0     0     0     0     0   
personal_transfer_received  0     0     0     0     0     0     223   0     0     0     0     0     0     0     0   
personal_transfer_sent      0     0     0     0     0     0     0     231   0     0     0     0     0     0     0   
rent                        0     0     0     0     0     0     0     0     6     0     0     0     0     0     0   
sales_revenue               0     0     0     0     0     0     0     0     0     7     0     0     0     0     0   
supplier_payment            0     0     0     0     0     0     0     0     0     0     12    0     0     0     0   
transport                   0     0     0     0     0     0     0     0     0     0     0     5     0     0     0   
uncategorized               0     0     0     0     0     0     0     0     0     0     0     0     322   0     0   
utilities                   0     0     0     0     0     0     0     0     0     0     0     0     0     87    0   
wages_salary                0     0     0     0     0     0     0     0     0     0     0     0     0     0     10  
```

## Real-only held-out evaluation

Trains on `synthetic + real_train` and evaluates on a held-out slice of **real** SMS only. This was originally intended as the generalization metric, but both labels and features in this pipeline are rule-derived from the same raw signals (see limitation section below), so a near-perfect score here is expected and does not demonstrate generalization. The section is retained because it still catches distributional surprises — any real row that fails here is a sign the labeling rules and feature encoding have diverged on real data.

- Synthetic training rows: **6200**
- Real training rows:      **792**
- Real test rows:          **199**
- Accuracy:                **1.000**
- Weighted F1:             **1.000**
- Macro F1:                **1.000**
- Real classes excluded (fewer than 2 real samples): loan_repayment, sales_revenue, wages_salary

### Per-class report on real held-out

```
                            precision    recall  f1-score   support

              airtime_data      1.000     1.000     1.000        34
              cash_deposit      1.000     1.000     1.000         3
           cash_withdrawal      1.000     1.000     1.000         1
          merchant_payment      1.000     1.000     1.000         6
personal_transfer_received      1.000     1.000     1.000        38
    personal_transfer_sent      1.000     1.000     1.000        49
             uncategorized      1.000     1.000     1.000         2
                 utilities      1.000     1.000     1.000        66

                  accuracy                          1.000       199
                 macro avg      1.000     1.000     1.000       199
              weighted avg      1.000     1.000     1.000       199
```

### Confusion matrix on real held-out

```
actual \ predicted          airtime_data  cash_deposit  cash_withdrawal  merchant_payment  personal_transfer_received  personal_transfer_sent  uncategorized  utilities
airtime_data                34    0     0     0     0     0     0     0   
cash_deposit                0     3     0     0     0     0     0     0   
cash_withdrawal             0     0     1     0     0     0     0     0   
merchant_payment            0     0     0     6     0     0     0     0   
personal_transfer_received  0     0     0     0     38    0     0     0   
personal_transfer_sent      0     0     0     0     0     49    0     0   
uncategorized               0     0     0     0     0     0     2     0   
utilities                   0     0     0     0     0     0     0     66  
```

## Interpretation

- The production Random Forest is compared against three baselines (Logistic Regression, Multinomial Naive Bayes, and a majority-class DummyClassifier) on the same stratified splits and the same feature vector. The majority-class row is the trivial baseline — any useful model should clearly exceed it.
- This evaluation is read-only. It does not overwrite `categorizer/model.pkl`; re-run `python -m categorizer.train` for that.

## Known evaluation limitation — rule-derived labels

Both the labels and the features in this pipeline are deterministic functions of the same raw signals:

- **Labels** come from `categorizer/label_corpus.py::_label()`, which maps `tx_type + keywords in {reference, counterparty_name}` to a category.
- **Features** in `categorizer/features.py` one-hot-encode `tx_type` and flag the same keywords on the same text.

Any classifier that can learn a simple piecewise rule will therefore score near-perfectly on this evaluation — even on held-out real SMS, because the labels on those rows were generated by the same rules whose inputs the features expose. High F1 here is evidence that the ML layer faithfully approximates the rule system; it is **not** evidence of generalization to a human-labeled ground truth.

**What a paper-honest evaluation requires.** A sample of real SMS (the `real` rows in the corpus are a natural candidate) must be hand-labeled by a human annotator blind to the rule system. The meaningful generalization metric is the model's agreement with human labels, not with auto-generated labels. Inter-annotator agreement on that sample would additionally quantify label noise. Both are flagged as outstanding items in `docs/improvements.md`.

**What this evaluation does tell us.** (1) The labeling rule set is internally consistent — features carry enough signal to reconstruct labels, so no rule is fighting the feature representation. (2) The model will not regress below the rule system it approximates, which is the operational floor. (3) Baseline comparison is preserved: MultinomialNB and majority-class DummyClassifier scoring well below RF/LogReg on the original 406-sample labeled set remained the best evidence the feature representation carries learnable structure.
