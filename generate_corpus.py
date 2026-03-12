#!/usr/bin/env python3
"""
MomoParse Synthetic SMS Data Generator
=======================================
Generates 310+ realistic MoMo SMS messages for MTN MoMo and Telecel Cash
based on real templates extracted from actual transaction screenshots.

Output: corpus/synthetic_sms_corpus.csv

Columns:
  raw_sms, telco, tx_type, amount, counterparty_name,
  counterparty_phone, balance, fee, tx_id, reference, dest_network

Usage:
  python generate_corpus.py
"""

import csv
import os
import random
import string
from collections import Counter
from datetime import datetime, timedelta

random.seed(42)

# ─── Name / reference pools (derived from real screenshots) ──────────────────

FIRST_NAMES = [
    "KWAME", "KOFI", "KWEKU", "AMA", "ABENA", "AKUA", "YAW", "KWABENA",
    "ADJOA", "EFUA", "NANA", "ADWOA", "AGYEI", "BOATENG", "MENSAH",
    "ASANTE", "AMOAH", "OWUSU", "AMPONSAH", "ANTWI", "FRIMPONG",
    "OBENG", "AGYEMANG", "DARKWAH", "ASARE", "NYAME", "APPIAH",
    "ASAMOAH", "OSEI", "BONSU", "ACHEAMPONG", "NIMAKO", "SARFO",
    "BAAH", "ODURO", "AIDOO", "AMANKWAH", "BAFFOUR", "FORSON",
    "OPOKU", "GYIMAH", "ASIEDU", "TAWIAH", "ADUSEI", "BEDIAKO",
    "OFORI", "KYEI", "DONKOR", "DADZIE", "PEPRAH", "BOAKYE",
    "YEBOAH", "SARPONG", "MANASSEH", "JONATHAN", "CECILIA", "THERESA",
    "GEORGE", "ROSE", "RAMSFIELD", "ADWOBA", "JANET", "GRACE",
    "CATHERINE", "MABEL", "MARTHA", "LOUISA", "DAVID", "PETER",
    "ERNEST", "LOVE", "MUHSINA", "RABIATU", "ABDULLAH", "IBRAHIM",
    "FATIMA", "HAJIA", "FELIX", "SAMUEL", "EMMANUEL", "BEATRICE",
    "JOSEPHINE", "AUGUSTINE", "RICHARD", "STEPHEN", "VICTORIA",
]

LAST_NAMES = [
    "BOATENG", "OWUSU", "MENSAH", "ASANTE", "AMOAH", "NYAME",
    "APPIAH", "OSEI", "FRIMPONG", "OBENG", "ANTWI", "AGYEMANG",
    "ASARE", "BONSU", "FORSON", "GYIMAH", "TAWIAH", "AIDOO",
    "OPOKU", "BAFFOUR", "DARKO", "SARPONG", "YEBOAH", "BOAKYE",
    "SARFO", "AMPONSAH", "ASAMOAH", "ACHEAMPONG", "NIMAKO", "BAAH",
    "ADOMAKO", "DOKO", "GYASI", "NKRUMAH", "ANDOH", "SAEED",
    "ZIBLIM", "ABUBAKARI", "ABDUL-MUMIN", "AMEYAW", "EFFAH",
    "ANKRAH", "ADUSEI", "DARKWAH", "KYEI", "DADZIE", "PEPRAH",
    "DONKOR", "OFORI", "QUAYE", "TAGOE", "NORTEY", "LARYEA",
    "BERKO", "BEDIAKO", "ODURO", "AMANKWAH", "ASIEDU",
]

BUSINESS_NAMES = [
    "FOEJOE ENTERPRISE", "EXPRESSPAY", "UNIQUE PLASS ENT.",
    "ADWOBA CATERING SERVICES", "BOAFO MICROFINANCE LIMITED",
    "PETRA SECURITIES", "CBG", "GOLD COAST TRADING",
    "KUMASI MARKET SUPPLIES", "ACCRA TRADERS", "MAAME AMA VENTURES",
    "BRIGHT FUTURES LTD", "KOFI BROBBEY STORES", "OSEI VENTURES",
    "AGYEMANG ENTERPRISE", "WEST AFRICA TEXTILES", "TEN ELEVEN MART",
    "SUNRISE BAKERY", "GHANA SEEDS LTD", "APOA CONSTRUCTION",
]

