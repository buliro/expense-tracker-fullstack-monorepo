"""Console interface for the expense tracker."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common.exceptions import PersistenceError, RecordNotFoundError, ValidationError
from common.services import ExpenseService, IncomeService, LedgerService
from common.storage import JSONStorage

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

def _parse_datetime(value: str) -> str:
    try:
        datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime '{value}'. Expected format YYYY-MM-DDTHH:MM:SS."
        ) from exc
    return value


def _parse_amount(value: str) -> str:
    try:
        amount = Decimal(value)
    except Exception as exc:  # pragma: no cover - delegated to service
        raise argparse.ArgumentTypeError("Amount must be a numeric value") from exc
    if amount <= 0:
        raise argparse.ArgumentTypeError("Amount must be greater than zero")
    return value


def _comma_join(items: Iterable[str]) -> str:
    return ", ".join(items)


def _load_services(data_dir: Path) -> Tuple[LedgerService, ExpenseService, IncomeService]:
    storage = JSONStorage(data_dir)
    expenses = ExpenseService(storage)
    incomes = IncomeService(storage)
    return LedgerService(expenses, incomes), expenses, incomes


def _format_expense(expense: Dict[str, Any]) -> str:
    tags = _comma_join(expense.get("tags", [])) or "-"
    merchant = expense.get("merchant") or "-"
    return (
        f"[{expense['id']}] {expense['incurred_at']} {expense['currency']} {expense['amount']}\n"
        f"  Category: {expense['category']} | Payment: {expense['payment_method']} | Merchant: {merchant}\n"
        f"  Description: {expense.get('description') or '-'}\n"
        f"  Tags: {tags}\n"
    )


def _format_income(income: Dict[str, Any]) -> str:
    tags = _comma_join(income.get("tags", [])) or "-"
    return (
        f"[{income['id']}] {income['received_at']} {income['currency']} {income['amount']}\n"
        f"  Source: {income['source']} | Method: {income['received_method']}\n"
        f"  Description: {income.get('description') or '-'}\n"
        f"  Tags: {tags}\n"
    )


def handle_expense(args: argparse.Namespace, service: ExpenseService) -> None:
    if args.command == "add":
        payload = {
            "amount": args.amount,
            "currency": args.currency,
            "category": args.category,
            "payment_method": args.payment_method,
            "incurred_at": args.incurred_at,
            "recorded_at": args.recorded_at,
            "description": args.description,
            "merchant": args.merchant,
            "tags": args.tags,
            "receipt_image_path": args.receipt,
        }
        expense = service.add(payload)
        print("Expense added:\n" + _format_expense(expense.to_dict()))
    elif args.command == "list":
        filters = {
            "category": args.category,
            "payment_method": args.payment_method,
            "tag": args.tag,
            "start": args.start,
            "end": args.end,
            "merchant": args.merchant,
        }
        expenses = service.list(**{k: v for k, v in filters.items() if v is not None})
        if not expenses:
            print("No expenses found.")
            return
        total = service.total(**{k: v for k, v in filters.items() if v is not None})
        print(f"Found {len(expenses)} expenses (total {total:.2f}):")
        for expense in expenses:
            print(_format_expense(expense.to_dict()))
    elif args.command == "edit":
        changes = {
            "amount": args.amount,
            "currency": args.currency,
            "category": args.category,
            "payment_method": args.payment_method,
            "incurred_at": args.incurred_at,
            "recorded_at": args.recorded_at,
            "description": args.description,
            "merchant": args.merchant,
            "tags": args.tags,
            "receipt_image_path": args.receipt,
        }
        cleaned = {k: v for k, v in changes.items() if v is not None}
        expense = service.update(args.id, cleaned)
        print("Expense updated:\n" + _format_expense(expense.to_dict()))
    elif args.command == "delete":
        service.delete(args.id)
        print(f"Expense {args.id} deleted.")


def handle_income(args: argparse.Namespace, service: IncomeService) -> None:
    if args.command == "add":
        payload = {
            "amount": args.amount,
            "currency": args.currency,
            "source": args.source,
            "received_method": args.received_method,
            "received_at": args.received_at,
            "recorded_at": args.recorded_at,
            "description": args.description,
            "tags": args.tags,
            "attachment_path": args.attachment,
        }
        income = service.add(payload)
        print("Income added:\n" + _format_income(income.to_dict()))
    elif args.command == "list":
        filters = {
            "source": args.source,
            "received_method": args.received_method,
            "tag": args.tag,
            "start": args.start,
            "end": args.end,
        }
        incomes = service.list(**{k: v for k, v in filters.items() if v is not None})
        if not incomes:
            print("No incomes found.")
            return
        total = service.total(**{k: v for k, v in filters.items() if v is not None})
        print(f"Found {len(incomes)} incomes (total {total:.2f}):")
        for income in incomes:
            print(_format_income(income.to_dict()))
    elif args.command == "edit":
        changes = {
            "amount": args.amount,
            "currency": args.currency,
            "source": args.source,
            "received_method": args.received_method,
            "received_at": args.received_at,
            "recorded_at": args.recorded_at,
            "description": args.description,
            "tags": args.tags,
            "attachment_path": args.attachment,
        }
        cleaned = {k: v for k, v in changes.items() if v is not None}
        income = service.update(args.id, cleaned)
        print("Income updated:\n" + _format_income(income.to_dict()))
    elif args.command == "delete":
        service.delete(args.id)
        print(f"Income {args.id} deleted.")


def handle_balance(args: argparse.Namespace, ledger: LedgerService) -> None:
    filters = {k: v for k, v in {
        "start": args.start,
        "end": args.end,
        "category": args.category,
        "source": args.source,
        "tag": args.tag,
    }.items() if v is not None}
    balance = ledger.balance(**filters)
    print(f"Net balance: {balance:.2f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Expense Tracker CLI")
    parser.add_argument(
        "--data-dir",
        default="data",
        type=Path,
        help="Directory to store JSON data (default: ./data)",
    )

    subparsers = parser.add_subparsers(dest="entity", required=True)

    expense_parser = subparsers.add_parser("expense", help="Manage expenses")
    expense_sub = expense_parser.add_subparsers(dest="command", required=True)

    expense_add = expense_sub.add_parser("add", help="Add a new expense")
    expense_add.add_argument("amount", type=_parse_amount)
    expense_add.add_argument("currency")
    expense_add.add_argument("category")
    expense_add.add_argument("payment_method")
    expense_add.add_argument("incurred_at", type=_parse_datetime)
    expense_add.add_argument("--recorded-at", dest="recorded_at", type=_parse_datetime)
    expense_add.add_argument("--description")
    expense_add.add_argument("--merchant")
    expense_add.add_argument("--tags", nargs="*", default=[])
    expense_add.add_argument("--receipt")

    expense_list = expense_sub.add_parser("list", help="List expenses")
    expense_list.add_argument("--category")
    expense_list.add_argument("--payment-method")
    expense_list.add_argument("--tag")
    expense_list.add_argument("--start", type=_parse_datetime)
    expense_list.add_argument("--end", type=_parse_datetime)
    expense_list.add_argument("--merchant")

    expense_edit = expense_sub.add_parser("edit", help="Edit an existing expense")
    expense_edit.add_argument("id")
    expense_edit.add_argument("--amount", type=_parse_amount)
    expense_edit.add_argument("--currency")
    expense_edit.add_argument("--category")
    expense_edit.add_argument("--payment-method")
    expense_edit.add_argument("--incurred-at", type=_parse_datetime)
    expense_edit.add_argument("--recorded-at", type=_parse_datetime)
    expense_edit.add_argument("--description")
    expense_edit.add_argument("--merchant")
    expense_edit.add_argument("--tags", nargs="*")
    expense_edit.add_argument("--receipt")

    expense_delete = expense_sub.add_parser("delete", help="Delete an expense")
    expense_delete.add_argument("id")

    income_parser = subparsers.add_parser("income", help="Manage incomes")
    income_sub = income_parser.add_subparsers(dest="command", required=True)

    income_add = income_sub.add_parser("add", help="Add a new income")
    income_add.add_argument("amount", type=_parse_amount)
    income_add.add_argument("currency")
    income_add.add_argument("source")
    income_add.add_argument("received_method")
    income_add.add_argument("received_at", type=_parse_datetime)
    income_add.add_argument("--recorded-at", dest="recorded_at", type=_parse_datetime)
    income_add.add_argument("--description")
    income_add.add_argument("--tags", nargs="*", default=[])
    income_add.add_argument("--attachment")

    income_list = income_sub.add_parser("list", help="List incomes")
    income_list.add_argument("--source")
    income_list.add_argument("--received-method")
    income_list.add_argument("--tag")
    income_list.add_argument("--start", type=_parse_datetime)
    income_list.add_argument("--end", type=_parse_datetime)

    income_edit = income_sub.add_parser("edit", help="Edit an existing income")
    income_edit.add_argument("id")
    income_edit.add_argument("--amount", type=_parse_amount)
    income_edit.add_argument("--currency")
    income_edit.add_argument("--source")
    income_edit.add_argument("--received-method")
    income_edit.add_argument("--received-at", type=_parse_datetime)
    income_edit.add_argument("--recorded-at", type=_parse_datetime)
    income_edit.add_argument("--description")
    income_edit.add_argument("--tags", nargs="*")
    income_edit.add_argument("--attachment")

    income_delete = income_sub.add_parser("delete", help="Delete an income")
    income_delete.add_argument("id")

    balance_parser = subparsers.add_parser("balance", help="Compute net balance")
    balance_parser.add_argument("--start", type=_parse_datetime)
    balance_parser.add_argument("--end", type=_parse_datetime)
    balance_parser.add_argument("--category")
    balance_parser.add_argument("--source")
    balance_parser.add_argument("--tag")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ledger, expense_service, income_service = _load_services(args.data_dir)

    try:
        if args.entity == "expense":
            handle_expense(args, expense_service)
        elif args.entity == "income":
            handle_income(args, income_service)
        elif args.entity == "balance":
            handle_balance(args, ledger)
        else:  # pragma: no cover - argparse should prevent this
            parser.error(f"Unknown entity: {args.entity}")
            return 2
    except ValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except RecordNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except PersistenceError as exc:
        print(f"Storage error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
