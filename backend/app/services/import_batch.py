"""Automatic import preparation and commit workflow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import settings
from app.registry.loader import get_module, get_registry
from app.services.agent_pipeline import _convert_all, run_analysis
from app.services.business import create_business_records, log_action
from app.services.excel_reader import detect_header_row, read_sheet_full, read_workbook_meta
from app.services.repository import repo


def batch_dir() -> Path:
    path = Path(settings.DATA_DIR) / "_import_batches"
    path.mkdir(parents=True, exist_ok=True)
    return path


def batch_path(batch_id: str) -> Path:
    return batch_dir() / f"{batch_id}.json"


def cache_path() -> Path:
    path = Path(settings.DATA_DIR) / "_fingerprint_cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    return path


def load_cache() -> dict[str, Any]:
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_cache(cache: dict[str, Any]) -> None:
    cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def make_fingerprint(sheet_name: str, header_row: int, headers: list[str]) -> str:
    normalized = "|".join(str(h).strip().lower() for h in headers)
    return hashlib.sha256(f"{sheet_name}|{header_row}|{normalized}".encode("utf-8")).hexdigest()


def save_batch(batch: dict[str, Any]) -> dict[str, Any]:
    safe_batch = json_safe(batch)
    batch_path(safe_batch["batch_id"]).write_text(json.dumps(safe_batch, ensure_ascii=False, indent=2), encoding="utf-8")
    return safe_batch


def get_batch(batch_id: str) -> dict[str, Any] | None:
    path = batch_path(batch_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


async def prepare_import(upload_id: str, sheet_name: str | None = None, sample_size: int = 10) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError("上传文件不存在")

    sheets = [s for s in read_workbook_meta(file_path) if s.row_count > 0 and s.column_count > 0]
    if not sheets:
        raise ValueError("没有找到可整理的工作表")
    if sheet_name is None:
        workbook_batch = await prepare_workbook_import(file_path, upload_id, sheets, sample_size)
        return save_batch(workbook_batch)

    chosen = sheet_name

    header_row = detect_header_row(file_path, chosen, scan_rows=10)
    df = read_sheet_full(file_path, chosen, header_row=header_row)
    headers = [str(h).strip() for h in df.columns]
    fingerprint = make_fingerprint(chosen, header_row, headers)

    cache = load_cache()
    cached = cache.get(fingerprint)
    cache_hit = bool(cached)

    if cached:
        analysis = analysis_from_cache(cached, df, header_row)
    else:
        rules_analysis = rule_based_analysis(df, chosen, header_row)
        if rules_analysis["classification"]["module"]:
            analysis = rules_analysis
        else:
            try:
                analysis = await run_analysis(file_path, chosen, sample_size)
            except Exception as exc:
                fallback = rule_based_analysis(df, chosen, header_row, allow_weak=True)
                if fallback["classification"]["module"]:
                    fallback["_debug"]["ai_error"] = str(exc)
                    analysis = fallback
                else:
                    raise

    module_key = analysis["classification"]["module"]
    module = get_module(module_key)
    if not module:
        raise ValueError("鏃犳硶璇嗗埆涓氬姟妯″潡")

    records = apply_module_defaults(module_key, analysis.get("preview_rows", []))
    issues = validate_records(module_key, records)
    blocked_rows = {issue["row_index"] for issue in issues if issue["severity"] == "blocker"}
    rows_ready = max(0, len(records) - len(blocked_rows))

    batch = {
        "batch_id": uuid.uuid4().hex,
        "filename": file_path.name,
        "upload_id": upload_id,
        "module": module_key,
        "module_label": module.module_label,
        "sheet_name": chosen,
        "status": "prepared",
        "rows_total": len(records),
        "rows_ready": rows_ready,
        "rows_blocked": len(blocked_rows),
        "records": records,
        "display_records": records_to_display(module_key, module.module_label, chosen, records),
        "issues": issues,
        "fingerprint": fingerprint,
        "cache_hit": cache_hit,
        "header_row_index": analysis.get("header_row_index", header_row),
        "_debug": {
            "field_mappings": analysis.get("field_mappings", []),
            "source": "cache" if cache_hit else "ai",
            "ai": analysis.get("_debug", {}),
        },
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return save_batch(batch)


async def prepare_workbook_import(file_path: Path, upload_id: str, sheets: list[Any], sample_size: int = 10) -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    sheet_reports: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    all_display_rows: list[dict[str, Any]] = []
    debug: dict[str, Any] = {"sheets": []}
    seen_profit_months: set[str] = set()

    for sheet in sheets:
        try:
            report = await prepare_sheet_report(file_path, upload_id, sheet.name, sample_size)
            profit_month = next(
                (
                    str(target.get("records", [{}])[0].get("month"))
                    for target in report["targets"]
                    if target.get("module") == "profit" and target.get("records")
                ),
                "",
            )
            if profit_month and profit_month in seen_profit_months:
                sheet_reports.append({
                    "sheet_name": sheet.name,
                    "status": "skipped",
                    "message": f"已跳过：{profit_month} 的利润核算已整理，避免重复导入",
                    "rows_total": sheet.row_count,
                    "targets": [],
                })
                continue
            if profit_month:
                seen_profit_months.add(profit_month)
            sheet_reports.append(report["sheet_report"])
            targets.extend(report["targets"])
            all_issues.extend(report["issues"])
            all_display_rows.extend(report["display_records"])
            debug["sheets"].append(report.get("_debug", {}))
        except Exception as exc:
            sheet_reports.append({
                "sheet_name": sheet.name,
                "status": "skipped",
                "message": f"暂未整理：{exc}",
                "rows_total": sheet.row_count,
                "targets": [],
            })

    rows_total = sum(target["rows_total"] for target in targets)
    rows_ready = sum(target["rows_ready"] for target in targets)
    blocked_rows = len({(issue.get("sheet_name"), issue.get("row_index"), issue.get("field")) for issue in all_issues if issue.get("severity") == "blocker"})

    return {
        "batch_id": uuid.uuid4().hex,
        "filename": file_path.name,
        "upload_id": upload_id,
        "module": "workbook",
        "module_label": "整本工作簿",
        "sheet_name": "全部工作表",
        "status": "prepared",
        "rows_total": rows_total,
        "rows_ready": rows_ready,
        "rows_blocked": blocked_rows,
        "records": all_display_rows,
        "display_records": all_display_rows,
        "targets": targets,
        "sheet_reports": sheet_reports,
        "issues": all_issues,
        "fingerprint": workbook_fingerprint(sheet_reports),
        "cache_hit": False,
        "header_row_index": 0,
        "_debug": debug,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


async def prepare_sheet_report(file_path: Path, upload_id: str, sheet_name: str, sample_size: int) -> dict[str, Any]:
    raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl").dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    profit = extract_profit_summary(raw_df, sheet_name)
    if profit["record"]:
        issues = validate_records("profit", [profit["record"]])
        target = make_target("profit", "利润核算", sheet_name, [profit["record"]], issues)
        return {
            "sheet_report": {
                "sheet_name": sheet_name,
                "status": "ready",
                "message": f"已整理为利润核算，收入 {profit['display_record'].get('总收入', 0)}，净利润 {profit['display_record'].get('净利润', 0)}",
                "rows_total": 1,
                "targets": [{"module": target["module"], "module_label": target["module_label"], "rows_ready": target["rows_ready"], "rows_blocked": target["rows_blocked"]}],
            },
            "targets": [target],
            "issues": tag_issues(sheet_name, issues),
            "display_records": [profit["display_record"]],
            "_debug": {"sheet": sheet_name, "source": "profit_summary_rules"},
        }

    receivables = extract_receivable_records(raw_df, sheet_name)
    if receivables["records"]:
        issues = validate_records("accounts_receivable", receivables["records"])
        target = make_target("accounts_receivable", "鍥炴绠＄悊", sheet_name, receivables["records"], issues)
        return {
            "sheet_report": {
                "sheet_name": sheet_name,
                "status": "ready",
                "message": f"已整理为应收账款，共 {len(receivables['records'])} 条",
                "rows_total": len(receivables["records"]),
                "targets": [{"module": target["module"], "module_label": target["module_label"], "rows_ready": target["rows_ready"], "rows_blocked": target["rows_blocked"]}],
            },
            "targets": [target],
            "issues": tag_issues(sheet_name, issues),
            "display_records": receivables["display_records"],
            "_debug": {"sheet": sheet_name, "source": "receivable_rules"},
        }

    header_row = detect_header_row(file_path, sheet_name, scan_rows=10)
    df = read_sheet_full(file_path, sheet_name, header_row=header_row, fill_merged=False)
    headers = [str(h).strip() for h in df.columns]
    fingerprint = make_fingerprint(sheet_name, header_row, headers)

    journal = extract_journal_flows(df, sheet_name)
    if journal["records"]:
        targets = []
        journal_issues = validate_records("journal", journal["records"])
        finance_records = journal_to_finance(journal["records"])
        finance_issues = validate_records("finance", finance_records)
        targets.append(make_target("journal", "日记账", sheet_name, journal["records"], journal_issues))
        targets.append(make_target("finance", "财务记录", sheet_name, finance_records, finance_issues))
        issues = tag_issues(sheet_name, journal_issues + finance_issues)
        return {
            "sheet_report": {
                "sheet_name": sheet_name,
                "status": "ready",
                "message": f"已整理为收支流水，共 {len(journal['records'])} 条",
                "rows_total": len(journal["records"]),
                "targets": [{"module": t["module"], "module_label": t["module_label"], "rows_ready": t["rows_ready"], "rows_blocked": t["rows_blocked"]} for t in targets],
            },
            "targets": targets,
            "issues": issues,
            "display_records": journal["display_records"],
            "_debug": {"sheet": sheet_name, "source": "parallel_journal_rules", "fingerprint": fingerprint, "groups": journal["groups"]},
        }

    single_sheet = await asyncio.wait_for(
        prepare_single_sheet_analysis(file_path, sheet_name, df, header_row, sample_size),
        timeout=20,
    )
    module_key = single_sheet["module"]
    targets = [make_target(module_key, single_sheet["module_label"], sheet_name, single_sheet["records"], single_sheet["issues"])]
    return {
        "sheet_report": {
            "sheet_name": sheet_name,
            "status": "ready",
            "message": f"已整理为{single_sheet['module_label']}，共 {len(single_sheet['records'])} 条",
            "rows_total": len(single_sheet["records"]),
            "targets": [{"module": t["module"], "module_label": t["module_label"], "rows_ready": t["rows_ready"], "rows_blocked": t["rows_blocked"]} for t in targets],
        },
        "targets": targets,
        "issues": tag_issues(sheet_name, single_sheet["issues"]),
        "display_records": single_sheet["display_records"],
        "_debug": single_sheet.get("_debug", {}),
    }


async def prepare_single_sheet_analysis(file_path: Path, sheet_name: str, df, header_row: int, sample_size: int) -> dict[str, Any]:
    rules_analysis = rule_based_analysis(df, sheet_name, header_row)
    if rules_analysis["classification"]["module"]:
        analysis = rules_analysis
    else:
        try:
            analysis = await run_analysis(file_path, sheet_name, sample_size)
        except Exception as exc:
            fallback = rule_based_analysis(df, sheet_name, header_row, allow_weak=True)
            if fallback["classification"]["module"]:
                fallback["_debug"]["ai_error"] = str(exc)
                analysis = fallback
            else:
                raise
    module_key = analysis["classification"]["module"]
    module = get_module(module_key)
    if not module:
        raise ValueError("鏃犳硶璇嗗埆涓氬姟妯″潡")
    records = apply_module_defaults(module_key, analysis.get("preview_rows", []))
    issues = validate_records(module_key, records)
    return {
        "module": module_key,
        "module_label": module.module_label,
        "records": records,
        "display_records": records_to_display(module_key, module.module_label, sheet_name, records),
        "issues": issues,
        "_debug": analysis.get("_debug", {}),
    }


def extract_profit_summary(df, sheet_name: str) -> dict[str, Any]:
    month = month_from_sheet(sheet_name)
    if not month or df.shape[1] < 17:
        return {"record": None, "display_record": None}

    header_row = None
    for idx, row in df.head(8).iterrows():
        text = "".join(str(clean_value(value)) for value in row)
        if "企业名称" in text and "开票金额" in text and "净利润" in text:
            header_row = idx
            break
    if header_row is None:
        return {"record": None, "display_record": None}

    main_headers = [str(clean_value(value)) for value in df.iloc[header_row].tolist()]
    sub_headers = [str(clean_value(value)) for value in df.iloc[header_row + 1].tolist()] if header_row + 1 < len(df) else []
    main_map = {normalize_header(name): idx for idx, name in enumerate(main_headers) if name}
    sub_map = {normalize_header(name): idx for idx, name in enumerate(sub_headers) if name}

    serial_col = main_map.get("搴忓彿", 0)
    company_col = main_map.get("浼佷笟鍚嶇О", 2)
    income_col = main_map.get("开票金额", 4)
    net_profit_col = main_map.get("鍑€鍒╂鼎", 15)
    salary_col = sub_map.get("宸ヤ汉宸ヨ祫", -1)
    recruitment_col = sub_map.get("鍚岃杩旇垂", -1)
    other_cols = [
        col for name, col in sub_map.items()
        if name in {"开票税额", "附加税", "保险费", "提成", "交际费", "通勤费", "其他"}
    ]

    rows = []
    for _, row in df.iloc[header_row + 2:].iterrows():
        serial = clean_value(row.iloc[serial_col]) if df.shape[1] > serial_col else ""
        company = clean_value(row.iloc[company_col]) if df.shape[1] > company_col else ""
        if not is_number_like(serial) or not company or "鍚堣" in str(company):
            continue
        rows.append(row)

    if not rows:
        return {"record": None, "display_record": None}

    def total(col: int) -> float:
        return round(sum(safe_float(row.iloc[col]) for row in rows if col < len(row)), 2)

    income = total(income_col)
    salary = total(salary_col) if salary_col >= 0 else 0
    recruitment_fee = total(recruitment_col) if recruitment_col >= 0 else 0
    other_expense = round(sum(total(col) for col in other_cols), 2)
    net_profit = total(net_profit_col)

    record = {
        "month": month,
        "total_income": income,
        "salary_expense": salary,
        "recruitment_fee_expense": recruitment_fee,
        "other_expense": other_expense,
        "net_profit": net_profit,
        "remark": f"{sheet_name}自动汇总，企业明细 {len(rows)} 条",
    }
    display = {
        "涓氬姟绫诲瀷": "鏈堝害鍒╂鼎鏍哥畻",
        "来源工作表": sheet_name,
        "鏈堜唤": month,
        "企业数": len(rows),
        "总收入": income,
        "宸ヨ祫鏀嚭": salary,
        "杩旇垂鏀嚭": recruitment_fee,
        "鍏朵粬鏀嚭": other_expense,
        "鍑€鍒╂鼎": net_profit,
    }
    return {"record": record, "display_record": display}


def extract_receivable_records(df, sheet_name: str) -> dict[str, Any]:
    header_row = None
    for idx, row in df.head(8).iterrows():
        text = "".join(str(clean_value(value)) for value in row)
        if "企业名称" in text and "劳务费金额" in text:
            header_row = idx
            break
    if header_row is None:
        return {"records": [], "display_records": []}

    headers = [str(clean_value(value)) for value in df.iloc[header_row].tolist()]
    header_map = {normalize_header(name): idx for idx, name in enumerate(headers) if name}
    serial_col = header_map.get("搴忓彿", 1)
    collector_col = header_map.get("追款人", 3)
    company_col = header_map.get("浼佷笟鍚嶇О", 4)
    month_col = header_map.get("鏈堜唤", 5)
    amount_col = header_map.get("劳务费金额", 6)
    remark_col = header_map.get("澶囨敞", 7)

    records: list[dict[str, Any]] = []
    display_records: list[dict[str, Any]] = []
    for row_idx, row in df.iloc[header_row + 1:].iterrows():
        serial = clean_value(row.iloc[serial_col]) if df.shape[1] > serial_col else ""
        collector = clean_value(row.iloc[collector_col]) if df.shape[1] > collector_col else ""
        company = clean_value(row.iloc[company_col]) if df.shape[1] > company_col else ""
        month_text = clean_value(row.iloc[month_col]) if df.shape[1] > month_col else ""
        amount = clean_value(row.iloc[amount_col]) if df.shape[1] > amount_col else ""
        remark = clean_value(row.iloc[remark_col]) if df.shape[1] > remark_col else ""
        if not is_number_like(serial) or not company or "鍚堣" in str(company) or safe_float(amount) == 0:
            continue
        expected_date = expected_date_from_month(month_text)
        record = {
            "company_name": company,
            "expected_date": expected_date,
            "actual_date": "",
            "amount": amount,
            "payment_method": "直接给付",
            "acceptance_due_date": "",
            "status": "待回款",
            "overdue_days": 0,
            "remark": f"{sheet_name}；追款人：{collector or '-'}；月份：{month_text or '-'}；{remark or ''}",
            "_origin": {"sheet": sheet_name, "row": int(row_idx) + 1},
        }
        records.append(record)
        display_records.append({
            "业务类型": "应收账款",
            "来源工作表": sheet_name,
            "原始行": int(row_idx) + 1,
            "企业名称": company,
            "月份": month_text or "-",
            "金额": amount,
            "追款人": collector or "-",
            "状态": "待回款",
            "备注": remark or "-",
        })
    return {"records": records, "display_records": display_records}


def month_from_sheet(sheet_name: str) -> str:
    match = re.search(r"(\d{1,2})\s*月", str(sheet_name))
    if not match:
        return ""
    month = int(match.group(1))
    if not 1 <= month <= 12:
        return ""
    return f"2026-{month:02d}"


def expected_date_from_month(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"(\d{1,2})", text)
    if not match:
        return "2026-12-31"
    month = max(1, min(12, int(match.group(1))))
    return f"2026-{month:02d}-28"


def is_number_like(value: Any) -> bool:
    try:
        if value in (None, ""):
            return False
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def extract_journal_flows(df, sheet_name: str) -> dict[str, Any]:
    headers = [str(h).strip() for h in df.columns]
    normalized = [normalize_header(h) for h in headers]
    groups: list[dict[str, int | str]] = []

    date_names = {"日期", "date"}
    income_amount_names = {"收入金额", "收入", "收款金额", "incomeamount", "income"}
    income_method_names = {"收入方式", "收款方式", "income_method", "incomemethod"}
    expense_amount_names = {"支出金额", "支出", "付款金额", "expenseamount", "expense"}
    expense_method_names = {"支出方式", "付款方式", "expense_method", "expensemethod"}
    description_names = {"摘要说明", "摘要", "说明", "description", "remark"}
    remark_names = {"备注", "备注信息", "remark"}

    def first_named(values: list[str], names: set[str], default: int = -1) -> int:
        for pos, value in enumerate(values):
            if value in names:
                return pos
        return default

    for idx, header in enumerate(normalized):
        if header not in date_names:
            continue
        next_date = next((pos for pos in range(idx + 1, len(normalized)) if normalized[pos] in date_names), len(normalized))
        window = normalized[idx:next_date]
        income_amount = first_named(window, income_amount_names)
        if 0 <= income_amount <= 4:
            income_method = first_named(window, income_method_names)
            income_description = first_named(window, description_names)
            groups.append({
                "kind": "收入",
                "date": idx,
                "amount": idx + income_amount,
                "method": idx + income_method if 0 <= income_method <= 4 else -1,
                "description": idx + income_description if 0 <= income_description <= 4 else -1,
            })
        expense_amount = first_named(window, expense_amount_names)
        if 0 <= expense_amount <= 4:
            expense_method = first_named(window, expense_method_names)
            expense_description = first_named(window, description_names)
            groups.append({
                "kind": "支出",
                "date": idx,
                "amount": idx + expense_amount,
                "method": idx + expense_method if 0 <= expense_method <= 4 else -1,
                "description": idx + expense_description if 0 <= expense_description <= 4 else -1,
            })

    if not groups:
        return {"records": [], "display_records": [], "groups": []}

    remark_columns = [i for i, h in enumerate(normalized) if h in remark_names]
    records: list[dict[str, Any]] = []
    display_records: list[dict[str, Any]] = []
    for row_idx, row in df.iterrows():
        for group in groups:
            amount = clean_value(row.iloc[int(group["amount"])]) if int(group["amount"]) >= 0 and int(group["amount"]) < len(row) else ""
            if amount in ("", None, "nan", 0, 0.0):
                continue
            amount_num = safe_float(amount)
            # 负数自动翻转收支方向：收入列中的负数 → 支出，支出列中的负数 → 收入
            flipped = amount_num < 0
            if flipped:
                is_income = group["kind"] != "收入"
                amount = abs(amount_num)
            else:
                is_income = group["kind"] == "收入"
            date_value = clean_value(row.iloc[int(group["date"])]) if int(group["date"]) >= 0 else ""
            method = clean_value(row.iloc[int(group["method"])]) if int(group["method"]) >= 0 and int(group["method"]) < len(row) else ""
            description = clean_value(row.iloc[int(group["description"])]) if int(group["description"]) >= 0 and int(group["description"]) < len(row) else ""
            remark = "；".join(str(clean_value(row.iloc[i])) for i in remark_columns if clean_value(row.iloc[i]) not in ("", "nan"))
            actual_direction = "收入" if is_income else "支出"
            record = {
                "date": date_value,
                "income_amount": amount if is_income else 0,
                "income_method": method if is_income else "",
                "expense_amount": amount if not is_income else 0,
                "expense_method": method if not is_income else "",
                "description": description,
                "source_type": "手动录入",
                "source_id": "",
                "remark": remark,
                "_origin": {"sheet": sheet_name, "row": int(row_idx) + 1, "section": group["kind"], "flipped": flipped},
            }
            records.append(record)
            display_records.append({
                "业务类型": "收支流水",
                "来源工作表": sheet_name,
                "原始行": int(row_idx) + 1,
                "收支": actual_direction,
                "日期": date_value,
                "金额": amount,
                "方式": method or "-",
                "摘要": description or "-",
                "备注": remark or "-",
            })
    return {"records": records, "display_records": display_records, "groups": groups}


def first_index(values: list[str], needles: list[str], default: int = -1) -> int:
    for needle in needles:
        if needle in values:
            return values.index(needle)
    return default


def clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return value if not isinstance(value, str) else text


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return ""
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    return value


def journal_to_finance(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finance = []
    for record in records:
        income = record.get("income_amount") or 0
        expense = record.get("expense_amount") or 0
        is_income = safe_float(income) > 0
        finance.append({
            "date": record.get("date"),
            "type": "收入" if is_income else "支出",
            "category": infer_finance_category(str(record.get("description") or record.get("remark") or ""), is_income),
            "amount": income if is_income else expense,
            "company_name": "",
            "remark": record.get("remark") or record.get("description") or "",
            "_origin": record.get("_origin", {}),
        })
    return finance


def infer_finance_category(text: str, is_income: bool) -> str:
    if is_income:
        return "企业回款" if any(k in text for k in ["回款", "货款", "收款", "收入"]) else "其他"
    if any(k in text for k in ["工资", "薪"]):
        return "工资发放"
    if any(k in text for k in ["返费", "招聘", "代招"]):
        return "代招返费"
    if any(k in text for k in ["办公", "房租", "水电", "差旅", "费用", "报销"]):
        return "办公费用"
    return "其他"


def safe_float(value: Any) -> float:
    try:
        import math
        num = float(value or 0)
        return 0.0 if math.isnan(num) else num
    except (TypeError, ValueError):
        return 0.0


def make_target(module: str, module_label: str, sheet_name: str, records: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    blocked = {issue["row_index"] for issue in issues if issue.get("severity") == "blocker"}
    display = records_to_display(module, module_label, sheet_name, records)
    return {
        "module": module,
        "module_label": module_label,
        "sheet_name": sheet_name,
        "selected": True,
        "rows_total": len(records),
        "rows_ready": max(0, len(records) - len(blocked)),
        "rows_blocked": len(blocked),
        "records": records,
        "display_records": display,
        "issues": tag_issues(sheet_name, issues),
    }


def records_to_display(module: str, module_label: str, sheet_name: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if module == "journal":
        display = []
        for idx, record in enumerate(records):
            origin = record.get("_origin", {}) if isinstance(record.get("_origin"), dict) else {}
            base = {
                "业务类型": "收支流水",
                "来源工作表": sheet_name,
                "原始行": origin.get("row", idx + 1),
                "日期": record.get("date") or "-",
                "摘要": record.get("description") or "-",
                "备注": record.get("remark") or "-",
            }
            income = safe_float(record.get("income_amount"))
            expense = safe_float(record.get("expense_amount"))
            if income:
                display.append({
                    **base,
                    "收支": "收入",
                    "金额": record.get("income_amount"),
                    "方式": record.get("income_method") or "-",
                })
            if expense:
                display.append({
                    **base,
                    "收支": "支出",
                    "金额": record.get("expense_amount"),
                    "方式": record.get("expense_method") or "-",
                })
        return display

    module_def = get_module(module)
    labels = {field.field_key: field.field_label for field in module_def.fields} if module_def else {}
    display = []
    for idx, record in enumerate(records):
        row = {"业务类型": module_label, "来源工作表": sheet_name, "原始行": record.get("_origin", {}).get("row", idx + 1)}
        for key, value in record.items():
            if key.startswith("_") or value in ("", None, "待填写", "寰呭～鍐?"):
                continue
            row[labels.get(key, key)] = value
        display.append(row)
    return display


def tag_issues(sheet_name: str, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged = []
    for issue in issues:
        copy = dict(issue)
        copy["sheet_name"] = sheet_name
        tagged.append(copy)
    return tagged


def workbook_fingerprint(sheet_reports: list[dict[str, Any]]) -> str:
    raw = json.dumps(sheet_reports, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "." in text and text.rsplit(".", 1)[1].isdigit():
        text = text.rsplit(".", 1)[0]
    for token in (" ", "　", "\t", "\n", "\r", "（", "）", "(", ")", ":", "："):
        text = text.replace(token, "")
    return text


def rule_based_analysis(df, sheet_name: str, header_row: int, allow_weak: bool = False) -> dict[str, Any]:
    registry = get_registry()
    headers = [str(h).strip() for h in df.columns]
    candidates: dict[str, dict[str, Any]] = {}

    for module_key, module in registry.items():
        score = 0
        mappings: list[dict[str, Any]] = []
        used_fields: set[str] = set()
        sheet_bonus = 4 if module.module_label in sheet_name or module_key in sheet_name.lower() else 0

        for col_idx, header in enumerate(headers):
            normalized = normalize_header(header)
            best_field = None
            best_score = 0

            for field in module.fields:
                names = [field.field_key, field.field_label] + field.aliases
                normalized_names = [normalize_header(name) for name in names]
                field_score = 0
                if normalized in normalized_names:
                    field_score = 4
                elif any(normalized and (normalized in name or name in normalized) for name in normalized_names):
                    field_score = 2
                if field.field_key in module.identifying_fields and field_score:
                    field_score += 2
                if field_score > best_score:
                    best_score = field_score
                    best_field = field

            if best_field and best_field.field_key not in used_fields:
                used_fields.add(best_field.field_key)
                score += best_score
                mappings.append({
                    "column_index": col_idx,
                    "original_header": header,
                    "mapped_field": best_field.field_key,
                    "field_label": best_field.field_label,
                    "confidence": 1.0,
                    "reasoning": "甯哥敤瀛楁瑙勫垯鑷姩璇嗗埆",
                })

        score += sheet_bonus
        candidates[module_key] = {"score": score, "mappings": mappings, "module": module}

    best_key, best = max(candidates.items(), key=lambda item: item[1]["score"])
    threshold = 4 if allow_weak else 10
    if best["score"] < threshold or not best["mappings"]:
        return {
            "classification": {"module": "", "module_label": "", "confidence": 0, "reasoning": "规则未命中"},
            "header_row_index": header_row,
            "field_mappings": [],
            "preview_rows": [],
            "total_rows": 0,
            "_debug": {"source": "rules", "score": best["score"], "candidates": {k: v["score"] for k, v in candidates.items()}},
        }

    module = best["module"]
    mapped_by_field = {m["mapped_field"]: m for m in best["mappings"]}
    field_mappings = []
    for field in module.fields:
        mapping = mapped_by_field.get(field.field_key)
        if mapping:
            field_mappings.append(mapping)
        else:
            field_mappings.append({
                "column_index": -1,
                "original_header": "",
                "mapped_field": field.field_key,
                "field_label": field.field_label,
                "confidence": 0,
                "reasoning": "表格未提供，按默认或空值处理",
            })

    records = _convert_all(df, field_mappings, module)
    return {
        "classification": {
            "module": best_key,
            "module_label": module.module_label,
            "confidence": 1.0,
            "reasoning": "甯哥敤瀛楁瑙勫垯鑷姩鏁寸悊",
        },
        "header_row_index": header_row,
        "field_mappings": field_mappings,
        "preview_rows": records,
        "total_rows": len(records),
        "_debug": {
            "source": "rules",
            "score": best["score"],
            "candidates": {k: v["score"] for k, v in candidates.items()},
        },
    }


def apply_module_defaults(module_key: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    module = get_module(module_key)
    if not module:
        return records
    defaults = {
        field.field_key: field.default_value
        for field in module.fields
        if field.default_value not in (None, "")
    }
    if not defaults:
        return records
    cleaned = []
    for record in records:
        row = dict(record)
        for key, value in defaults.items():
            if row.get(key) in (None, "", "待填写", "寰呭～鍐?"):
                row[key] = value
        cleaned.append(row)
    return cleaned


def analysis_from_cache(cached: dict[str, Any], df, header_row: int) -> dict[str, Any]:
    module_key = cached["module"]
    module = get_module(module_key)
    mappings = cached.get("field_mappings", [])
    if module_key == "journal":
        journal = extract_journal_flows(df, "甯哥敤鏍煎紡")
        rows = journal["records"] if journal["records"] else _convert_all(df, mappings, module)
    else:
        rows = _convert_all(df, mappings, module)
    return {
        "classification": {
            "module": module_key,
            "module_label": module.module_label if module else module_key,
            "confidence": 1.0,
            "reasoning": "甯哥敤鏍煎紡鑷姩鏁寸悊",
        },
        "header_row_index": cached.get("header_row_index", header_row),
        "field_mappings": mappings,
        "preview_rows": rows,
        "total_rows": len(rows),
    }


def validate_records(module_key: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    module = get_module(module_key)
    if not module:
        return []

    issues: list[dict[str, Any]] = []
    required = [field for field in module.fields if field.required]
    labels = {field.field_key: field.field_label for field in module.fields}

    for index, record in enumerate(records):
        for field in required:
            value = record.get(field.field_key)
            if value in (None, "", "待填写", "寰呭～鍐?"):
                issues.append({
                    "row_index": index,
                    "field": field.field_key,
                    "field_label": field.field_label,
                    "severity": "blocker",
                    "message": f"{field.field_label}涓虹┖",
                    "original_value": value,
                    "suggested_value": field.default_value,
                })

        if module_key == "journal":
            parsed_date = parse_record_date(record.get("date"))
            if not parsed_date:
                issues.append({
                    "row_index": index,
                    "field": "date",
                    "field_label": "鏃ユ湡",
                    "severity": "blocker",
                    "message": "鏃ユ湡鏍煎紡涓嶆纭紝鏃犳硶淇濆瓨涓烘棩璁拌处",
                    "original_value": record.get("date"),
                    "suggested_value": None,
                })
            income = safe_float(record.get("income_amount"))
            expense = safe_float(record.get("expense_amount"))
            if income == 0 and expense == 0:
                issues.append({
                    "row_index": index,
                    "field": "amount",
                    "field_label": "閲戦",
                    "severity": "blocker",
                    "message": "收入金额和支出金额不能同时为空",
                    "original_value": "",
                    "suggested_value": None,
                })

        for key, value in record.items():
            if value in ("待填写", "寰呭～鍐?") and key not in [f.field_key for f in required]:
                issues.append({
                    "row_index": index,
                    "field": key,
                    "field_label": labels.get(key, key),
                    "severity": "warning",
                    "message": f"{labels.get(key, key)}未在表格中找到，已保留为空",
                    "original_value": value,
                    "suggested_value": None,
                })

    return issues


def parse_record_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def commit_batch(batch_id: str) -> dict[str, Any]:
    batch = get_batch(batch_id)
    if not batch:
        raise FileNotFoundError("导入批次不存在")
    if batch.get("status") == "committed":
        return batch

    created = []
    commit_errors = []
    if batch.get("targets"):
        for target in batch["targets"]:
            if target.get("selected") is False:
                continue
            blocked_rows = {issue["row_index"] for issue in target.get("issues", []) if issue.get("severity") == "blocker"}
            ready_records = [
                clean_import_record(record)
                for index, record in enumerate(target.get("records", []))
                if index not in blocked_rows
            ]
            try:
                created.extend(create_business_records(target["module"], ready_records, source={"type": "import", "batch_id": batch_id}))
            except Exception as exc:
                commit_errors.append({"module": target.get("module"), "row_index": None, "message": str(exc)})
    else:
        blocked_rows = {issue["row_index"] for issue in batch.get("issues", []) if issue.get("severity") == "blocker"}
        ready_records = [
            clean_import_record(record)
            for index, record in enumerate(batch.get("records", []))
            if index not in blocked_rows
        ]

        try:
            created.extend(create_business_records(batch["module"], ready_records, source={"type": "import", "batch_id": batch_id}))
        except Exception as exc:
            commit_errors.append({"module": batch.get("module"), "row_index": None, "message": str(exc)})

    batch["status"] = "committed" if created else "failed"
    batch["committed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    batch["committed_rows"] = len(created)
    batch["commit_errors"] = commit_errors
    save_batch(batch)
    remember_successful_format(batch)
    append_import_history(batch, len(created))
    log_action(batch["module"], "导入", f"保存导入批次 {batch_id}，成功 {len(created)} 行")
    return batch


def clean_import_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if v not in ("待填写", "寰呭～鍐?", None, "")}


def remember_successful_format(batch: dict[str, Any]) -> None:
    cache = load_cache()
    fingerprint = batch.get("fingerprint")
    if not fingerprint:
        return
    existing = cache.get(fingerprint, {})
    cache[fingerprint] = {
        "module": batch["module"],
        "module_label": batch["module_label"],
        "field_mappings": batch.get("_debug", {}).get("field_mappings", []),
        "header_row_index": batch.get("header_row_index", 0),
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success_count": int(existing.get("success_count", 0)) + 1,
    }
    save_cache(cache)


def append_import_history(batch: dict[str, Any], imported_rows: int) -> None:
    history_file = Path(settings.DATA_DIR) / "_import_history.json"
    history: list[dict[str, Any]] = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    history.append({
        "import_id": batch["batch_id"],
        "filename": batch["filename"],
        "module": batch["module"],
        "sheet": batch["sheet_name"],
        "total_rows": batch["rows_total"],
        "imported_rows": imported_rows,
        "error_rows": batch["rows_blocked"],
        "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