TELECEL_AGENT_CODES = ["A00433", "A25736", "A11205", "A44678", "A09321", "A87654", "A31290"]
MTN_AGENT_CODES = ["A25736", "A31204", "A44521", "A12088", "A67432", "A09871", "A55234"]

BANK_ACCOUNTS = [
    ("STANBIC BANK ACCOUNT", "9040013268597"),
    ("GCB BANK ACCOUNT", "1011234567890"),
    ("ABSA ACCOUNT", "9050045678123"),
    ("FIDELITY BANK ACCOUNT", "2030089123456"),
    ("ECOBANK ACCOUNT", "3040156789012"),
    ("CALBANK ACCOUNT", "4050234567890"),
]

# short_code → merchant label
MERCHANT_REGISTRY = {
    "749000": "Inv.Debit",
    "735000": "EXPRESSPAY",
    "400100": "ECG PREPAID",
    "711":    "GHANA WATER",
    "400200": "DSTV GHANA",
    "900200": "MULTICHOICE GH",
    "800100": "NHIS GHANA",
}

REFERENCES = [
    "Alex", "1", "2006", "thess", "internet", "support money", "Godlove",
    "veggies", "oil", "abele", "drink", "cake", "Deposit", "indomie",
    "Ken", "Apple Music", "food", "rent", "school fees", "medical",
    "transport", "water bill", "electricity", "business", "salary",
    "market", "shopping", "birthday", "emergency", "loan", "savings",
    ".", "-", "n", "Q", "K",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def rname():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    if random.random() < 0.25:
        mid = random.choice(FIRST_NAMES)
        return f"{first} {mid} {last}"
    return f"{first} {last}"


def mtn_phone():
    prefix = random.choice(["024", "025", "053", "054", "055", "059"])
    return prefix + "".join(random.choices(string.digits, k=7))


def telecel_phone():
    prefix = random.choice(["020", "050"])
    return prefix + "".join(random.choices(string.digits, k=7))


def to_intl(phone: str) -> str:
    """0XXXXXXXXX → 233XXXXXXXXX"""
    return "233" + phone[1:]


def rand_amount(lo=5.0, hi=1000.0) -> float:
    amt = round(random.uniform(lo, hi), 2)
    if random.random() < 0.35:          # bias toward round numbers
        amt = round(amt)
    return amt


def fmt_amt(v: float) -> str:
    """Format with comma-thousands for >= 1000"""
    if v >= 1000:
        return f"{v:,.2f}"
    return f"{v:.2f}"


def rand_balance(lo=1.0, hi=3000.0) -> float:
    return round(random.uniform(lo, hi), 2)


def tcash_txid() -> str:
    """Telecel: 16 digits starting with 000001"""
    return "000001" + "".join(random.choices(string.digits, k=10))


def mtn_txid() -> str:
    """MTN: 11 digits starting with 7"""
    return "7" + "".join(random.choices(string.digits, k=10))


def rand_dt() -> datetime:
    start = datetime(2025, 6, 1)
    end   = datetime(2026, 3, 12)
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))


