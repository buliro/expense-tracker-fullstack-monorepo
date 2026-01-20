"""Persistence utilities for the expense tracker core services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .exceptions import PersistenceError


class JSONStorage:
    """Simple file-based JSON storage with crash-safe writes."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)

    def load(self, resource: str) -> List[Dict[str, Any]]:
        path = self._base_path / resource
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise PersistenceError(f"Corrupted JSON data in {path}") from exc
        except OSError as exc:
            raise PersistenceError(f"Unable to read from {path}") from exc

        if not isinstance(payload, list):
            raise PersistenceError(f"Expected list payload in {path}")
        return payload

    def save(self, resource: str, records: Iterable[Dict[str, Any]]) -> None:
        path = self._base_path / resource
        temp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(list(records), handle, indent=2)
                handle.flush()
        except OSError as exc:
            raise PersistenceError(f"Unable to write to {temp_path}") from exc
        # Use replace for atomic move on POSIX; ensures crash-safe persistence.
        temp_path.replace(path)

    @property
    def base_path(self) -> Path:
        return self._base_path
