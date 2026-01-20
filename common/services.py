"""Framework-agnostic business services for the expense tracker."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

from .exceptions import PersistenceError, RecordNotFoundError, ValidationError
from .models import Category, Expense, Income
from .storage import JSONStorage
from .validators import (
    INCOME_METHODS,
    PAYMENT_METHODS,
    ensure_recorded_after,
    normalize_tags,
    parse_amount,
    validate_currency,
    validate_datetime,
    validate_enum,
    validate_optional_str,
    validate_relative_path,
    validate_required_str,
)


class CategoryService:
    """Manages expense categories and persistence."""

    def __init__(self, storage: JSONStorage, resource: str = "categories.json") -> None:
        self._storage = storage
        self._resource = resource
        self._categories: Dict[str, Category] = {}
        self.load()

    def add(self, payload: Dict[str, object]) -> Category:
        data = self._validate_payload(payload)
        category = Category(**data)
        self._categories[category.id] = category
        self._persist()
        return category

    def update(self, category_id: str, changes: Dict[str, object]) -> Category:
        existing = self._get_or_raise(category_id)
        merged_payload = {**existing.to_dict(), **changes}
        data = self._validate_payload(merged_payload, current=existing)
        updated = Category(**data)
        self._categories[category_id] = updated
        self._persist()
        return updated

    def delete(self, category_id: str) -> None:
        self._get_or_raise(category_id)
        del self._categories[category_id]
        self._persist()

    def get(self, category_id: str) -> Category:
        return self._get_or_raise(category_id)

    def list(self) -> List[Category]:
        return sorted(self._categories.values(), key=lambda cat: cat.name.lower())

    def load(self) -> None:
        raw_records = self._storage.load(self._resource)
        self._categories = {
            payload["id"]: Category.from_dict(payload) for payload in raw_records
        }

    def _persist(self) -> None:
        try:
            self._storage.save(
                self._resource, [category.to_dict() for category in self._categories.values()]
            )
        except PersistenceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise PersistenceError("Unexpected error while saving categories") from exc

    def _get_or_raise(self, category_id: str) -> Category:
        try:
            return self._categories[category_id]
        except KeyError as exc:
            raise RecordNotFoundError(f"Category {category_id} not found") from exc

    def _validate_payload(
        self, payload: Dict[str, object], *, current: Optional[Category] = None
    ) -> Dict[str, object]:
        name = validate_required_str(payload.get("name"), "name", 50)
        canonical = name.lower()

        for category in self._categories.values():
            if current and category.id == current.id:
                continue
            if category.name.lower() == canonical:
                raise ValidationError("Category name must be unique")

        return {
            "id": current.id if current else str(uuid4()),
            "name": name,
        }


class ExpenseService:
    """Manages expense records and mediates persistence."""

    def __init__(self, storage: JSONStorage, resource: str = "expenses.json") -> None:
        self._storage = storage
        self._resource = resource
        self._expenses: Dict[str, Expense] = {}
        self.load()  # Hydrate in-memory cache from persistence on construction.

    # Public API -----------------------------------------------------------
    def add(self, payload: Dict[str, object]) -> Expense:
        data = self._validate_payload(payload)
        expense = Expense(**data)
        self._expenses[expense.id] = expense
        self._persist()
        return expense

    def update(self, expense_id: str, changes: Dict[str, object]) -> Expense:
        existing = self._get_or_raise(expense_id)
        # Merge existing serialised data with incoming changes to support partial updates.
        merged_payload = {**existing.to_dict(), **changes}
        data = self._validate_payload(merged_payload, current=existing)
        updated = Expense(**data)
        self._expenses[expense_id] = updated
        self._persist()
        return updated

    def delete(self, expense_id: str) -> None:
        self._get_or_raise(expense_id)
        del self._expenses[expense_id]
        self._persist()

    def get(self, expense_id: str) -> Expense:
        """Return an expense or raise if it does not exist."""
        return self._get_or_raise(expense_id)

    def list(self, **filters: object) -> List[Expense]:
        records: Iterable[Expense] = self._expenses.values()
        records = list(self._apply_filters(records, filters))
        return sorted(records, key=lambda exp: exp.incurred_at)

    def total(self, **filters: object) -> Decimal:
        expenses = self.list(**filters)
        return sum((expense.amount for expense in expenses), start=Decimal("0.00"))

    def load(self) -> None:
        """Load existing expenses from persistence."""
        raw_records = self._storage.load(self._resource)
        self._expenses = {
            payload["id"]: Expense.from_dict(payload) for payload in raw_records
        }

    # Internal helpers -----------------------------------------------------
    def _persist(self) -> None:
        try:
            # Persist current snapshot; storage layer handles atomic writes.
            self._storage.save(
                self._resource, [expense.to_dict() for expense in self._expenses.values()]
            )
        except PersistenceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise PersistenceError("Unexpected error while saving expenses") from exc

    def _get_or_raise(self, expense_id: str) -> Expense:
        try:
            return self._expenses[expense_id]
        except KeyError as exc:
            raise RecordNotFoundError(f"Expense {expense_id} not found") from exc

    def _validate_payload(
        self, payload: Dict[str, object], *, current: Optional[Expense] = None
    ) -> Dict[str, object]:
        root = self._storage.base_path
        # Compose normalised fields ensuring validation across all entry points.
        base = {
            "id": current.id if current else str(uuid4()),
            "amount": parse_amount(payload.get("amount"), "amount"),
            "currency": validate_currency(str(payload.get("currency", "")).upper()),
            "category": validate_required_str(payload.get("category"), "category", 50),
            "payment_method": validate_enum(
                payload.get("payment_method"), "payment_method", PAYMENT_METHODS
            ),
            "incurred_at": validate_datetime(payload.get("incurred_at"), "incurred_at"),
            "recorded_at": _recorded_datetime(payload.get("recorded_at")),
            "description": validate_optional_str(payload.get("description"), "description", 200),
            "merchant": validate_optional_str(payload.get("merchant"), "merchant", 100),
            "tags": normalize_tags(payload.get("tags")),
            "receipt_image_path": validate_relative_path(
                payload.get("receipt_image_path"),
                Path(root / "attachments"),
                "receipt_image_path",
                required_prefix="attachments/receipts",
            ),
        }
        ensure_recorded_after(
            base["incurred_at"], base["recorded_at"], "incurred_at", "recorded_at"
        )
        return base

    def _apply_filters(self, records: Iterable[Expense], filters: Dict[str, object]) -> Iterable[Expense]:
        # Pre-compute normalised filter values once to avoid repeated parsing per record.
        category = (
            str(filters["category"]).strip().lower()
            if filters.get("category") is not None
            else None
        )
        payment_method = (
            str(filters["payment_method"]).strip().lower()
            if filters.get("payment_method") is not None
            else None
        )
        tag = (
            str(filters["tag"]).strip().lower()
            if filters.get("tag") is not None
            else None
        )
        start = (
            validate_datetime(filters["start"], "start")
            if filters.get("start") is not None
            else None
        )
        end = (
            validate_datetime(filters["end"], "end")
            if filters.get("end") is not None
            else None
        )
        merchant = (
            str(filters["merchant"]).strip().lower()
            if filters.get("merchant") is not None
            else None
        )

        def matches(expense: Expense) -> bool:
            if category and expense.category.lower() != category:
                return False
            if payment_method and expense.payment_method != payment_method:
                return False
            if tag and tag not in expense.tags:
                return False
            if start and expense.incurred_at < start:
                return False
            if end and expense.incurred_at > end:
                return False
            if merchant and (expense.merchant or "").lower() != merchant:
                return False
            return True

        return filter(matches, records)

    def rename_category(self, old_name: str, new_name: str) -> None:
        canonical_old = old_name.strip().lower()
        canonical_new = new_name.strip()
        if not canonical_new:
            return

        changed = False
        for expense_id, expense in list(self._expenses.items()):
            if expense.category.lower() == canonical_old:
                payload = expense.to_dict()
                payload["category"] = canonical_new
                data = self._validate_payload(payload, current=expense)
                self._expenses[expense_id] = Expense(**data)
                changed = True

        if changed:
            self._persist()

    def is_category_in_use(self, category_name: str) -> bool:
        canonical = category_name.strip().lower()
        return any(expense.category.lower() == canonical for expense in self._expenses.values())


class IncomeService:
    """Manages income records and mediates persistence."""

    def __init__(self, storage: JSONStorage, resource: str = "incomes.json") -> None:
        self._storage = storage
        self._resource = resource
        self._incomes: Dict[str, Income] = {}
        self.load()  # Hydrate in-memory cache from persistence on construction.

    def add(self, payload: Dict[str, object]) -> Income:
        data = self._validate_payload(payload)
        income = Income(**data)
        self._incomes[income.id] = income
        self._persist()
        return income

    def update(self, income_id: str, changes: Dict[str, object]) -> Income:
        existing = self._get_or_raise(income_id)
        # Merge existing serialised data with incoming changes to support partial updates.
        merged_payload = {**existing.to_dict(), **changes}
        data = self._validate_payload(merged_payload, current=existing)
        updated = Income(**data)
        self._incomes[income_id] = updated
        self._persist()
        return updated

    def delete(self, income_id: str) -> None:
        self._get_or_raise(income_id)
        del self._incomes[income_id]
        self._persist()

    def get(self, income_id: str) -> Income:
        """Return an income or raise if it does not exist."""
        return self._get_or_raise(income_id)

    def list(self, **filters: object) -> List[Income]:
        records: Iterable[Income] = self._incomes.values()
        records = list(self._apply_filters(records, filters))
        return sorted(records, key=lambda inc: inc.received_at)

    def total(self, **filters: object) -> Decimal:
        incomes = self.list(**filters)
        return sum((income.amount for income in incomes), start=Decimal("0.00"))

    def load(self) -> None:
        raw_records = self._storage.load(self._resource)
        self._incomes = {
            payload["id"]: Income.from_dict(payload) for payload in raw_records
        }

    def _persist(self) -> None:
        try:
            # Persist current snapshot; storage layer handles atomic writes.
            self._storage.save(
                self._resource, [income.to_dict() for income in self._incomes.values()]
            )
        except PersistenceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise PersistenceError("Unexpected error while saving incomes") from exc

    def _get_or_raise(self, income_id: str) -> Income:
        try:
            return self._incomes[income_id]
        except KeyError as exc:
            raise RecordNotFoundError(f"Income {income_id} not found") from exc

    def _validate_payload(
        self, payload: Dict[str, object], *, current: Optional[Income] = None
    ) -> Dict[str, object]:
        root = self._storage.base_path
        # Compose normalised fields ensuring validation across all entry points.
        base = {
            "id": current.id if current else str(uuid4()),
            "amount": parse_amount(payload.get("amount"), "amount"),
            "currency": validate_currency(str(payload.get("currency", "")).upper()),
            "source": validate_required_str(payload.get("source"), "source", 50),
            "received_method": validate_enum(
                payload.get("received_method"), "received_method", INCOME_METHODS
            ),
            "received_at": validate_datetime(payload.get("received_at"), "received_at"),
            "recorded_at": _recorded_datetime(payload.get("recorded_at")),
            "description": validate_optional_str(payload.get("description"), "description", 200),
            "tags": normalize_tags(payload.get("tags")),
            "attachment_path": validate_relative_path(
                payload.get("attachment_path"),
                Path(root / "attachments"),
                "attachment_path",
                required_prefix="attachments/income_docs",
            ),
        }
        ensure_recorded_after(
            base["received_at"], base["recorded_at"], "received_at", "recorded_at"
        )
        return base

    def _apply_filters(self, records: Iterable[Income], filters: Dict[str, object]) -> Iterable[Income]:
        # Pre-compute normalised filter values once to avoid repeated parsing per record.
        source = (
            str(filters["source"]).strip().lower()
            if filters.get("source") is not None
            else None
        )
        received_method = (
            str(filters["received_method"]).strip().lower()
            if filters.get("received_method") is not None
            else None
        )
        tag = (
            str(filters["tag"]).strip().lower()
            if filters.get("tag") is not None
            else None
        )
        start = (
            validate_datetime(filters["start"], "start")
            if filters.get("start") is not None
            else None
        )
        end = (
            validate_datetime(filters["end"], "end")
            if filters.get("end") is not None
            else None
        )

        def matches(income: Income) -> bool:
            if source and income.source.lower() != source:
                return False
            if received_method and income.received_method != received_method:
                return False
            if tag and tag not in income.tags:
                return False
            if start and income.received_at < start:
                return False
            if end and income.received_at > end:
                return False
            return True

        return filter(matches, records)


class LedgerService:
    """Aggregates expenses and incomes to provide balances."""

    def __init__(self, expense_service: ExpenseService, income_service: IncomeService) -> None:
        self._expenses = expense_service
        self._incomes = income_service

    def balance(self, **filters: object) -> Decimal:
        """Compute income minus expense with shared filters."""
        income_total = self._incomes.total(**filters)
        expense_total = self._expenses.total(**filters)
        return income_total - expense_total

    def refresh(self) -> None:
        """Reload data from persistence for both services."""
        self._expenses.load()
        self._incomes.load()

    def snapshot(self) -> Dict[str, List[Dict[str, object]]]:
        """Return serialisable snapshot useful for testing or exports."""
        return {
            "incomes": [income.to_dict() for income in self._incomes.list()],
            "expenses": [expense.to_dict() for expense in self._expenses.list()],
        }


def _recorded_datetime(candidate: Optional[object]) -> datetime:
    if candidate is None:
        # Default to an accurate timestamp at validation time; ensures predictable ordering.
        return datetime.now(timezone.utc)
    if isinstance(candidate, datetime):
        return candidate.astimezone(timezone.utc)
    return validate_datetime(candidate, "recorded_at")
