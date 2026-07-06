"""JSON repository layer for module records.

This keeps the current JSON storage model but gives the rest of the app a
stable data-access boundary that can later move to SQLite/PostgreSQL.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class JsonRepository:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or settings.DATA_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, module: str) -> Path:
        return self.base_dir / f"{module}.json"

    def list_records(self, module: str) -> list[dict[str, Any]]:
        path = self.path_for(module)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def write_records(self, module: str, records: list[dict[str, Any]]) -> None:
        path = self.path_for(module)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_record(self, module: str, record_id: int) -> dict[str, Any] | None:
        for record in self.list_records(module):
            if int(record.get("id", 0) or 0) == record_id:
                return record
        return None

    def create_record(self, module: str, data: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
        records = self.list_records(module)
        next_id = max([int(r.get("id", 0) or 0) for r in records] + [0]) + 1
        ts = now_str()
        record = deepcopy(data)
        record.update({
            "id": next_id,
            "created_at": record.get("created_at") or ts,
            "updated_at": ts,
            "_source": source or record.get("_source") or {"type": "manual"},
        })
        records.append(record)
        self.write_records(module, records)
        return record

    def create_many(self, module: str, rows: list[dict[str, Any]], source: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not rows:
            return []
        records = self.list_records(module)
        next_id = max([int(r.get("id", 0) or 0) for r in records] + [0]) + 1
        ts = now_str()
        created = []
        for offset, row in enumerate(rows):
            record = deepcopy(row)
            record.update({
                "id": next_id + offset,
                "created_at": record.get("created_at") or ts,
                "updated_at": ts,
                "_source": source or record.get("_source") or {"type": "manual"},
            })
            created.append(record)
        records.extend(created)
        self.write_records(module, records)
        return created

    def update_record(self, module: str, record_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
        records = self.list_records(module)
        for index, record in enumerate(records):
            if int(record.get("id", 0) or 0) == record_id:
                updated = deepcopy(record)
                updated.update(patch)
                updated["id"] = record.get("id")
                updated["created_at"] = record.get("created_at")
                updated["updated_at"] = now_str()
                records[index] = updated
                self.write_records(module, records)
                return updated
        return None

    def delete_record(self, module: str, record_id: int) -> bool:
        records = self.list_records(module)
        kept = [r for r in records if int(r.get("id", 0) or 0) != record_id]
        if len(kept) == len(records):
            return False
        self.write_records(module, kept)
        return True

    def append_system_record(self, module: str, data: dict[str, Any]) -> dict[str, Any]:
        return self.create_record(module, data, source={"type": "system"})


repo = JsonRepository()
