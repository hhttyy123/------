"""Generic dataset storage, import, query, and export services."""

from __future__ import annotations

import csv
import io
import json
import math
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def datasets_dir() -> Path:
    path = Path(settings.DATA_DIR) / "datasets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def index_path() -> Path:
    path = Path(settings.DATA_DIR) / "_datasets_index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    return path


def upload_path(upload_id: str) -> Path:
    return Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"


def dataset_path(dataset_id: str) -> Path:
    return datasets_dir() / f"{dataset_id}.json"


def read_index() -> list[dict[str, Any]]:
    try:
        data = json.loads(index_path().read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def write_index(items: list[dict[str, Any]]) -> None:
    index_path().write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def read_dataset(dataset_id: str) -> dict[str, Any] | None:
    path = dataset_path(dataset_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def write_dataset(dataset: dict[str, Any]) -> None:
    dataset_path(dataset["dataset_id"]).write_text(
        json.dumps(json_safe(dataset), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_datasets() -> list[dict[str, Any]]:
    return read_index()


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    return read_dataset(dataset_id)


def preview_sheet(upload_id: str, sheet_name: str, header_row: int | None = None, limit: int = 100) -> dict[str, Any]:
    path = upload_path(upload_id)
    if not path.exists():
        raise FileNotFoundError("上传文件不存在")
    header = detect_header_row(path, sheet_name) if header_row is None else header_row
    df = read_excel_sheet(path, sheet_name, header)
    columns = make_columns(df.columns)
    rows = dataframe_to_rows(df.head(limit), columns)
    return {
        "upload_id": upload_id,
        "sheet_name": sheet_name,
        "header_row": header,
        "columns": columns,
        "rows": rows,
        "total_rows": int(len(df)),
    }


def create_dataset_from_sheet(
    upload_id: str,
    sheet_name: str,
    name: str | None = None,
    header_row: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    path = upload_path(upload_id)
    if not path.exists():
        raise FileNotFoundError("上传文件不存在")
    header = detect_header_row(path, sheet_name) if header_row is None else header_row

    # 读取原始数据（不含表头），用于检测双层表头
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)

    # 检测是否存在双层表头：下一行有足够多的非空值来填充"未命名"列
    main_headers = [str(v).strip() if pd.notna(v) else "" for v in raw.iloc[header]]
    sub_row_idx = header + 1
    has_sub_headers = False
    if sub_row_idx < len(raw):
        sub_row = raw.iloc[sub_row_idx]
        sub_values = [str(v).strip() if pd.notna(v) and str(v).strip() else "" for v in sub_row]
        # 如果子行在空/未命名列位置有值，说明是双层表头
        unnamed_count = sum(1 for h in main_headers if not h or "unnamed" in h.lower())
        sub_fill_count = sum(1 for i, (mh, sv) in enumerate(zip(main_headers, sub_values)) if (not mh or "unnamed" in mh.lower()) and sv)
        has_sub_headers = unnamed_count >= 3 and sub_fill_count >= 3

    if has_sub_headers:
        # 合并双层表头：子表头填充主表头的空/未命名位置
        merged_headers = []
        for main, sub in zip(main_headers, sub_values):
            if main and "unnamed" not in main.lower():
                merged_headers.append(main)
            elif sub:
                merged_headers.append(sub)
            else:
                merged_headers.append(main if main else f"未命名列{len(merged_headers)+1}")
        # 跳过标题行和双层表头行，取数据
        data_start = header + 2
        data_df = raw.iloc[data_start:].reset_index(drop=True)
        data_df.columns = merged_headers[:len(data_df.columns)]
    else:
        # 单层表头，标准流程
        data_df = raw.iloc[header + 1:].reset_index(drop=True)
        data_df.columns = [str(h) if pd.notna(h) and str(h).strip() else f"列{i+1}" for i, h in enumerate(raw.iloc[header])]

    data_df = data_df.dropna(how="all").reset_index(drop=True)
    columns = make_columns(data_df.columns)
    rows = dataframe_to_rows(data_df, columns)

    ts = now_str()
    dataset_id = uuid.uuid4().hex
    dataset = {
        "dataset_id": dataset_id,
        "name": name or sheet_name,
        "category": category or "other",
        "source_file": path.name,
        "upload_id": upload_id,
        "sheet_name": sheet_name,
        "header_row": header,
        "columns": columns,
        "rows": rows,
        "created_at": ts,
        "updated_at": ts,
    }
    write_dataset(dataset)
    upsert_index(dataset)
    return dataset


def create_workbook_dataset(
    upload_id: str,
    name: str,
    category: str = "other",
) -> dict[str, Any]:
    """导入整本工作簿：自动识别所有 Sheet，合并为一个数据集，附加「来源工作表」列。"""
    path = upload_path(upload_id)
    if not path.exists():
        raise FileNotFoundError("上传文件不存在")

    xls = pd.ExcelFile(path, engine="openpyxl")
    all_rows: list[dict[str, Any]] = []
    all_columns: list[dict[str, Any]] = []
    seen_col_keys: set[str] = set()

    for sheet_name in xls.sheet_names:
        # 跳过明显非数据的 Sheet
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
        raw = raw.dropna(how="all").dropna(axis=1, how="all")
        if raw.shape[0] < 3 or raw.shape[1] < 3:
            continue

        header = detect_header_row(path, sheet_name)
        main_headers = [str(v).strip() if pd.notna(v) else "" for v in raw.iloc[header]]
        sub_row_idx = header + 1

        has_sub_headers = False
        if sub_row_idx < len(raw):
            sub_row = raw.iloc[sub_row_idx]
            sub_values = [str(v).strip() if pd.notna(v) and str(v).strip() else "" for v in sub_row]
            unnamed_count = sum(1 for h in main_headers if not h or "unnamed" in h.lower())
            sub_fill_count = sum(1 for i, (mh, sv) in enumerate(zip(main_headers, sub_values)) if (not mh or "unnamed" in mh.lower()) and sv)
            has_sub_headers = unnamed_count >= 3 and sub_fill_count >= 3

        if has_sub_headers:
            merged_headers = []
            for main, sub in zip(main_headers, sub_values):
                if main and "unnamed" not in main.lower():
                    merged_headers.append(main)
                elif sub:
                    merged_headers.append(sub)
                else:
                    merged_headers.append(main if main else f"列{len(merged_headers)+1}")
            data_start = header + 2
        else:
            merged_headers = [str(h) if pd.notna(h) and str(h).strip() else f"列{i+1}" for i, h in enumerate(raw.iloc[header])]
            data_start = header + 1

        data_df = raw.iloc[data_start:].reset_index(drop=True)
        data_df.columns = merged_headers[:len(data_df.columns)]
        data_df = data_df.dropna(how="all").reset_index(drop=True)

        # 添加来源工作表标记
        data_df["来源工作表"] = sheet_name

        cols = make_columns(data_df.columns)
        rows = dataframe_to_rows(data_df, cols)

        # 记录列信息（用第一个有效 Sheet 的列作为基准）
        if not all_columns:
            all_columns = cols
            seen_col_keys = {c["key"] for c in cols}

        all_rows.extend(rows)

    if not all_rows:
        raise ValueError("没有找到可导入的数据工作表")

    # 确保所有行都有完整的列（补充缺失列）
    for row in all_rows:
        for col in all_columns:
            if col["key"] not in row:
                row[col["key"]] = ""
        # 只保留基准列
        extra = [k for k in list(row.keys()) if k not in seen_col_keys and k != "id"]
        for k in extra:
            del row[k]

    ts = now_str()
    dataset_id = uuid.uuid4().hex
    dataset = {
        "dataset_id": dataset_id,
        "name": name,
        "category": category,
        "source_file": path.name,
        "upload_id": upload_id,
        "sheet_name": "全部工作表",
        "header_row": 0,
        "columns": all_columns,
        "rows": all_rows,
        "created_at": ts,
        "updated_at": ts,
    }
    write_dataset(dataset)
    upsert_index(dataset)
    return dataset


def update_dataset_meta(dataset_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    for key in ("name", "category"):
        if key in patch:
            dataset[key] = patch[key]
    dataset["updated_at"] = now_str()
    write_dataset(dataset)
    upsert_index(dataset)
    return dataset


def delete_dataset(dataset_id: str) -> bool:
    path = dataset_path(dataset_id)
    if not path.exists():
        return False
    path.unlink()
    write_index([item for item in read_index() if item.get("dataset_id") != dataset_id])
    return True


def list_rows(dataset_id: str, search: str = "", limit: int = 500, offset: int = 0) -> dict[str, Any] | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    rows = filter_search(dataset.get("rows", []), search)
    total = len(rows)
    return {
        "dataset_id": dataset_id,
        "columns": dataset.get("columns", []),
        "total": total,
        "rows": rows[offset:offset + limit],
    }


def create_row(dataset_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    rows = dataset.setdefault("rows", [])
    next_id = max([int(row.get("id", 0) or 0) for row in rows] + [0]) + 1
    row = normalize_row(data, dataset.get("columns", []))
    row["id"] = next_id
    rows.append(row)
    dataset["updated_at"] = now_str()
    write_dataset(dataset)
    upsert_index(dataset)
    return row


def update_row(dataset_id: str, row_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    rows = dataset.get("rows", [])
    for index, row in enumerate(rows):
        if int(row.get("id", 0) or 0) == row_id:
            updated = deepcopy(row)
            updated.update(normalize_row(data, dataset.get("columns", []), include_missing=False))
            updated["id"] = row_id
            rows[index] = updated
            dataset["updated_at"] = now_str()
            write_dataset(dataset)
            upsert_index(dataset)
            return updated
    return None


def delete_row(dataset_id: str, row_id: int) -> bool:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return False
    rows = dataset.get("rows", [])
    kept = [row for row in rows if int(row.get("id", 0) or 0) != row_id]
    if len(kept) == len(rows):
        return False
    dataset["rows"] = kept
    dataset["updated_at"] = now_str()
    write_dataset(dataset)
    upsert_index(dataset)
    return True


def query_dataset(dataset_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    rows = dataset.get("rows", [])
    for item in payload.get("filters", []):
        rows = [row for row in rows if match_filter(row, item)]
    total = len(rows)
    summary = numeric_summary(rows, dataset.get("columns", []))
    groups = grouped_summary(rows, payload.get("group_by") or [], payload.get("aggregations") or [])
    limit = int(payload.get("limit") or 500)
    return {
        "total": total,
        "rows": rows[:limit],
        "summary": summary,
        "groups": groups,
    }


def export_dataset_csv(dataset_id: str) -> str | None:
    dataset = read_dataset(dataset_id)
    if not dataset:
        return None
    output = io.StringIO()
    fieldnames = ["id"] + [column["key"] for column in dataset.get("columns", [])]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in dataset.get("rows", []):
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return "\ufeff" + output.getvalue()


def upsert_index(dataset: dict[str, Any]) -> None:
    items = [item for item in read_index() if item.get("dataset_id") != dataset["dataset_id"]]
    items.insert(0, {
        "dataset_id": dataset["dataset_id"],
        "name": dataset["name"],
        "category": dataset.get("category", "other"),
        "source_file": dataset.get("source_file", ""),
        "sheet_name": dataset.get("sheet_name", ""),
        "row_count": len(dataset.get("rows", [])),
        "column_count": len(dataset.get("columns", [])),
        "created_at": dataset.get("created_at", ""),
        "updated_at": dataset.get("updated_at", ""),
    })
    write_index(items)


def read_excel_sheet(path: Path, sheet_name: str, header_row: int) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, engine="openpyxl")
    df = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return df


def detect_header_row(path: Path, sheet_name: str, scan_rows: int = 12) -> int:
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=scan_rows, engine="openpyxl")
    best_index = 0
    best_score = -1
    for index, row in raw.iterrows():
        values = [str(value).strip() for value in row.tolist() if pd.notna(value) and str(value).strip()]
        text_count = sum(1 for value in values if not is_number_like(value))
        score = len(values) + text_count
        if score > best_score:
            best_index = int(index)
            best_score = score
    return best_index


def make_columns(raw_columns: Any) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    columns = []
    for index, raw in enumerate(raw_columns):
        label = clean_header(raw, index)
        count = seen.get(label, 0) + 1
        seen[label] = count
        key = label if count == 1 else f"{label}_{count}"
        columns.append({
            "key": key,
            "label": label,
            "type": "text",
            "visible": True,
        })
    return columns


def clean_header(value: Any, index: int) -> str:
    text = str(value or "").strip()
    if not text or text.lower().startswith("unnamed:"):
        return f"未命名列{index + 1}"
    if "." in text and text.rsplit(".", 1)[1].isdigit():
        return text.rsplit(".", 1)[0]
    return text


def dataframe_to_rows(df: pd.DataFrame, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for offset, (_, source) in enumerate(df.iterrows(), start=1):
        row = {"id": offset}
        for index, column in enumerate(columns):
            value = source.iloc[index] if index < len(source) else ""
            row[column["key"]] = clean_cell(value)
        rows.append(row)
    return rows


def clean_cell(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return int(value) if value == int(value) else value
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    return value


def normalize_row(data: dict[str, Any], columns: list[dict[str, Any]], include_missing: bool = True) -> dict[str, Any]:
    keys = [column["key"] for column in columns]
    if include_missing:
        return {key: data.get(key, "") for key in keys}
    return {key: value for key, value in data.items() if key in keys}


def filter_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    if not search:
        return rows
    needle = search.lower()
    return [row for row in rows if needle in " ".join(str(v) for v in row.values()).lower()]


def match_filter(row: dict[str, Any], item: dict[str, Any]) -> bool:
    field = item.get("field")
    op = item.get("operator")
    value = item.get("value")
    current = row.get(field, "")
    current_text = str(current)
    if op == "contains":
        return str(value).lower() in current_text.lower()
    if op == "not_contains":
        return str(value).lower() not in current_text.lower()
    if op == "eq":
        return current_text == str(value)
    if op == "ne":
        return current_text != str(value)
    if op == "empty":
        return current in ("", None)
    if op == "not_empty":
        return current not in ("", None)
    if op in {"gt", "gte", "lt", "lte"}:
        left = to_float(current)
        right = to_float(value)
        if left is None or right is None:
            return False
        return {"gt": left > right, "gte": left >= right, "lt": left < right, "lte": left <= right}[op]
    if op == "between" and isinstance(value, list) and len(value) == 2:
        return str(value[0]) <= current_text[:10] <= str(value[1])
    return True


def numeric_summary(rows: list[dict[str, Any]], columns: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for column in columns:
        key = column["key"]
        values = [to_float(row.get(key)) for row in rows]
        nums = [value for value in values if value is not None]
        if nums:
            result[key] = {
                "sum": round(sum(nums), 2),
                "avg": round(sum(nums) / len(nums), 2),
                "count": len(nums),
            }
    return result


def grouped_summary(rows: list[dict[str, Any]], group_by: list[str], aggregations: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not group_by:
        return []
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in group_by)
        item = grouped.setdefault(key, {field: row.get(field, "") for field in group_by} | {"count": 0})
        item["count"] += 1
        for agg in aggregations:
            field = agg.get("field")
            agg_type = agg.get("type", "sum")
            num = to_float(row.get(field))
            if num is None:
                continue
            out_key = f"{field}_{agg_type}"
            if agg_type == "sum":
                item[out_key] = round(float(item.get(out_key, 0)) + num, 2)
    return list(grouped.values())


def to_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        num = float(value)
        return None if math.isnan(num) else num
    except (TypeError, ValueError):
        return None


def is_number_like(value: Any) -> bool:
    return to_float(value) is not None
