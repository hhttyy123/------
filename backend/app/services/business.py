"""Business services for linkage, dashboard, warnings, and profit."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.registry.loader import get_module, get_registry
from app.services.repository import JsonRepository, now_str, repo

SENSITIVE_DELETE_MODULES = {
    "payroll", "recruitment_fee", "accounts_receivable", "finance",
    "journal", "profit", "approval", "audit_log",
}

APPROVAL_MODULES = {"payroll", "recruitment_fee"}
LARGE_FINANCE_THRESHOLD = 10000


def field_labels(module_key: str) -> dict[str, str]:
    module = get_module(module_key)
    if not module:
        return {}
    return {field.field_key: field.field_label for field in module.fields}


def module_payloads() -> list[dict[str, Any]]:
    payloads = []
    for key, module in get_registry().items():
        payloads.append({
            "module": key,
            "module_label": module.module_label,
            "description": module.description,
            "fields": [field.to_dict() for field in module.fields],
            "record_count": len(repo.list_records(key)),
        })
    return payloads


def clear_test_records() -> dict[str, Any]:
    cleared_modules = []
    for module_key in get_registry().keys():
        repo.write_records(module_key, [])
        cleared_modules.append(module_key)

    data_dir = Path(settings.DATA_DIR)
    for filename, empty_value in {
        "_import_history.json": "[]",
        "_fingerprint_cache.json": "{}",
    }.items():
        path = data_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(empty_value, encoding="utf-8")

    batch_dir = data_dir / "_import_batches"
    cleared_batches = 0
    if batch_dir.exists():
        for path in batch_dir.glob("*.json"):
            path.unlink()
            cleared_batches += 1

    datasets_dir = data_dir / "datasets"
    cleared_datasets = 0
    if datasets_dir.exists():
        for path in datasets_dir.glob("*.json"):
            path.unlink()
            cleared_datasets += 1
    datasets_index = data_dir / "_datasets_index.json"
    if datasets_index.exists():
        datasets_index.write_text("[]", encoding="utf-8")

    return {
        "ok": True,
        "cleared_modules": cleared_modules,
        "cleared_batches": cleared_batches,
        "cleared_datasets": cleared_datasets,
    }


def schema_payload(module_key: str) -> dict[str, Any] | None:
    module = get_module(module_key)
    if not module:
        return None
    return {
        "module": module.module_key,
        "module_label": module.module_label,
        "description": module.description,
        "fields": [field.to_dict() for field in module.fields],
        "identifying_fields": module.identifying_fields,
    }


def searchable_text(record: dict[str, Any]) -> str:
    return " ".join(str(value) for value in record.values() if not isinstance(value, (dict, list)))


def is_valid_journal_record(record: dict[str, Any]) -> bool:
    if not parse_date(record.get("date")):
        return False
    return amount_value(record.get("income_amount")) > 0 or amount_value(record.get("expense_amount")) > 0


def list_module_records(module: str, search: str = "", limit: int = 200) -> list[dict[str, Any]]:
    records = repo.list_records(module)
    if module == "journal":
        records = [r for r in records if is_valid_journal_record(r)]
    if search:
        needle = search.strip().lower()
        records = [r for r in records if needle in searchable_text(r).lower()]
    return records[:limit]


def create_business_record(module: str, data: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    record = repo.create_record(module, data, source=source)
    if not (module == "finance" and (source or {}).get("type") == "import"):
        apply_linkages(module, record)
    maybe_create_approval(module, record)
    log_action(module, "新增", f"新增{schema_payload(module)['module_label'] if schema_payload(module) else module}记录 #{record['id']}")
    return record


def create_business_records(module: str, rows: list[dict[str, Any]], source: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    created = repo.create_many(module, rows, source=source)
    for record in created:
        if not (module == "finance" and (source or {}).get("type") == "import"):
            apply_linkages(module, record)
        maybe_create_approval(module, record)
    if created:
        label = schema_payload(module)["module_label"] if schema_payload(module) else module
        log_action(module, "导入", f"批量导入{label} {len(created)} 条")
    return created


def update_business_record(module: str, record_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    record = repo.update_record(module, record_id, patch)
    if record:
        apply_linkages(module, record)
        log_action(module, "编辑", f"编辑{module}记录 #{record_id}")
    return record


def delete_business_record(module: str, record_id: int) -> bool:
    if module in SENSITIVE_DELETE_MODULES:
        return False
    ok = repo.delete_record(module, record_id)
    if ok:
        log_action(module, "删除", f"删除{module}记录 #{record_id}", sensitive=True)
    return ok


def amount_value(value: Any) -> float:
    try:
        if value in (None, "", "待填写"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def month_of(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(record.get(key) or "")
        if len(value) >= 7:
            return value[:7]
    return date.today().strftime("%Y-%m")


def apply_linkages(module: str, record: dict[str, Any]) -> None:
    if module == "payroll" and str(record.get("status") or "") == "已发放":
        create_journal_from_source(
            source_module=module,
            source_id=record["id"],
            entry_date=record.get("issued_at") or f"{record.get('month', '')}-01",
            expense=amount_value(record.get("net_pay")),
            source_type="工资发放",
            description=f"{record.get('employee_name', '')} 工资发放",
        )
    elif module == "recruitment_fee":
        create_journal_from_source(
            source_module=module,
            source_id=record["id"],
            entry_date=record.get("date") or record.get("created_at", "")[:10],
            expense=amount_value(record.get("amount")),
            source_type="返费支出",
            description=f"{record.get('company_name', '')} 代招返费",
        )
    elif module == "accounts_receivable" and str(record.get("status") or "") == "已到账":
        create_journal_from_source(
            source_module=module,
            source_id=record["id"],
            entry_date=record.get("actual_date") or record.get("expected_date"),
            income=amount_value(record.get("amount")),
            source_type="回款到账",
            description=f"{record.get('company_name', '')} 回款到账",
        )
    elif module == "finance":
        record_type = str(record.get("type") or "")
        create_journal_from_source(
            source_module=module,
            source_id=record["id"],
            entry_date=record.get("date") or record.get("created_at", "")[:10],
            income=amount_value(record.get("amount")) if record_type == "收入" else 0,
            expense=amount_value(record.get("amount")) if record_type == "支出" else 0,
            source_type="财务记录",
            description=str(record.get("remark") or record.get("category") or "财务记录"),
        )


def create_journal_from_source(
    source_module: str,
    source_id: int,
    entry_date: Any,
    source_type: str,
    description: str,
    income: float = 0,
    expense: float = 0,
) -> None:
    existing = repo.list_records("journal")
    for item in existing:
        source = item.get("_source") or {}
        if source.get("source_module") == source_module and source.get("source_id") == source_id:
            return
    repo.create_record("journal", {
        "date": str(entry_date or date.today().isoformat())[:10],
        "income_amount": income,
        "income_method": "",
        "expense_amount": expense,
        "expense_method": "",
        "description": description,
        "source_type": source_type,
        "source_id": source_id,
        "sync_status": "已同步",
    }, source={"type": "system", "source_module": source_module, "source_id": source_id})


def maybe_create_approval(module: str, record: dict[str, Any]) -> None:
    needs_approval = module in APPROVAL_MODULES
    if module == "finance" and amount_value(record.get("amount")) >= LARGE_FINANCE_THRESHOLD:
        needs_approval = True
    if not needs_approval:
        return
    repo.create_record("approval", {
        "module": module,
        "data_id": str(record["id"]),
        "submitter": "默认操作人",
        "reviewer": "",
        "approver": "",
        "status": "待审核",
        "submit_time": now_str(),
        "review_time": "",
        "approve_time": "",
        "review_comment": "",
        "approve_comment": "",
    }, source={"type": "system", "source_module": module, "source_id": record["id"]})


def log_action(module: str, action: str, description: str, sensitive: bool = False) -> None:
    if module == "audit_log":
        return
    repo.create_record("audit_log", {
        "operator": "默认操作人",
        "operation_time": now_str(),
        "module": module,
        "action_type": action,
        "description": description,
        "ip_address": "",
        "is_sensitive": sensitive,
    }, source={"type": "system"})


def calculate_profit(month: str | None = None, repository: JsonRepository | None = None) -> dict[str, Any]:
    repository = repository or repo
    target_month = month or date.today().strftime("%Y-%m")
    receivables = repository.list_records("accounts_receivable")
    payroll = repository.list_records("payroll")
    fees = repository.list_records("recruitment_fee")
    finance = repository.list_records("finance")

    total_income = sum(amount_value(r.get("amount")) for r in receivables if str(r.get("status")) == "已到账" and month_of(r, "actual_date", "expected_date") == target_month)
    salary_expense = sum(amount_value(r.get("net_pay")) for r in payroll if str(r.get("status")) == "已发放" and month_of(r, "issued_at", "month") == target_month)
    fee_expense = sum(amount_value(r.get("amount")) for r in fees if month_of(r, "date", "created_at") == target_month)
    other_expense = sum(amount_value(r.get("amount")) for r in finance if str(r.get("type")) == "支出" and month_of(r, "date", "created_at") == target_month)
    net_profit = total_income - salary_expense - fee_expense - other_expense

    return {
        "month": target_month,
        "total_income": round(total_income, 2),
        "salary_expense": round(salary_expense, 2),
        "recruitment_fee_expense": round(fee_expense, 2),
        "other_expense": round(other_expense, 2),
        "net_profit": round(net_profit, 2),
    }


def save_profit(month: str | None = None) -> dict[str, Any]:
    payload = calculate_profit(month)
    existing = repo.list_records("profit")
    for record in existing:
        if record.get("month") == payload["month"]:
            return repo.update_record("profit", int(record["id"]), payload) or record
    return repo.create_record("profit", payload, source={"type": "system"})


def generate_warnings() -> list[dict[str, Any]]:
    today = date.today()
    warnings: list[dict[str, Any]] = []

    for record in repo.list_records("accounts_receivable"):
        expected = parse_date(record.get("expected_date"))
        if expected and expected < today and str(record.get("status") or "") != "已到账":
            warnings.append({
                "type": "回款逾期",
                "module": "accounts_receivable",
                "record_id": record.get("id"),
                "title": f"{record.get('company_name', '企业')} 回款逾期",
                "message": f"逾期 {(today - expected).days} 天，金额 {record.get('amount', 0)}",
                "severity": "warning",
            })

    for employee in repo.list_records("employee"):
        entry = parse_date(employee.get("entry_date"))
        if not entry or (today - entry).days <= 20:
            continue
        employee_name = employee.get("name") or employee.get("employee_name")
        has_contract = any(c.get("employee_name") == employee_name for c in repo.list_records("contract"))
        if not has_contract:
            warnings.append({
                "type": "未签合同",
                "module": "employee",
                "record_id": employee.get("id"),
                "title": f"{employee_name or '员工'} 入职未签合同",
                "message": f"入职已超过 {(today - entry).days} 天",
                "severity": "warning",
            })

    for contract in repo.list_records("contract"):
        end = parse_date(contract.get("end_date"))
        if end and 0 <= (end - today).days <= 15:
            warnings.append({
                "type": "合同到期",
                "module": "contract",
                "record_id": contract.get("id"),
                "title": f"{contract.get('employee_name', '员工')} 合同即将到期",
                "message": f"还有 {(end - today).days} 天到期",
                "severity": "info",
            })

    return warnings


def dashboard_summary() -> dict[str, Any]:
    current_month = date.today().strftime("%Y-%m")
    warnings = generate_warnings()
    profit = calculate_profit(current_month)
    receivable_income = sum(
        amount_value(r.get("amount"))
        for r in repo.list_records("accounts_receivable")
        if str(r.get("status") or "") == "已到账" and month_of(r, "actual_date", "expected_date") == current_month
    )
    finance_income = sum(
        amount_value(r.get("amount"))
        for r in repo.list_records("finance")
        if str(r.get("type") or "") == "收入"
        and str(r.get("category") or "") == "企业回款"
        and month_of(r, "date", "created_at") == current_month
    )
    operating_income = receivable_income or finance_income or profit["total_income"]
    employees = repo.list_records("employee")
    active_employees = len([e for e in employees if str(e.get("status") or "在职") == "在职"])
    approvals = len([a for a in repo.list_records("approval") if str(a.get("status") or "") in {"待审核", "待审批"}])
    return {
        "active_employees": active_employees,
        "month_receivable": round(operating_income, 2),
        "month_salary": profit["salary_expense"],
        "month_profit": profit["net_profit"],
        "warning_count": len(warnings),
        "approval_count": approvals,
        "current_month": current_month,
    }


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
