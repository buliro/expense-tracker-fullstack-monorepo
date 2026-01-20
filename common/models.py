"""Data models for the expense tracker domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

__all__ = ["Category", "Expense", "Income", "isoformat_utc", "parse_datetime"]


def isoformat_utc(dt: datetime) -> str:
    """Return an ISO 8601 string with trailing Z for UTC-aware datetimes."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    iso = dt.isoformat(timespec="seconds")
    # datetime.isoformat renders +00:00 for UTC; replace with the shorter Z form.
    return iso.replace("+00:00", "Z")


def parse_datetime(value: str) -> datetime:
    """Parse ISO 8601 datetime strings with optional trailing Z into UTC-aware datetime."""
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC to avoid accidental timezone drift.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class Category:
    id: str
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        return cls(id=data["id"], name=data["name"])


@dataclass(frozen=True)
class Expense:
    id: str
    amount: Decimal
    currency: str
    category: str
    payment_method: str
    incurred_at: datetime
    recorded_at: datetime
    description: Optional[str] = None
    merchant: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    receipt_image_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the expense to JSON-friendly natives."""
        return {
            "id": self.id,
            "amount": f"{self.amount:.2f}",
            "currency": self.currency,
            "category": self.category,
            "payment_method": self.payment_method,
            "incurred_at": isoformat_utc(self.incurred_at),
            "recorded_at": isoformat_utc(self.recorded_at),
            "description": self.description,
            "merchant": self.merchant,
            "tags": list(self.tags),
            "receipt_image_path": self.receipt_image_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Hydrate an Expense from JSON-native data."""
        return cls(
            id=data["id"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            category=data["category"],
            payment_method=data["payment_method"],
            incurred_at=parse_datetime(data["incurred_at"]),
            recorded_at=parse_datetime(data["recorded_at"]),
            description=data.get("description"),
            merchant=data.get("merchant"),
            tags=list(data.get("tags", [])),
            receipt_image_path=data.get("receipt_image_path"),
        )


@dataclass(frozen=True)
class Income:
    id: str
    amount: Decimal
    currency: str
    source: str
    received_method: str
    received_at: datetime
    recorded_at: datetime
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    attachment_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the income to JSON-friendly natives."""
        return {
            "id": self.id,
            "amount": f"{self.amount:.2f}",
            "currency": self.currency,
            "source": self.source,
            "received_method": self.received_method,
            "received_at": isoformat_utc(self.received_at),
            "recorded_at": isoformat_utc(self.recorded_at),
            "description": self.description,
            "tags": list(self.tags),
            "attachment_path": self.attachment_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Income":
        """Hydrate an Income from JSON-native data."""
        return cls(
            id=data["id"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            source=data["source"],
            received_method=data["received_method"],
            received_at=parse_datetime(data["received_at"]),
            recorded_at=parse_datetime(data["recorded_at"]),
            description=data.get("description"),
            tags=list(data.get("tags", [])),
            attachment_path=data.get("attachment_path"),
        )
