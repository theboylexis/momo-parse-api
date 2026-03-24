# ML Model Benchmark — MomoParse Categorizer

## Model Choice: RandomForest

**Why RandomForest over alternatives:**

| Model | Pros | Cons | Suitability |
|-------|------|------|-------------|
| **RandomForest** (chosen) | Handles small datasets well, interpretable feature importances, robust to outliers, no hyperparameter sensitivity | Can overfit on small data, larger model size | Best fit for current data size (406 samples) |
| Logistic Regression | Fast, interpretable coefficients, good baseline | Poor with non-linear boundaries, needs feature scaling | Good baseline but weaker on multi-class with sparse categories |
| Gradient Boosting (XGBoost) | Higher accuracy ceiling, handles imbalance | Requires more tuning, overfits faster on small data, less interpretable | Overkill for 406 samples, better when dataset grows |
| Neural Network (MLP) | Learns complex patterns, scales well | Needs thousands of samples, black box, slow to train | Not viable at current data size |
| Naive Bayes | Very fast, works with tiny datasets | Strong independence assumption, poor with correlated features | Viable alternative, worth benchmarking |

**Decision rationale:** At 406 labeled samples with 15 categories (6 of which have <10 samples), RandomForest provides the best balance of accuracy, interpretability, and robustness. The `class_weight="balanced"` parameter compensates for class imbalance without requiring synthetic oversampling.

## Current Performance

**Dataset:** 406 labeled transactions, 15 categories

### Category Distribution

| Category | Count | % | Status |
|----------|-------|---|--------|
| personal_transfer_sent | 120 | 29.6% | Well-represented |
| personal_transfer_received | 98 | 24.1% | Well-represented |
| merchant_payment | 58 | 14.3% | Well-represented |
| airtime_data | 38 | 9.4% | Adequate |
| cash_withdrawal | 34 | 8.4% | Adequate |
| uncategorized | 20 | 4.9% | Adequate |
| wages_salary | 9 | 2.2% | Underrepresented |
| utilities | 8 | 2.0% | Underrepresented |
| loan_repayment | 7 | 1.7% | Underrepresented |
| supplier_payment | 5 | 1.2% | Underrepresented |
| transport | 3 | 0.7% | Critical — too few |
| cash_deposit | 2 | 0.5% | Critical — too few |
| sales_revenue | 2 | 0.5% | Critical — too few |
| rent | 1 | 0.2% | Critical — too few |
| loan_disbursement | 1 | 0.2% | Critical — too few |

### Training Metrics (full dataset)

- **Accuracy:** 100% (on training data — expected for RF with small data)
- **Weighted F1:** 1.00 (train set — NOT indicative of generalization)
- **Cross-validation:** Skipped — 5 categories have <2 samples, making stratified k-fold impossible

### Top 10 Feature Importances

| Feature | Importance | Signal |
|---------|-----------|--------|
| kw_food | 0.098 | Keyword match for food-related references |
| amount_bucket | 0.084 | Transaction amount range |
| kw_loan | 0.076 | Keyword match for loan references |
| tx_transfer_received | 0.067 | Transaction type: received |
| kw_salary | 0.064 | Keyword match for salary references |
| tx_merchant_payment | 0.059 | Transaction type: merchant |
| tx_cash_in | 0.057 | Transaction type: cash deposit |
| tx_transfer_sent | 0.054 | Transaction type: sent |
| kw_transport | 0.054 | Keyword match for transport references |
| kw_rent | 0.047 | Keyword match for rent references |

**Observation:** Feature importances are well-distributed — no single feature dominates. The model relies on a combination of transaction type (from parser) and reference keywords (from SMS text), which mirrors how a human would categorize transactions.

## Honest Limitations

1. **No held-out test set.** With 406 samples and severe class imbalance, a train/test split would leave some categories with 0 test samples. The 100% train accuracy is meaningless for generalization claims.

2. **Cross-validation impossible.** 5 categories have <2 samples. Stratified k-fold requires at least `k` samples per class.

3. **Overfitting risk.** RandomForest with `max_depth=None` on 406 samples will memorize the training data. The model likely overfits to the specific SMS templates in the corpus.

4. **Category imbalance.** The top 3 categories (transfer_sent, transfer_received, merchant_payment) account for 68% of data. Rare categories (rent, loan_disbursement, sales_revenue) have 1-2 samples each — the model cannot reliably learn these.

5. **Corpus bias.** Training data comes from a single SMS corpus, likely from one or two users. Real-world distribution will differ.

## Improvement Roadmap

### Short-term (current project scope)
- [ ] Collect more labeled data — target 50+ samples per category
- [ ] Run proper 5-fold CV once all categories have >= 5 samples
- [ ] Benchmark against Logistic Regression and Naive Bayes as baselines
- [ ] Report precision/recall per category on a held-out test set

### Medium-term (post-capstone)
- [ ] Implement counterparty learning as a complementary Layer 1 (already built)
- [ ] Add confidence calibration — model's `predict_proba` outputs may not reflect true confidence
- [ ] Evaluate Gradient Boosting once dataset exceeds 1,000 samples

### Long-term (production)
- [ ] Continuous learning from user corrections
- [ ] A/B testing of model versions
- [ ] Category taxonomy expansion based on real user transaction patterns

## How This Maps to Telco Scoring

The ML categorizer is not a credit scoring model — it's the **preprocessing layer** that transforms unstructured SMS data into the structured categories that the financial indexes operate on.

```
SMS Text → Parser (rule-based) → Categorizer (ML) → Financial Indexes → Health Score
                                      ↑
                              This benchmark covers this layer
```

The categorizer's accuracy directly impacts the quality of:
- Income vs. expense classification (affects savings rate, expense ratio)
- Spending category breakdown (affects counterparty concentration, expense volatility)
- Loan detection (affects risk signals)

A miscategorized transaction propagates through the entire scoring pipeline.
