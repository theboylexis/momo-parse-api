from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParseResult:
    raw_sms: str
    telco: str                        # mtn | telecel | unknown
    tx_type: str                      # transfer_sent | transfer_received | etc.
    template_id: Optional[str]
    confidence: float                 # 1.0 = perfect match, 0.8 = partial, 0.0 = unrecognized

    # Financial fields
    amount: Optional[float]
    currency: str = "GHS"
    balance: Optional[float] = None
    fee: float = 0.0

    # Counterparty
    counterparty_name: Optional[str] = None
    counterparty_phone: Optional[str] = None

    # Transaction metadata
    tx_id: Optional[str] = None
    reference: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "telco": self.telco,
            "tx_type": self.tx_type,
            "template_id": self.template_id,
            "confidence": self.confidence,
            "amount": self.amount,
            "currency": self.currency,
            "balance": self.balance,
            "fee": self.fee,
            "counterparty": {
                "name": self.counterparty_name,
                "phone": self.counterparty_phone,
            },
            "tx_id": self.tx_id,
            "reference": self.reference,
            "date": self.date,
            "time": self.time,
        }
