"""Validation helpers shared across expense tracker services."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, List, Optional

from .exceptions import ValidationError
from .models import parse_datetime

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
TAG_PATTERN = re.compile(r"^[a-z0-9_-]{1,30}$")

PAYMENT_METHODS = {
    "cash",
    "debit_card",
    "credit_card",
    "bank_transfer",
    "mobile_payment",
    "other",
}

INCOME_METHODS = {
    "salary",
    "bonus",
    "interest",
    "gift",
    "other",
}


def _quantize_two_decimals(amount: Decimal) -> Decimal:
    """Round the amount to two decimal places using bankers-safe HALF_UP rounding."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_amount(raw: object, field: str) -> Decimal:
    """Convert raw input to a positive Decimal with exactly two fraction digits."""
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:  # type: ignore[arg-type]
        raise ValidationError(f"{field} must be a numeric value") from exc

    if amount <= 0:
        raise ValidationError(f"{field} must be greater than zero")

    return _quantize_two_decimals(amount)


def validate_currency(code: str) -> str:
    if not isinstance(code, str) or not CURRENCY_PATTERN.fullmatch(code):
        raise ValidationError("currency must be a 3-letter ISO 4217 code (uppercase)")
    return code


def validate_required_str(value: object, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValidationError(f"{field} cannot be empty")
    if len(trimmed) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters")
    return trimmed


def validate_optional_str(value: object, field: str, max_length: int) -> Optional[str]:
    if value is None:
        return None
    return validate_required_str(value, field, max_length)


def normalize_tags(raw_tags: Optional[Iterable[object]]) -> List[str]:
    if raw_tags is None:
        return []
    normalized: List[str] = []
    seen = set()
    for raw in raw_tags:
        if not isinstance(raw, str):
            raise ValidationError("tags must be strings")
        tag = raw.strip().lower()
        if not tag:
            raise ValidationError("tags cannot be empty strings")
        if len(tag) > 30:
            raise ValidationError("tags must be at most 30 characters")
        if not TAG_PATTERN.fullmatch(tag):
            raise ValidationError("tags may only contain lowercase letters, digits, underscores, or hyphens")
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


def validate_datetime(value: object, field: str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = parse_datetime(value)
    else:
        raise ValidationError(f"{field} must be a datetime or ISO 8601 string")
    return dt.astimezone(timezone.utc)


def validate_enum(value: object, field: str, allowed: Iterable[str]) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    canonical = value.strip().lower()
    if canonical not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return canonical


def validate_relative_path(
    raw: object,
    root: Path,
    field: str,
    *,
    required_prefix: Optional[str] = None,
) -> Optional[str]:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValidationError(f"{field} must be a string path")
    candidate = Path(raw.strip())
    if not candidate.parts:
        raise ValidationError(f"{field} cannot be empty")
    if candidate.is_absolute():
        raise ValidationError(f"{field} must be a relative path")
    if required_prefix:
        prefix_path = Path(required_prefix)
        prefix_parts = prefix_path.parts
        if candidate.parts[: len(prefix_parts)] != prefix_parts:
            raise ValidationError(
                f"{field} must start with '{required_prefix}' to stay within the attachments area"
            )
    try:
        resolved = (root / candidate).resolve()
    except OSError as exc:
        raise ValidationError(f"{field} points to an invalid path") from exc
    # Ensure the final path stays under the configured storage root to avoid traversal.
    base_root = root.resolve()
    if resolved == base_root:
        return str(candidate.as_posix())
    if base_root not in resolved.parents:
        raise ValidationError(f"{field} must be located within {root}")
    # Store the path relative to root for portability.
    return str(candidate.as_posix())


def ensure_recorded_after(event_dt: datetime, recorded_dt: datetime, event_field: str, recorded_field: str) -> None:
    if recorded_dt < event_dt:
        raise ValidationError(f"{recorded_field} must not be earlier than {event_field}")
