"""
Auto-label the SMS corpus for training.

Rules applied (in priority order):
  1. Direct tx_type mappings (high confidence)
  2. Keyword signals in reference / counterparty_name
  3. Default fallback for transfer_sent → personal_transfer_sent
                         transfer_received → personal_transfer_received

Run once to generate:  categorizer/labeled_data.csv
"""
from __future__ import annotations

import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))

# ── Keyword patterns ──────────────────────────────────────────────────────────

_RENT     = re.compile(r"\b(rent|house|apartment|landlord|accommodation|room)\b", re.I)
_SALARY   = re.compile(r"\b(salary|wage|wages|payroll|stipend|allowance)\b", re.I)
_TRANSPORT= re.compile(r"\b(transport|uber|bolt|taxi|fare|fuel|trotro|bus)\b", re.I)
_UTILITY  = re.compile(r"\b(electricity|ecg|gwcl|water|utility|internet|wifi)\b", re.I)
_SUPPLIER = re.compile(r"\b(supplier|vendor|wholesale|goods|stock|supply|invoice|shop|store)\b", re.I)
_LOAN     = re.compile(r"\b(loan|borrow|credit|advance|repay|installment)\b", re.I)
_FOOD     = re.compile(r"\b(food|chop|rice|market|grocery|produce|veggie)\b", re.I)

_DIRECT: dict[str, str] = {
    "airtime_purchase":  "airtime_data",
    "airtime_received":  "airtime_data",
    "cash_in":           "cash_deposit",
    "cash_out":          "cash_withdrawal",
    "cash_withdrawal":   "cash_withdrawal",
    "cash_deposit":      "cash_deposit",
    "merchant_payment":  "merchant_payment",
    "bill_payment":      "utilities",
    "loan_repayment":    "loan_repayment",
    "loan_disbursement": "loan_disbursement",
    "fee":               "fee_charge",
    "wallet_balance":    "uncategorized",
}


def _label(tx_type: str, reference: str, counterparty: str, amount: str) -> str:
    tx = tx_type.lower().strip()

    if tx in _DIRECT:
        return _DIRECT[tx]

    text = f"{reference} {counterparty}".strip()

    if tx in ("transfer_sent", "payment_sent", "bank_transfer"):
        if _RENT.search(text):     return "rent"
        if _SALARY.search(text):   return "wages_salary"
        if _TRANSPORT.search(text): return "transport"
        if _UTILITY.search(text):  return "utilities"
        if _SUPPLIER.search(text): return "supplier_payment"
        if _LOAN.search(text):     return "loan_repayment"
        if _FOOD.search(text):     return "supplier_payment"
        return "personal_transfer_sent"

    if tx in ("transfer_received", "payment_received"):
        if _LOAN.search(text):     return "loan_disbursement"
        if _SALARY.search(text):   return "wages_salary"
        if _SUPPLIER.search(text): return "sales_revenue"
        if _FOOD.search(text):     return "sales_revenue"
        return "personal_transfer_received"

    return "uncategorized"


def run():
    corpus_files = [
        os.path.join(ROOT, "corpus", "real_sms_corpus.csv"),
        os.path.join(ROOT, "corpus", "synthetic_sms_corpus.csv"),
    ]

    out_path = os.path.join(ROOT, "categorizer", "labeled_data.csv")
    written = 0
    skipped = 0

    with open(out_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow([
            "raw_sms", "telco", "tx_type", "amount",
            "counterparty_name", "counterparty_phone",
            "balance", "fee", "reference", "category"
        ])

        for path in corpus_files:
            if not os.path.exists(path):
                print(f"  SKIP (not found): {path}", file=sys.stderr)
                continue

            with open(path, newline="", encoding="utf-8") as fin:
                reader = csv.DictReader(fin)
                for row in reader:
                    tx_type = row.get("tx_type", "").strip()
                    if not tx_type or tx_type == "tx_type":
                        skipped += 1
                        continue

                    category = _label(
                        tx_type,
                        row.get("reference", ""),
                        row.get("counterparty_name", ""),
                        row.get("amount", ""),
                    )

                    writer.writerow([
                        row.get("raw_sms", ""),
                        row.get("telco", ""),
                        tx_type,
                        row.get("amount", ""),
                        row.get("counterparty_name", ""),
                        row.get("counterparty_phone", ""),
                        row.get("balance", ""),
                        row.get("fee", ""),
                        row.get("reference", ""),
                        category,
                    ])
                    written += 1

    print(f"Labeled {written} rows -> {out_path}  (skipped {skipped})")


if __name__ == "__main__":
    run()
