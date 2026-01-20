"""Flask REST API exposing the expense tracker services."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from common.exceptions import PersistenceError, RecordNotFoundError, ValidationError
from common.services import CategoryService, ExpenseService, IncomeService, LedgerService
from common.storage import JSONStorage


def create_app(data_dir: Optional[Path] = None) -> Flask:
    app = Flask(__name__)

    env_name = os.getenv("EXPENSE_TRACKER_ENV", "prod").lower()
    if env_name in {"dev", "development"}:
        CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    else:
        allowed_origins = os.getenv("EXPENSE_TRACKER_ALLOWED_ORIGINS")
        if allowed_origins:
            origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
            CORS(app, resources={r"/*": {"origins": origins}}, supports_credentials=True)
        else:
            CORS(app)

    storage = JSONStorage(Path(data_dir or "data"))
    category_service = CategoryService(storage)
    expense_service = ExpenseService(storage)
    income_service = IncomeService(storage)
    ledger = LedgerService(expense_service, income_service)

    def _success(payload: Any, status: int = 200):
        if status == 204:
            return ("", status)
        return jsonify(payload), status

    def _handle_error(exc: Exception, status: int, message: str):
        app.logger.error("%s: %s", message, exc)
        return jsonify({"error": message, "details": str(exc)}), status

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return _handle_error(exc, 400, "Validation error")

    @app.errorhandler(RecordNotFoundError)
    def handle_not_found(exc: RecordNotFoundError):
        return _handle_error(exc, 404, "Record not found")

    @app.errorhandler(PersistenceError)
    def handle_persistence_error(exc: PersistenceError):
        return _handle_error(exc, 500, "Persistence error")

    def _json_body() -> Dict[str, Any]:
        if not request.is_json:
            raise ValidationError("Request content must be application/json")
        data = request.get_json(silent=True)
        if data is None:
            raise ValidationError("Malformed JSON body")
        return data

    def _clean_filters(raw: Dict[str, Optional[str]]) -> Dict[str, str]:
        return {k: v for k, v in raw.items() if v not in (None, "")}

    @app.get("/categories")
    def list_categories():
        categories = category_service.list()
        return _success({"items": [category.to_dict() for category in categories]})

    @app.post("/categories")
    def create_category():
        payload = _json_body()
        category = category_service.add(payload)
        return _success(category.to_dict(), 201)

    @app.put("/categories/<category_id>")
    def update_category(category_id: str):
        existing = category_service.get(category_id)
        payload = _json_body()
        category = category_service.update(category_id, payload)
        if existing.name != category.name:
            expense_service.rename_category(existing.name, category.name)
        return _success(category.to_dict())

    @app.delete("/categories/<category_id>")
    def delete_category(category_id: str):
        category = category_service.get(category_id)
        if expense_service.is_category_in_use(category.name):
            raise ValidationError("Cannot delete a category that is in use by expenses")
        category_service.delete(category_id)
        return _success({}, 204)

    @app.get("/expenses")
    def list_expenses():
        filters = {
            "category": request.args.get("category"),
            "payment_method": request.args.get("payment_method"),
            "tag": request.args.get("tag"),
            "merchant": request.args.get("merchant"),
            "start": request.args.get("start"),
            "end": request.args.get("end"),
        }
        applied = _clean_filters(filters)
        expenses = expense_service.list(**applied)
        total = expense_service.total(**applied)
        return _success({
            "items": [expense.to_dict() for expense in expenses],
            "total": f"{total:.2f}",
        })

    @app.post("/expenses")
    def create_expense():
        payload = _json_body()
        expense = expense_service.add(payload)
        return _success(expense.to_dict(), 201)

    @app.get("/expenses/<expense_id>")
    def get_expense(expense_id: str):
        expense = expense_service.get(expense_id)
        return _success(expense.to_dict())

    @app.put("/expenses/<expense_id>")
    def update_expense(expense_id: str):
        payload = _json_body()
        expense = expense_service.update(expense_id, payload)
        return _success(expense.to_dict())

    @app.delete("/expenses/<expense_id>")
    def delete_expense(expense_id: str):
        expense_service.delete(expense_id)
        return _success({}, 204)

    @app.get("/incomes")
    def list_incomes():
        filters = {
            "source": request.args.get("source"),
            "received_method": request.args.get("received_method"),
            "tag": request.args.get("tag"),
            "start": request.args.get("start"),
            "end": request.args.get("end"),
        }
        applied = _clean_filters(filters)
        incomes = income_service.list(**applied)
        total = income_service.total(**applied)
        return _success({
            "items": [income.to_dict() for income in incomes],
            "total": f"{total:.2f}",
        })

    @app.post("/incomes")
    def create_income():
        payload = _json_body()
        income = income_service.add(payload)
        return _success(income.to_dict(), 201)

    @app.get("/incomes/<income_id>")
    def get_income(income_id: str):
        income = income_service.get(income_id)
        return _success(income.to_dict())

    @app.put("/incomes/<income_id>")
    def update_income(income_id: str):
        payload = _json_body()
        income = income_service.update(income_id, payload)
        return _success(income.to_dict())

    @app.delete("/incomes/<income_id>")
    def delete_income(income_id: str):
        income_service.delete(income_id)
        return _success({}, 204)

    @app.get("/summary")
    def summary():
        filters = {
            "start": request.args.get("start"),
            "end": request.args.get("end"),
            "category": request.args.get("category"),
            "source": request.args.get("source"),
            "tag": request.args.get("tag"),
        }
        applied = _clean_filters(filters)
        balance = ledger.balance(**applied)
        return _success({"balance": f"{balance:.2f}"})

    return app
