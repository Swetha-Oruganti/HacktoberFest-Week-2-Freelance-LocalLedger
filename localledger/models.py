from dataclasses import asdict, dataclass, field
from typing import Any

DOCUMENT_TYPES = ("invoice", "receipt", "expense_bill", "other_financial_document", "unknown")
PAYMENT_STATUSES = ("paid", "unpaid", "partially_paid", "overdue", "unknown")

@dataclass
class Extraction:
    document_type: str = "unknown"
    vendor_name: str | None = None
    invoice_number: str | None = None
    issue_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total_amount: float | None = None
    payment_status: str = "unknown"
    expense_category: str | None = None
    confidence: str = "low"
    review_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Extraction":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in value.items() if k in allowed})
