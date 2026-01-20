"""Tkinter desktop application for the expense tracker."""

from __future__ import annotations

import argparse
import tkinter as tk
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Iterable, List, Optional, Tuple

from common.exceptions import PersistenceError, RecordNotFoundError, ValidationError
from common.models import Category, parse_datetime
from common.services import CategoryService, ExpenseService, IncomeService, LedgerService
from common.storage import JSONStorage
from common.validators import INCOME_METHODS, PAYMENT_METHODS


PRIMARY_BG = "#0f172a"
SECONDARY_BG = "#1e293b"
ACCENT_BG = "#1d4ed8"
ACCENT_ACTIVE_BG = "#2563eb"
TEXT_PRIMARY = "#e2e8f0"
TEXT_MUTED = "#94a3b8"


def _iso_now() -> str:
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="seconds").replace("+00:00", "Z")


def _current_date_time() -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")


def split_iso_datetime(value: str) -> Tuple[str, str]:
    dt = parse_user_datetime(value)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def combine_date_time(date_str: str, time_str: Optional[str]) -> str:
    date_text = (date_str or "").strip()
    if not date_text:
        raise ValueError("Date is required")
    time_text = (time_str or "00:00").strip() or "00:00"
    candidate = f"{date_text}T{time_text}"
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError("Invalid date or time") from exc
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sanitize_amount_input(raw: str) -> str:
    if raw is None:
        return ""
    cleaned = raw.replace(",", "").strip()
    return cleaned


def format_amount_display(value: Decimal | str) -> str:
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    sanitized = sanitize_amount_input(value)
    if not sanitized:
        return ""
    try:
        amount = Decimal(sanitized)
    except InvalidOperation:
        return value.strip()
    return f"{amount:,.2f}"