def fdate(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def ftime(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


def tcash_fee(amount: float, dest: str = "mtn") -> float:
    """Approximate Telecel Cash outbound fee schedule."""
    if dest in ("telecel", "merchant"):
        return 0.00
    if dest == "bank":
        if amount <= 100:   return round(random.uniform(0.50, 1.00), 2)
        if amount <= 500:   return round(random.uniform(1.00, 5.00), 2)
        return round(random.uniform(3.00, 10.00), 2)
    # mtn / other
    if amount <= 50:    return round(random.choice([0.00, 0.20, 0.51]), 2)
    if amount <= 100:   return round(random.uniform(0.50, 1.00), 2)
    if amount <= 500:   return round(random.uniform(1.00, 5.00), 2)
    return round(random.uniform(3.00, 10.00), 2)


def mtn_fee(amount: float, tx_type: str = "transfer") -> float:
    if tx_type == "cash_out":
        return round(max(0.50, amount * 0.01), 2)
    if amount <= 50:    return round(random.choice([0.00, 0.50, 1.00]), 2)
    if amount <= 200:   return round(random.uniform(1.00, 2.00), 2)
    return round(random.uniform(1.20, 3.00), 2)


def inv_ref() -> str:
    """Hex-style investment reference like 90e6d0cdx2f1a.."""
    return "".join(random.choices(string.hexdigits.lower(), k=12)) + ".."


def rref() -> str:
    return random.choice(REFERENCES)


# ─── Telecel Templates ────────────────────────────────────────────────────────

def tcash_transfer_sent_mtn():
    tid   = tcash_txid()
    name  = rname()
    phone = mtn_phone()
    amt   = rand_amount(5, 1000)
    dt    = rand_dt()
    bal   = rand_balance(1, 2000)
    fee   = tcash_fee(amt, "mtn")
    ref   = rref()

    # Two slightly different footers observed in real SMS
    if random.random() < 0.7:
        footer = (
            "Sending money from Telecel Cash to Telecel Cash remains FREE on the Telecel Play App. "
            "Download the App https://bit.ly/TelecelPlayGhana and continue to enjoy the convenience.\n"
            f"Reference: {ref}.\nSendi k3k3!"
        )
    else:
        footer = f"Do more with Telecel Cash!\nReference: {ref}.\nSendi k3k3!"

    sms = (
        f"{tid} Confirmed. GHS{amt:.2f} sent to {phone} - {name} on MTN MOBILE MONEY on "
        f"{fdate(dt)} at {ftime(dt)}. Your Telecel Cash balance is GHS{bal:.2f}. "
        f"You were charged GHS{fee:.2f}. Your E-levy charge is GHS0.00. {footer}"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="transfer_sent",
                amount=amt, counterparty_name=name, counterparty_phone=phone,
                balance=bal, fee=fee, tx_id=tid, reference=ref, dest_network="mtn")


def tcash_transfer_sent_telecel():
    tid   = tcash_txid()
    name  = rname()
    phone = telecel_phone()
    amt   = rand_amount(5, 500)
    dt    = rand_dt()
    bal   = rand_balance(1, 2000)
    ref   = rref()

    sms = (
        f"{tid} Confirmed. GHS{amt:.2f} sent to {phone} - {name} on TELECEL CASH on "
        f"{fdate(dt)} at {ftime(dt)}. Your Telecel Cash balance is GHS{bal:.2f}. "
        "You were charged GHS0.00. Your E-levy charge is GHS0.00. "
        "Sending money from Telecel Cash to Telecel Cash remains FREE on the Telecel Play App. "
        "Download the App https://bit.ly/TelecelPlayGhana and continue to enjoy the convenience.\n"
        f"Reference: {ref}.\nSendi k3k3!"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="transfer_sent",
                amount=amt, counterparty_name=name, counterparty_phone=phone,
                balance=bal, fee=0.00, tx_id=tid, reference=ref, dest_network="telecel")


def tcash_transfer_received_mtn():
    tid        = tcash_txid()
    name       = rname()
    phone_intl = to_intl(mtn_phone())
    amt        = rand_amount(5, 1000)
    dt         = rand_dt()
    bal        = rand_balance(1, 3000)
    ref        = rref()

    sms = (
        f"{tid} Confirmed. You have received GHS{amt:.2f} from MTN MOBILE MONEY with transaction "
        f"reference: Transfer From: {phone_intl}-{name} on {fdate(dt)} at {ftime(dt)}. "
        f"Your Telecel Cash balance is GHS{bal:.2f}. Ref: {ref}"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="transfer_received",
                amount=amt, counterparty_name=name, counterparty_phone=phone_intl,
                balance=bal, fee=0.00, tx_id=tid, reference=ref, dest_network="mtn")


def tcash_transfer_received_telecel():
    tid        = tcash_txid()
    name       = rname()
    phone_intl = to_intl(telecel_phone())
    amt        = rand_amount(5, 500)
    dt         = rand_dt()
    bal        = rand_balance(1, 2000)
    ref        = rref()

    sms = (
        f"{tid} Confirmed. You have received GHS{amt:.2f} from {name} on TELECEL CASH on "
        f"{fdate(dt)} at {ftime(dt)}. Your Telecel Cash balance is GHS{bal:.2f}. Ref: {ref}"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="transfer_received",
                amount=amt, counterparty_name=name, counterparty_phone=phone_intl,
                balance=bal, fee=0.00, tx_id=tid, reference=ref, dest_network="telecel")


def tcash_merchant_payment():
    tid  = tcash_txid()
    code = random.choice(list(MERCHANT_REGISTRY.keys()))
    merch = MERCHANT_REGISTRY[code]
    amt  = rand_amount(5, 500)
    dt   = rand_dt()
    bal  = rand_balance(1, 2000)

    if code == "749000":
        ref = "Petra Securities Achieve.."
    elif code == "735000":
        ref = inv_ref()
    else:
        ref = rref()

    sms = (
        f"{tid} Confirmed. GHS{amt:.2f} paid to {code} - {merch} on "
        f"{fdate(dt)} at {ftime(dt)}. Your new Telecel Cash balance is GHS{bal:.2f}. "
        f"You were charged GHS0.00. Your E-levy charge is GHS0.00. "
        f"Reference: {ref}.\nSendi k3k3!"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="merchant_payment",
                amount=amt, counterparty_name=merch, counterparty_phone=code,
                balance=bal, fee=0.00, tx_id=tid, reference=ref, dest_network="merchant")


def tcash_airtime_purchase():
    tid   = tcash_txid()
    phone = telecel_phone()
    amt   = rand_amount(1, 100)
    dt    = rand_dt()
    bal   = rand_balance(1, 1000)

    sms = (
        f"{tid} Confirmed. You bought GHS{amt:.2f} of airtime for {phone} on "
        f"{fdate(dt)} at {ftime(dt)}. Your Telecel Cash balance is GHS{bal:.2f}."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="airtime_purchase",
                amount=amt, counterparty_name="TELECEL AIRTIME", counterparty_phone=phone,
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_airtime_received():
    tid   = tcash_txid()
    name  = rname()
    phone = telecel_phone()
    amt   = rand_amount(1, 100)
    dt    = rand_dt()

    sms = (
        f"Transaction ID: {tid} confirmed from 555. You have received airtime of GHS{amt:.2f} from "
        f"{phone} - {name} on {fdate(dt)} at {ftime(dt)}."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="airtime_received",
                amount=amt, counterparty_name=name, counterparty_phone=phone,
                balance=None, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_cash_withdrawal():
    tid   = tcash_txid()
    agent = random.choice(TELECEL_AGENT_CODES)
    biz   = random.choice(BUSINESS_NAMES)
    amt   = rand_amount(20, 500)
    dt    = rand_dt()
    bal   = rand_balance(1, 1000)

    sms = (
        f"{tid} Confirmed. You have withdrawn GHS{amt:.2f} from {agent} - {biz} on "
        f"{fdate(dt)} at {ftime(dt)}. Your Telecel Cash balance is GHS{bal:.2f}."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="cash_withdrawal",
                amount=amt, counterparty_name=biz, counterparty_phone=agent,
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="agent")


def tcash_bank_transfer():
    tid          = tcash_txid()
    name         = rname()
    bank, acct   = random.choice(BANK_ACCOUNTS)
    amt          = rand_amount(20, 2000)
    dt           = rand_dt()
    bal          = rand_balance(1, 1000)
    fee          = tcash_fee(amt, "bank")
    ref          = rref()

    sms = (
        f"{tid} Confirmed. You have transferred GHS{amt:.2f} to {bank} - "
        f"{acct} - {name} on {fdate(dt)} at {ftime(dt)}. "
        f"Your Telecel Cash balance is GHS{bal:.2f}. "
        f"You were charged GHS{fee:.2f} (Telecel Cash fee GHS{fee:.2f} + E-levy GHS0.00).\n"
        f"Reference: {ref}.\nSendi k3k3!"
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="bank_transfer",
                amount=amt, counterparty_name=name, counterparty_phone=acct,
                balance=bal, fee=fee, tx_id=tid, reference=ref, dest_network="bank")


def tcash_deposit_received():
    tid = tcash_txid()
    biz = random.choice(BUSINESS_NAMES)
    amt = rand_amount(50, 2000)
    dt  = rand_dt()
    bal = rand_balance(50, 3000)

    sms = (
        f"{tid} Confirmed. On {fdate(dt)} at {ftime(dt)}, a deposit of GHS{amt:.2f} was made "
        f"to your account from {biz} . Your balance is GHS{bal:.2f}. "
        "Sending money from Telecel Cash to Telecel Cash remains FREE on the Telecel Play App. "
        "Download the App https://bit.ly/TelecelPlayGhana and continue to enjoy the convenience."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="deposit_received",
                amount=amt, counterparty_name=biz, counterparty_phone="",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_payment_received_expresspay():
    tid = tcash_txid()
    amt = rand_amount(50, 1000)
    dt  = rand_dt()
    bal = rand_balance(50, 2000)

    sms = (
        f"{tid} confirmed. You have received GHS{amt:.2f} as payment from EXPRESSPAY on "
        f"{fdate(dt)} at {ftime(dt)}. Your new Telecel Cash balance is GHS{bal:.2f}."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="payment_received",
                amount=amt, counterparty_name="EXPRESSPAY", counterparty_phone="735000",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_loan_repayment():
    tid = tcash_txid()
    amt = rand_amount(1, 200)
    dt  = rand_dt()
    bal = rand_balance(1, 500)

    charge = random.choice(["default charge", "Principal", "interest charge", "loan repayment fee"])

    if "Principal" in charge:
        sms = (
            f"{tid} confirmed. You have paid off GHS{amt:.2f} Ready Loan Principal from CBG on "
            f"{fdate(dt)} at {ftime(dt)}. Your new Telecel Cash balance is GHS{bal:.2f}."
        )
    else:
        sms = (
            f"{tid} confirmed. You have paid your GHS{amt:.2f} Ready Loan {charge} on "
            f"{fdate(dt)} at {ftime(dt)}. Your new Telecel Cash balance is GHS{bal:.2f}."
        )
    return dict(raw_sms=sms, telco="telecel", tx_type="loan_repayment",
                amount=amt, counterparty_name="CBG READY LOAN", counterparty_phone="",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_interest_received():
    tid = tcash_txid()
    amt = round(random.uniform(0.10, 5.00), 2)
    bal = rand_balance(50, 1000)

    sms = (
        f"Dear customer, you have received GHS{amt:.2f} from Telecel Cash as interest earned "
        f"on your mobile wallet. Your new Telecel Cash balance is GHS{bal:.2f}."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="interest_received",
                amount=amt, counterparty_name="TELECEL CASH", counterparty_phone="",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


def tcash_wallet_balance():
    tid = tcash_txid()
    bal = rand_balance(0, 2000)

    sms = (
        f"{tid} Confirmed. Your Telecel Cash wallet balance is GHS{bal:.2f} . "
        "Sending money from Telecel Cash to Telecel Cash remains FREE on the Telecel Play App. "
        "Download the App https://bit.ly/TelecelPlayGhana and continue to enjoy the convenience."
    )
    return dict(raw_sms=sms, telco="telecel", tx_type="wallet_balance",
                amount=0.00, counterparty_name="", counterparty_phone="",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="telecel")


# ─── MTN Templates ────────────────────────────────────────────────────────────

def mtn_payment_made_v1():
    """Old format — no period after name, GHSx.xx fee style."""
    name  = rname()
    amt   = rand_amount(5, 500)
    bal   = rand_balance(50, 3000)
    fee   = mtn_fee(amt)
    ref   = rref()
    tid   = mtn_txid()
    bal_s = f"GHS {fmt_amt(bal)}"

    # Two sub-variants seen in screenshots
    if random.random() < 0.5:
        tail = (
            f"Fee charged: GHS{fee:.2f} Tax charged: 0. "
            "Download the MoMo App for a Faster & Easier Experience. "
            "Click here: https://bit.ly/downloadMyMoMo"
        )
    else:
        tail = f"Fee charged: GHS{fee:.2f} TAX charged: GHS 0.00."

    sms = (
        f"Payment made for GHS {amt:.2f} to {name} Current Balance: {bal_s} . "
        f"Available Balance: {bal_s} Reference: {ref}. Transaction ID: {tid}. {tail}"
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="transfer_sent",
                amount=amt, counterparty_name=name, counterparty_phone="",
                balance=bal, fee=fee, tx_id=tid, reference=ref, dest_network="mtn")


def mtn_payment_made_v2():
    """Newer format — period after name, spaced fee style."""
    name  = rname()
    amt   = rand_amount(5, 500)
    bal   = rand_balance(50, 3000)
    fee   = mtn_fee(amt)
    ref   = rref()
    tid   = mtn_txid()
    bal_s = f"GHS {fmt_amt(bal)}"

    sms = (
        f"Payment made for GHS {amt:.2f} to {name}. Current Balance: {bal_s}. "
        f"Available Balance: {bal_s}. Reference: {ref}. Transaction ID: {tid}. "
        f"Fee charged: GHS {fee:.2f} TAX charged: GHS 0.00."
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="transfer_sent",
                amount=amt, counterparty_name=name, counterparty_phone="",
                balance=bal, fee=fee, tx_id=tid, reference=ref, dest_network="mtn")


def mtn_payment_received():
    name  = rname()
    phone = mtn_phone()
    amt   = rand_amount(5, 1000)
    bal   = rand_balance(50, 3000)
    tid   = mtn_txid()
    ref   = rref()
    bal_s = f"GHS {fmt_amt(bal)}"

    # Some receipts include the sender's network ("from VODAFONE")
    net_suffix = random.choice(["", " from VODAFONE", " from TELECEL"])
    if net_suffix:
        ref_section = f"Reference: {name},{phone}{net_suffix}."
    else:
        ref_section = f"Reference: {ref}."

    sms = (
        f"Payment received for GHS {amt:.2f} from {name} Current Balance: {bal_s} . "
        f"Available Balance: {bal_s} . {ref_section} Transaction ID: {tid}. TRANSACTION FEE: 0.00"
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="transfer_received",
                amount=amt, counterparty_name=name, counterparty_phone=phone,
                balance=bal, fee=0.00, tx_id=tid, reference=ref, dest_network="mtn")


def mtn_cash_out():
    name  = random.choice([rname(), random.choice(BUSINESS_NAMES)])
    amt   = rand_amount(20, 1000)
    bal   = rand_balance(1, 2000)
    fee   = mtn_fee(amt, "cash_out")
    tid   = mtn_txid()
    bal_s = f"GHS{fmt_amt(bal)}"

    sms = (
        f"Cash Out made for GHS{amt:.2f} to {name}. Current Balance: {bal_s} "
        f"Financial Transaction Id: {tid}. Cash-out fee is charged automatically from your MTN MoMo wallet. "
        "Please do not pay any fees to the Agent. Thank you for using MTN MobileMoney. "
        f"Fee charged: GHS{fee:.2f}."
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="cash_out",
                amount=amt, counterparty_name=name, counterparty_phone="",
                balance=bal, fee=fee, tx_id=tid, reference="", dest_network="agent")


def mtn_airtime_purchase():
    amt = rand_amount(1, 50)
    dt  = rand_dt()
    bal = rand_balance(50, 2000)
    tid = mtn_txid()
    bal_s = f"GHS {fmt_amt(bal)}"

    sms = (
        f"Your payment of GHS {amt:.2f} to MTN AIRTIME has been completed at "
        f"{fdate(dt)} {ftime(dt)}. Your new balance: {bal_s}. "
        f"Fee was GHS 0.00 Tax was GHS -. Reference: -. "
        f"Financial Transaction Id: {tid}. External Transaction Id: {tid}."
        "Download the MoMo App for a Faster & Easier Experience."
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="airtime_purchase",
                amount=amt, counterparty_name="MTN AIRTIME", counterparty_phone="750000",
                balance=bal, fee=0.00, tx_id=tid, reference="-", dest_network="mtn")


def mtn_bundle_purchase():
    amt = random.choice([5.00, 10.00, 15.00, 20.00, 25.00, 30.00, 50.00])
    bal = rand_balance(50, 2000)
    tid = mtn_txid()
    bal_s = f"GHS {fmt_amt(bal)}"

    sms = (
        f"Payment for GHS{amt:.2f} to MTN BUNDLE .Current Balance: {bal_s}. "
        f"Transaction Id: {tid}. Fee charged: GHS0.00,Tax Charged 0 "
        "Download the MoMo App for a Faster & Easier Experience."
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="bundle_purchase",
                amount=amt, counterparty_name="MTN BUNDLE", counterparty_phone="400300",
                balance=bal, fee=0.00, tx_id=tid, reference="", dest_network="mtn")


MTN_MERCHANTS = [
    "FIT N FINE GYM CENTER LIMITED", "GOIL FILLING STATION", "SHOPRITE GHANA",
    "MELCOM GHANA", "PALACE HYPERMARKET", "KFC GHANA", "PIZZA HUT ACCRA",
    "KOALA SUPERMARKET", "GAME STORES GHANA", "ELECTROLAND GHANA",
    "FRANKO TRADING", "SAMSUNG GHANA OFFICIAL", "VODAFONE GHANA",
    "TOTAL PETROLEUM GHANA", "REPUBLIC BANK GHANA", "PAPAYE FAST FOOD",
    "MAXMART SUPERMARKET", "EVERPURE WATER", "LUCKY STAR RESTAURANT",
    "ACCRA MALL PARKING", "STARBITES GHANA", "DE TASTE RESTAURANT",
]


def mtn_merchant_payment():
    """Named merchant payment — 'Your payment of GHS X to MERCHANT has been completed'"""
    merchant = random.choice(MTN_MERCHANTS)
    amt   = rand_amount(5, 500)
    dt    = rand_dt()
    bal   = rand_balance(10, 2000)
    fee   = round(random.choice([0.00, 0.50, 1.00]), 2)
    tid   = mtn_txid()
    bal_s = f"GHS {fmt_amt(bal)}"

    sms = (
        f"Your payment of GHS {amt:.2f} to {merchant} has been completed at "
        f"{fdate(dt)} {ftime(dt)}. Reference: . Your new balance: {bal_s}. "
        f"Fee was GHS {fee:.2f} Tax charged: GHS0. "
        f"Financial Transaction Id: {tid}. External Transaction Id: -."
        "Download the MoMo App for a Faster & Easier Experience "
        "Click here: https://bit.ly/downloadMyMoMo"
    )
    return dict(raw_sms=sms, telco="mtn", tx_type="merchant_payment",
                amount=amt, counterparty_name=merchant, counterparty_phone="",
                balance=bal, fee=fee, tx_id=tid, reference="", dest_network="merchant")


# ─── Weighted distribution ────────────────────────────────────────────────────

TELECEL_DIST = [
    (tcash_transfer_sent_mtn,           0.20),
    (tcash_transfer_sent_telecel,       0.07),
    (tcash_transfer_received_mtn,       0.18),
    (tcash_transfer_received_telecel,   0.06),
    (tcash_merchant_payment,            0.15),
    (tcash_airtime_purchase,            0.08),
    (tcash_airtime_received,            0.04),
    (tcash_cash_withdrawal,             0.06),
    (tcash_bank_transfer,               0.06),
    (tcash_deposit_received,            0.04),
    (tcash_payment_received_expresspay, 0.02),
    (tcash_loan_repayment,              0.02),
    (tcash_interest_received,           0.01),
    (tcash_wallet_balance,              0.01),
]

MTN_DIST = [
    (mtn_payment_made_v1,   0.20),
    (mtn_payment_made_v2,   0.18),
    (mtn_payment_received,  0.28),
    (mtn_cash_out,          0.11),
    (mtn_airtime_purchase,  0.09),
    (mtn_bundle_purchase,   0.05),
    (mtn_merchant_payment,  0.09),
]


def wchoice(dist):
    funcs, weights = zip(*dist)
    return random.choices(funcs, weights=weights, k=1)[0]


# ─── Main ─────────────────────────────────────────────────────────────────────

def generate(n_telecel: int = 155, n_mtn: int = 160) -> list[dict]:
    rows = [wchoice(TELECEL_DIST)() for _ in range(n_telecel)]
    rows += [wchoice(MTN_DIST)() for _ in range(n_mtn)]
    random.shuffle(rows)
    return rows


def main():
    os.makedirs("corpus", exist_ok=True)

    rows = generate()

    fieldnames = [
        "raw_sms", "telco", "tx_type", "amount", "counterparty_name",
        "counterparty_phone", "balance", "fee", "tx_id", "reference", "dest_network",
    ]

    out = "corpus/synthetic_sms_corpus.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Generated {len(rows)} records  ->  {out}\n")

    telco_counts = Counter(r["telco"] for r in rows)
    type_counts  = Counter(f"{r['telco']}/{r['tx_type']}" for r in rows)

    print("Telco breakdown:")
    for k, v in sorted(telco_counts.items()):
        print(f"  {k:10s}  {v}")

    print("\nTransaction type breakdown:")
    for k, v in sorted(type_counts.items()):
        print(f"  {k:45s}  {v}")


if __name__ == "__main__":
    main()