def parse_user_datetime(value: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Datetime string cannot be empty")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return parse_datetime(normalized)


class ExpenseTab(ttk.Frame):
    """UI for managing expenses."""

    def __init__(
        self,
        master: tk.Misc,
        service: ExpenseService,
        category_service: CategoryService,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=16, style="Panel.TFrame")
        self.service = service
        self.category_service = category_service
        self.on_change = on_change

        self.amount_var = tk.StringVar()
        self.currency_var = tk.StringVar(value="USD")
        self.category_var = tk.StringVar()
        self.payment_var = tk.StringVar(value=sorted(PAYMENT_METHODS)[0])
        current_date, current_time = _current_date_time()
        self.incurred_date_var = tk.StringVar(value=current_date)
        self.incurred_time_var = tk.StringVar(value=current_time)
        self.description_var = tk.StringVar()
        self.merchant_var = tk.StringVar()
        self.tags_var = tk.StringVar()

        self.categories: List[Category] = []
        self.category_combo: Optional[ttk.Combobox] = None
        self.add_category_button: Optional[ttk.Button] = None
        self.delete_category_button: Optional[ttk.Button] = None
        self.refresh_category_button: Optional[ttk.Button] = None

        self._build_form()
        self._build_table()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._reload_categories(preserve_selection=False)

    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text="Add Expense", style="Card.TLabelframe")
        form.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 12))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        def add_field(
            label: str,
            var: tk.StringVar,
            column: int,
            row: int,
            *,
            state: Optional[str] = None,
        ) -> ttk.Entry:
            ttk.Label(form, text=label, style="FormLabel.TLabel").grid(
                column=column, row=row, sticky="w", padx=4, pady=4
            )
            entry = ttk.Entry(form, textvariable=var, style="App.TEntry")
            if state:
                entry.configure(state=state)
            entry.grid(column=column, row=row + 1, sticky="ew", padx=4, pady=(0, 8))
            return entry

        amount_entry = add_field("Amount", self.amount_var, 0, 0)
        amount_entry.bind("<FocusOut>", self._handle_amount_focus_out)

        add_field("Currency", self.currency_var, 1, 0, state="readonly")

        ttk.Label(form, text="Category", style="FormLabel.TLabel").grid(
            column=0, row=2, sticky="w", padx=4, pady=4
        )
        category_frame = ttk.Frame(form, style="Panel.TFrame")
        category_frame.grid(column=0, row=3, sticky="ew", padx=4, pady=(0, 8))
        category_frame.columnconfigure(0, weight=1)

        self.category_combo = ttk.Combobox(
            category_frame,
            textvariable=self.category_var,
            values=[],
            state="readonly",
            style="App.TCombobox",
        )
        self.category_combo.grid(column=0, row=0, sticky="ew")

        self.add_category_button = ttk.Button(
            category_frame,
            text="Add",
            command=self._prompt_add_category,
            style="Secondary.TButton",
        )
        self.add_category_button.grid(column=1, row=0, padx=4)

        self.delete_category_button = ttk.Button(
            category_frame,
            text="Delete",
            command=self._delete_selected_category,
            style="Secondary.TButton",
        )
        self.delete_category_button.grid(column=2, row=0, padx=4)

        self.refresh_category_button = ttk.Button(
            category_frame,
            text="Refresh",
            command=lambda: self._reload_categories(preserve_selection=True),
            style="Secondary.TButton",
        )
        self.refresh_category_button.grid(column=3, row=0, padx=4)

        ttk.Label(form, text="Payment Method", style="FormLabel.TLabel").grid(
            column=1, row=2, sticky="w", padx=4, pady=4
        )
        payment_combo = ttk.Combobox(
            form,
            textvariable=self.payment_var,
            values=sorted(PAYMENT_METHODS),
            state="readonly",
            style="App.TCombobox",
        )
        payment_combo.grid(column=1, row=3, sticky="ew", padx=4, pady=(0, 8))

        add_field("Incurred Date (YYYY-MM-DD)", self.incurred_date_var, 0, 4)
        add_field("Incurred Time (HH:MM)", self.incurred_time_var, 1, 4)
        add_field("Merchant", self.merchant_var, 0, 6)
        add_field("Tags (comma separated)", self.tags_var, 1, 6)

        ttk.Label(form, text="Description", style="FormLabel.TLabel").grid(
            column=0, row=8, columnspan=2, sticky="w", padx=4, pady=4
        )
        desc_entry = ttk.Entry(form, textvariable=self.description_var, style="App.TEntry")
        desc_entry.grid(column=0, row=9, columnspan=2, sticky="ew", padx=4, pady=(0, 8))

        button_row = ttk.Frame(form, style="Panel.TFrame")
        button_row.grid(column=0, row=10, columnspan=2, sticky="e", padx=4, pady=4)
        ttk.Button(
            button_row,
            text="Reset",
            command=self.reset_form,
            style="Secondary.TButton",
        ).grid(column=0, row=0, padx=4)
        ttk.Button(
            button_row,
            text="Add Expense",
            command=self.submit,
            style="Primary.TButton",
        ).grid(column=1, row=0, padx=4)

    def _build_table(self) -> None:
        table_frame = ttk.Frame(self, style="Panel.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("date", "category", "amount", "payment", "merchant")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
            style="App.Treeview",
        )
        headings = {
            "date": "Date",
            "category": "Category",
            "amount": "Amount",
            "payment": "Payment",
            "merchant": "Merchant",
        }
        for key, label in headings.items():
            width = 140 if key != "amount" else 120
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=width, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        button_bar = ttk.Frame(table_frame, style="Panel.TFrame")
        button_bar.grid(row=1, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(
            button_bar,
            text="Delete Selected",
            command=self.delete_selected,
            style="Secondary.TButton",
        ).grid(row=0, column=0, padx=4)

    def submit(self) -> None:
        sanitized_amount = sanitize_amount_input(self.amount_var.get())
        try:
            incurred_at = combine_date_time(self.incurred_date_var.get(), self.incurred_time_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Expense", "Provide a valid incurred date and time.", parent=self
            )
            return
        payload = {
            "amount": sanitized_amount,
            "currency": (self.currency_var.get() or "USD").strip().upper(),
            "category": self.category_var.get(),
            "payment_method": self.payment_var.get(),
            "incurred_at": incurred_at,
            "description": self.description_var.get() or None,
            "merchant": self.merchant_var.get() or None,
            "tags": self._split_tags(self.tags_var.get()),
            "receipt_image_path": None,
        }

        errors = self._validate(payload)
        if errors:
            messagebox.showerror("Invalid Expense", "\n".join(errors), parent=self)
            return

        try:
            self.service.add(payload)
        except ValidationError as exc:
            messagebox.showerror("Invalid Expense", str(exc), parent=self)
            return

        self.reset_form()
        self.populate()
        self.on_change()

    def delete_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please select an expense to delete.", parent=self)
            return
        for item_id in selection:
            try:
                self.service.delete(item_id)
            except RecordNotFoundError as exc:
                messagebox.showwarning("Not Found", str(exc), parent=self)
            except PersistenceError as exc:
                messagebox.showerror("Storage Error", str(exc), parent=self)
                break
        self.populate()
        self.on_change()

    def populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for expense in self.service.list():
            data = expense.to_dict()
            amount_display = f"{data['currency']} {format_amount_display(data['amount'])}"
            try:
                date_part, time_part = split_iso_datetime(data["incurred_at"])
                incurred_display = f"{date_part} {time_part}"
            except Exception:
                incurred_display = data["incurred_at"]
            merchant = data.get("merchant") or "-"
            values = (
                incurred_display,
                data["category"],
                amount_display,
                data["payment_method"],
                merchant if merchant else "-",
            )
            self.tree.insert("", "end", iid=data["id"], values=values)

    def reset_form(self) -> None:
        self.amount_var.set("")
        self.description_var.set("")
        self.merchant_var.set("")
        self.tags_var.set("")
        current_date, current_time = _current_date_time()
        self.incurred_date_var.set(current_date)
        self.incurred_time_var.set(current_time)
        self._reload_categories(preserve_selection=False)

    def _handle_amount_focus_out(self, _event: object) -> None:
        self.amount_var.set(format_amount_display(self.amount_var.get()))

    def _validate(self, payload: dict) -> List[str]:
        errors: List[str] = []

        amount_text = payload["amount"].strip()
        if not amount_text:
            errors.append("Amount is required.")
        else:
            try:
                amount_value = Decimal(amount_text)
            except InvalidOperation:
                errors.append("Amount must be a number.")
            else:
                if amount_value <= 0:
                    errors.append("Amount must be greater than zero.")

        if not payload["category"].strip():
            errors.append("Category is required.")

        if not payload["payment_method"].strip():
            errors.append("Payment method is required.")

        incurred_text = (payload["incurred_at"] or "").strip()
        if not incurred_text:
            errors.append("Incurred date/time is required.")
        else:
            try:
                incurred_dt = parse_user_datetime(incurred_text)
            except Exception:
                errors.append("Provide a valid incurred date and time.")
            else:
                if incurred_dt > datetime.now(timezone.utc):
                    errors.append("Incurred date cannot be in the future.")

        return errors

    @staticmethod
    def _split_tags(raw: str) -> Optional[Iterable[str]]:
        cleaned = [tag.strip() for tag in raw.split(",") if tag.strip()]
        return cleaned if cleaned else None

    def _reload_categories(self, preserve_selection: bool = True) -> None:
        previous = self.category_var.get().strip()
        try:
            categories = self.category_service.list()
        except PersistenceError as exc:
            messagebox.showerror("Storage Error", str(exc), parent=self)
            categories = []
        except ValidationError as exc:
            messagebox.showerror("Invalid Category", str(exc), parent=self)
            categories = []
        except Exception as exc:  # pragma: no cover - defensive guard
            messagebox.showerror("Error", f"Unexpected error loading categories: {exc}", parent=self)
            categories = []

        self.categories = categories
        names = [category.name for category in categories]
        if preserve_selection and previous and previous not in names:
            names.insert(0, previous)

        if self.category_combo is not None:
            self.category_combo["values"] = names
            if names:
                self.category_combo.configure(state="readonly")
            else:
                self.category_combo.configure(state="disabled")

        if self.delete_category_button is not None:
            self.delete_category_button.configure(state="normal" if categories else "disabled")

        if names:
            if preserve_selection and previous in names:
                self.category_var.set(previous)
            else:
                self.category_var.set(names[0])
        else:
            self.category_var.set("")

    def _prompt_add_category(self) -> None:
        name = simpledialog.askstring("Add Category", "Category name:", parent=self)
        if name is None:
            return
        trimmed = name.strip()
        if not trimmed:
            messagebox.showerror("Invalid Category", "Category name cannot be empty.", parent=self)
            return
        try:
            created = self.category_service.add({"name": trimmed})
        except ValidationError as exc:
            messagebox.showerror("Invalid Category", str(exc), parent=self)
            return
        except PersistenceError as exc:
            messagebox.showerror("Storage Error", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            messagebox.showerror("Error", f"Unexpected error adding category: {exc}", parent=self)
            return

        self.category_var.set(created.name)
        self._reload_categories(preserve_selection=True)

    def _delete_selected_category(self) -> None:
        name = self.category_var.get().strip()
        if not name:
            messagebox.showinfo("No Category", "Select a category to delete.", parent=self)
            return

        category = next((item for item in self.categories if item.name == name), None)
        if category is None:
            messagebox.showwarning(
                "Category Missing",
                "The selected category could not be found. Please refresh and try again.",
                parent=self,
            )
            self._reload_categories(preserve_selection=False)
            return

        if self.service.is_category_in_use(name):
            messagebox.showerror(
                "Category In Use",
                "Cannot delete a category that is currently used by expenses.",
                parent=self,
            )
            return

        confirm = messagebox.askyesno(
            "Delete Category",
            f"Delete category '{name}'? This action cannot be undone.",
            parent=self,
        )
        if not confirm:
            return

        try:
            self.category_service.delete(category.id)
        except ValidationError as exc:
            messagebox.showerror("Invalid Category", str(exc), parent=self)
            return
        except PersistenceError as exc:
            messagebox.showerror("Storage Error", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            messagebox.showerror("Error", f"Unexpected error deleting category: {exc}", parent=self)
            return

        self._reload_categories(preserve_selection=False)


class IncomeTab(ttk.Frame):
    """UI for managing incomes."""

    def __init__(
        self,
        master: tk.Misc,
        service: IncomeService,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=16, style="Panel.TFrame")
        self.service = service
        self.on_change = on_change

        self.amount_var = tk.StringVar()
        self.currency_var = tk.StringVar(value="USD")
        self.source_var = tk.StringVar()
        self.method_var = tk.StringVar(value=sorted(INCOME_METHODS)[0])
        current_date, current_time = _current_date_time()
        self.received_date_var = tk.StringVar(value=current_date)
        self.received_time_var = tk.StringVar(value=current_time)
        self.description_var = tk.StringVar()
        self.tags_var = tk.StringVar()

        self._build_form()
        self._build_table()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text="Add Income", style="Card.TLabelframe")
        form.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 12))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        def add_field(
            label: str,
            var: tk.StringVar,
            column: int,
            row: int,
            *,
            state: Optional[str] = None,
        ) -> ttk.Entry:
            ttk.Label(form, text=label, style="FormLabel.TLabel").grid(
                column=column, row=row, sticky="w", padx=4, pady=4
            )
            entry = ttk.Entry(form, textvariable=var, style="App.TEntry")
            if state:
                entry.configure(state=state)
            entry.grid(column=column, row=row + 1, sticky="ew", padx=4, pady=(0, 8))
            return entry

        amount_entry = add_field("Amount", self.amount_var, 0, 0)
        amount_entry.bind("<FocusOut>", self._handle_amount_focus_out)

        add_field("Currency", self.currency_var, 1, 0, state="readonly")
        add_field("Source", self.source_var, 0, 2)

        ttk.Label(form, text="Received Method", style="FormLabel.TLabel").grid(
            column=1, row=2, sticky="w", padx=4, pady=4
        )
        method_combo = ttk.Combobox(
            form,
            textvariable=self.method_var,
            values=sorted(INCOME_METHODS),
            state="readonly",
            style="App.TCombobox",
        )
        method_combo.grid(column=1, row=3, sticky="ew", padx=4, pady=(0, 8))

        add_field("Received Date (YYYY-MM-DD)", self.received_date_var, 0, 4)
        add_field("Received Time (HH:MM)", self.received_time_var, 1, 4)
        add_field("Description", self.description_var, 0, 6)
        add_field("Tags (comma separated)", self.tags_var, 1, 6)

        button_row = ttk.Frame(form, style="Panel.TFrame")
        button_row.grid(column=0, row=8, columnspan=2, sticky="e", padx=4, pady=4)
        ttk.Button(
            button_row,
            text="Reset",
            command=self.reset_form,
            style="Secondary.TButton",
        ).grid(column=0, row=0, padx=4)
        ttk.Button(
            button_row,
            text="Add Income",
            command=self.submit,
            style="Primary.TButton",
        ).grid(column=1, row=0, padx=4)

    def _build_table(self) -> None:
        table_frame = ttk.Frame(self, style="Panel.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("date", "source", "method", "amount")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
            style="App.Treeview",
        )
        headings = {
            "date": "Date",
            "source": "Source",
            "method": "Method",
            "amount": "Amount",
        }
        for key, label in headings.items():
            width = 150 if key != "amount" else 120
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=width, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        button_bar = ttk.Frame(table_frame, style="Panel.TFrame")
        button_bar.grid(row=1, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(
            button_bar,
            text="Delete Selected",
            command=self.delete_selected,
            style="Secondary.TButton",
        ).grid(row=0, column=0, padx=4)

    def submit(self) -> None:
        sanitized_amount = sanitize_amount_input(self.amount_var.get())
        try:
            received_at = combine_date_time(self.received_date_var.get(), self.received_time_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Income", "Provide a valid received date and time.", parent=self
            )
            return
        payload = {
            "amount": sanitized_amount,
            "currency": (self.currency_var.get() or "USD").strip().upper(),
            "source": self.source_var.get(),
            "received_method": self.method_var.get(),
            "received_at": received_at,
            "description": self.description_var.get() or None,
            "tags": self._split_tags(self.tags_var.get()),
            "attachment_path": None,
        }

        errors = self._validate(payload)
        if errors:
            messagebox.showerror("Invalid Income", "\n".join(errors), parent=self)
            return

        try:
            self.service.add(payload)
        except ValidationError as exc:
            messagebox.showerror("Invalid Income", str(exc), parent=self)
            return
        except PersistenceError as exc:
            messagebox.showerror("Storage Error", str(exc), parent=self)
            return

        self.reset_form()
        self.populate()
        self.on_change()

    def delete_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No selection", "Please select an income to delete.", parent=self)
            return
        for item_id in selection:
            try:
                self.service.delete(item_id)
            except RecordNotFoundError as exc:
                messagebox.showwarning("Not Found", str(exc), parent=self)
            except PersistenceError as exc:
                messagebox.showerror("Storage Error", str(exc), parent=self)
                break
        self.populate()
        self.on_change()

    def populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for income in self.service.list():
            data = income.to_dict()
            amount_display = f"{data['currency']} {format_amount_display(data['amount'])}"
            try:
                date_part, time_part = split_iso_datetime(data["received_at"])
                received_display = f"{date_part} {time_part}"
            except Exception:
                received_display = data["received_at"]
            values = (
                received_display,
                data["source"],
                data["received_method"],
                amount_display,
            )
            self.tree.insert("", "end", iid=data["id"], values=values)

    def reset_form(self) -> None:
        self.amount_var.set("")
        self.source_var.set("")
        self.description_var.set("")
        self.tags_var.set("")
        current_date, current_time = _current_date_time()
        self.received_date_var.set(current_date)
        self.received_time_var.set(current_time)

    def _handle_amount_focus_out(self, _event: object) -> None:
        self.amount_var.set(format_amount_display(self.amount_var.get()))

    def _validate(self, payload: dict) -> List[str]:
        errors: List[str] = []

        amount_text = payload["amount"].strip()
        if not amount_text:
            errors.append("Amount is required.")
        else:
            try:
                amount_value = Decimal(amount_text)
            except InvalidOperation:
                errors.append("Amount must be a number.")
            else:
                if amount_value <= 0:
                    errors.append("Amount must be greater than zero.")

        if not payload["source"].strip():
            errors.append("Source is required.")

        if not payload["received_method"].strip():
            errors.append("Received method is required.")

        received_text = (payload["received_at"] or "").strip()
        if not received_text:
            errors.append("Received date/time is required.")
        else:
            try:
                received_dt = parse_user_datetime(received_text)
            except Exception:
                errors.append("Received date must be a valid ISO 8601 datetime.")
            else:
                if received_dt > datetime.now(timezone.utc):
                    errors.append("Received date cannot be in the future.")

        return errors

    @staticmethod
    def _split_tags(raw: str) -> Optional[Iterable[str]]:
        cleaned = [tag.strip() for tag in raw.split(",") if tag.strip()]
        return cleaned if cleaned else None


class ExpenseTrackerApp(tk.Tk):
    """Main application window."""

    def __init__(self, data_dir: Path) -> None:
        super().__init__()
        self.title("Expense Tracker")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(bg=PRIMARY_BG)

        self._configure_styles()

        storage = JSONStorage(data_dir)
        self.categories = CategoryService(storage)
        self.expenses = ExpenseService(storage)
        self.incomes = IncomeService(storage)
        self.ledger = LedgerService(self.expenses, self.incomes)

        self.expense_total_var = tk.StringVar(value="0.00")
        self.income_total_var = tk.StringVar(value="0.00")
        self.balance_var = tk.StringVar(value="0.00")

        self._build_layout()
        self.refresh_all()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=PRIMARY_BG)
        style.configure("TLabel", background=PRIMARY_BG, foreground=TEXT_PRIMARY)

        style.configure("Panel.TFrame", background=SECONDARY_BG, relief="flat")
        style.configure("Card.TLabelframe", background=SECONDARY_BG, foreground=TEXT_PRIMARY)
        style.configure("Card.TLabelframe.Label", background=SECONDARY_BG, foreground=TEXT_PRIMARY)
        style.configure("Header.TFrame", background=PRIMARY_BG)
        style.configure("Summary.TFrame", background=SECONDARY_BG)
        style.configure("Metric.TFrame", background=SECONDARY_BG)

        style.configure("FormLabel.TLabel", background=SECONDARY_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=PRIMARY_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 20, "bold"))
        style.configure("MetricLabel.TLabel", background=SECONDARY_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        style.configure("MetricValue.TLabel", background=SECONDARY_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 16, "bold"))
        style.configure(
            "MetricNegative.TFrame",
            background="#321524",
            bordercolor="#f87171",
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "MetricValueNegative.TLabel",
            background="#321524",
            foreground="#fca5a5",
            font=("Segoe UI", 16, "bold"),
        )

        style.configure(
            "App.TEntry",
            fieldbackground=SECONDARY_BG,
            background=SECONDARY_BG,
            foreground=TEXT_PRIMARY,
            insertcolor=TEXT_PRIMARY,
            bordercolor=ACCENT_BG,
        )
        style.map(
            "App.TEntry",
            fieldbackground=[("focus", SECONDARY_BG)],
            foreground=[("disabled", TEXT_MUTED)],
        )

        style.configure(
            "App.TCombobox",
            fieldbackground=SECONDARY_BG,
            background=SECONDARY_BG,
            foreground=TEXT_PRIMARY,
            arrowcolor=TEXT_PRIMARY,
        )
        style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", SECONDARY_BG)],
            foreground=[("disabled", TEXT_MUTED)],
        )

        style.configure(
            "Primary.TButton",
            background=ACCENT_BG,
            foreground=TEXT_PRIMARY,
            bordercolor=ACCENT_BG,
            focustcolor=TEXT_PRIMARY,
            padding=(18, 6),
        )
        style.map(
            "Primary.TButton",
            background=[("active", ACCENT_ACTIVE_BG)],
            foreground=[("disabled", TEXT_MUTED)],
        )

        style.configure(
            "Secondary.TButton",
            background=SECONDARY_BG,
            foreground=TEXT_PRIMARY,
            bordercolor=SECONDARY_BG,
            padding=(14, 6),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", ACCENT_BG)],
            foreground=[("disabled", TEXT_MUTED)],
        )

        style.configure(
            "App.Treeview",
            background=SECONDARY_BG,
            fieldbackground=SECONDARY_BG,
            foreground=TEXT_PRIMARY,
            bordercolor=SECONDARY_BG,
            rowheight=28,
        )
        style.configure(
            "App.Treeview.Heading",
            background=SECONDARY_BG,
            foreground=TEXT_MUTED,
            relief="flat",
        )
        style.map(
            "App.Treeview",
            background=[("selected", ACCENT_BG)],
            foreground=[("selected", TEXT_PRIMARY)],
        )

        style.configure("App.TNotebook", background=PRIMARY_BG, borderwidth=0)
        style.configure(
            "App.TNotebook.Tab",
            background=SECONDARY_BG,
            foreground=TEXT_MUTED,
            padding=(16, 10),
        )
        style.map(
            "App.TNotebook.Tab",
            background=[("selected", ACCENT_BG)],
            foreground=[("selected", TEXT_PRIMARY)],
        )

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=20, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Expense Tracker", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        summary = ttk.Frame(self, padding=(20, 10), style="Summary.TFrame")
        summary.grid(row=1, column=0, sticky="ew")
        summary.columnconfigure((0, 1, 2), weight=1)

        def build_metric(column: int, label: str, var: tk.StringVar) -> tuple[ttk.Frame, ttk.Label]:
            container = ttk.Frame(summary, style="Metric.TFrame", padding=(16, 12))
            container.grid(row=0, column=column, sticky="ew", padx=6)
            ttk.Label(container, text=label, style="MetricLabel.TLabel").grid(row=0, column=0, sticky="w")
            value_label = ttk.Label(container, textvariable=var, style="MetricValue.TLabel")
            value_label.grid(row=1, column=0, sticky="w")
            return container, value_label

        build_metric(0, "Expense Total", self.expense_total_var)
        build_metric(1, "Income Total", self.income_total_var)
        self.balance_container, self.balance_value_label = build_metric(2, "Net Balance", self.balance_var)

        notebook = ttk.Notebook(self, style="App.TNotebook")
        notebook.grid(row=2, column=0, sticky="nsew")

        self.expense_tab = ExpenseTab(notebook, self.expenses, self.categories, self.refresh_all)
        self.income_tab = IncomeTab(notebook, self.incomes, self.refresh_all)

        notebook.add(self.expense_tab, text="Expenses", padding=4)
        notebook.add(self.income_tab, text="Income", padding=4)

    def refresh_all(self) -> None:
        self.expense_tab.populate()
        self.income_tab.populate()
        self.refresh_summary()

    def refresh_summary(self) -> None:
        expenses_total = self.expenses.total()
        incomes_total = self.incomes.total()
        balance = self.ledger.balance()
        self.expense_total_var.set(format_amount_display(expenses_total))
        self.income_total_var.set(format_amount_display(incomes_total))
        self.balance_var.set(format_amount_display(balance))
        if balance < 0:
            self.balance_container.configure(style="MetricNegative.TFrame")
            self.balance_value_label.configure(style="MetricValueNegative.TLabel")
        else:
            self.balance_container.configure(style="Metric.TFrame")
            self.balance_value_label.configure(style="MetricValue.TLabel")


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Tkinter desktop app for the expense tracker")
    parser.add_argument(
        "--data-dir",
        default="data",
        type=Path,
        help="Directory containing JSON storage files (default: ./data)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    app = ExpenseTrackerApp(args.data_dir)
    app.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
