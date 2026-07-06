"""PostgreSQL-backed staging and commit flow for journal imports."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil import parser as date_parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CashTransaction, Company, Contract, Employee, EmploymentRecord, ImportBatch, ImportRow, Position, StoredFile, TransactionLink
from app.services.company_db import create_company, normalize_company_name
from app.services.employee_db import create_employee, normalize_id, validate_employee_data
from app.services.excel_reader import detect_header_row, read_sheet_full
from app.services.import_batch import extract_journal_flows, json_safe


def stage_journal_import(
    session: Session,
    upload_id: str,
    sheet_name: str,
    header_row: int | None = None,
) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError("上传文件不存在")

    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    extracted = extract_journal_flows(dataframe, sheet_name)
    if not extracted["records"]:
        raise ValueError("未识别到可导入的收入或支出明细")

    now = datetime.now(timezone.utc)
    storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(
            original_name=storage_key,
            storage_key=storage_key,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=file_path.stat().st_size,
            sha256=_file_sha256(file_path),
            uploaded_by=None,
            created_at=now,
        )
        session.add(stored_file)
        session.flush()

    batch = ImportBatch(
        file_id=stored_file.id,
        module="journal",
        status="ready",
        mapping_version="journal-parallel-v1",
        total_rows=0,
        ready_rows=0,
        warning_rows=0,
        blocked_rows=0,
        error_message=None,
        created_by=None,
        committed_by=None,
        created_at=now,
        committed_at=None,
    )
    session.add(batch)
    session.flush()

    raw_rows = _raw_rows_by_index(dataframe)
    for record in extracted["records"]:
        normalized, issues = normalize_journal_record(record, sheet_name)
        origin = record.get("_origin", {})
        data_index = max(int(origin.get("row", 1)) - 1, 0)
        excel_row = data_index + actual_header + 2
        status = "blocked" if any(issue["severity"] == "blocker" for issue in issues) else "ready"
        fingerprint = _record_fingerprint(normalized) if status == "ready" else None
        session.add(ImportRow(
            batch_id=batch.id,
            sheet_name=sheet_name,
            source_row=excel_row,
            source_region=str(origin.get("section") or "main"),
            raw_data=raw_rows.get(data_index, {}),
            normalized_data=normalized,
            record_fingerprint=fingerprint,
            status=status,
            issues=issues,
            target_table=None,
            target_record_id=None,
            created_at=now,
        ))
        batch.total_rows += 1
        if status == "ready":
            batch.ready_rows += 1
        else:
            batch.blocked_rows += 1

    if batch.ready_rows == 0:
        batch.status = "failed"
        batch.error_message = "没有可提交的有效记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)


def get_staged_batch(session: Session, batch_id: int, include_rows: bool = True) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise LookupError("导入批次不存在")
    payload: dict[str, Any] = {
        "batch_id": batch.id,
        "module": batch.module,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "ready_rows": batch.ready_rows,
        "warning_rows": batch.warning_rows,
        "blocked_rows": batch.blocked_rows,
        "created_at": batch.created_at.isoformat(),
        "committed_at": batch.committed_at.isoformat() if batch.committed_at else None,
    }
    if include_rows:
        rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id).order_by(ImportRow.id)).all()
        payload["rows"] = [{
            "id": row.id,
            "sheet_name": row.sheet_name,
            "source_row": row.source_row,
            "source_region": row.source_region,
            "normalized_data": row.normalized_data,
            "status": row.status,
            "issues": row.issues,
        } for row in rows]
    return payload


def commit_staged_journal(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise LookupError("导入批次不存在")
    if batch.module != "journal":
        raise ValueError("当前只支持提交日记账批次")
    if batch.status != "ready":
        raise ValueError(f"批次状态 {batch.status} 不允许提交")

    rows = session.scalars(select(ImportRow).where(
        ImportRow.batch_id == batch_id,
        ImportRow.status == "ready",
    ).order_by(ImportRow.id)).all()
    now = datetime.now(timezone.utc)
    imported = 0
    try:
        batch.status = "committing"
        for row in rows:
            data = row.normalized_data or {}
            transaction = CashTransaction(
                transaction_date=date.fromisoformat(str(data["transaction_date"])),
                ledger_type=str(data["ledger_type"]),
                direction=str(data["direction"]),
                category="other",
                amount=Decimal(str(data["amount"])),
                payment_method=str(data.get("payment_method") or "") or None,
                company_id=None,
                employee_id=None,
                summary=str(data.get("summary") or "") or None,
                status="confirmed",
                reversal_of_id=None,
                source_import_row_id=row.id,
                created_by=None,
                created_at=now,
                updated_at=now,
            )
            session.add(transaction)
            session.flush()
            session.add(TransactionLink(
                transaction_id=transaction.id,
                source_type="import_row",
                source_id=row.id,
                link_role="origin",
                created_at=now,
            ))
            row.status = "committed"
            row.target_table = "cash_transactions"
            row.target_record_id = transaction.id
            imported += 1
        batch.status = "committed"
        batch.committed_at = now
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}


def stage_company_import(session: Session, upload_id: str, sheet_name: str, header_row: int | None = None) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists(): raise FileNotFoundError("上传文件不存在")
    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    aliases = {
        "name": {"企业名称", "企业", "公司名称", "单位名称", "name", "company"},
        "contact_person": {"联系人", "对接人", "负责人", "contact_person", "contact"},
        "contact_phone": {"联系电话", "手机号", "电话", "contact_phone", "phone"},
        "address": {"地址", "企业地址", "公司地址", "address"},
        "business_license_no": {"营业执照号", "营业执照", "执照号", "business_license"},
        "cooperation_status": {"合作状态", "状态", "cooperation_status", "status"},
        "cooperation_start_date": {"合作起始日期", "合作开始", "start_date"},
        "cooperation_end_date": {"合作截止日期", "合作结束", "end_date"},
        "default_receivable_days": {"默认回款天数", "回款期限", "账期", "receivable_days"},
        "remark": {"备注", "说明", "remark"},
    }
    columns = {str(column).strip(): column for column in dataframe.columns}
    mapping = {field: next((columns[name] for name in names if name in columns), None) for field, names in aliases.items()}
    if mapping["name"] is None: raise ValueError("未找到企业名称列")
    now = datetime.now(timezone.utc); storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()
    batch = ImportBatch(file_id=stored_file.id, module="company", status="ready", mapping_version="company-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()
    for index, source in dataframe.iterrows():
        raw = {str(column): json_safe(source[column]) for column in dataframe.columns}
        data = {field: json_safe(source[column]) if column is not None else "" for field, column in mapping.items()}
        data = normalize_company_import_data(data)
        issues = []
        if not data["name"]: issues.append({"field": "name", "severity": "blocker", "message": "企业名称不能为空"})
        elif session.scalar(select(Company.id).where(Company.normalized_name == normalize_company_name(data["name"]), Company.deleted_at.is_(None))): issues.append({"field": "name", "severity": "blocker", "message": "企业已存在"})
        status = "blocked" if issues else "ready"
        session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=int(index) + actual_header + 2, source_region="main", raw_data=raw, normalized_data=data, record_fingerprint=_record_fingerprint({"name": normalize_company_name(data["name"])}), status=status, issues=issues, target_table=None, target_record_id=None, created_at=now))
        batch.total_rows += 1; batch.ready_rows += int(status == "ready"); batch.blocked_rows += int(status == "blocked")
    session.commit(); return get_staged_batch(session, batch.id, include_rows=False)


def commit_staged_companies(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None: raise LookupError("导入批次不存在")
    if batch.module != "company" or batch.status != "ready": raise ValueError("批次不允许提交")
    rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "ready").order_by(ImportRow.id)).all()
    imported = 0
    try:
        for row in rows:
            company_data = dict(row.normalized_data or {})
            for field in ("cooperation_start_date", "cooperation_end_date"):
                company_data[field] = _parse_date(company_data.get(field))
            # Check if soft-deleted duplicate exists, reactivate it
            normalized = normalize_company_name(company_data["name"])
            existing = session.scalar(select(Company).where(Company.normalized_name == normalized, Company.deleted_at.isnot(None)))
            if existing:
                existing.deleted_at = None
                existing.cooperation_status = company_data.get("cooperation_status") or existing.cooperation_status
                existing.updated_at = datetime.now(timezone.utc)
                existing.source_import_row_id = row.id
                session.flush()
                row.status = "committed"; row.target_table = "companies"; row.target_record_id = existing.id; imported += 1
            else:
                company = create_company(session, company_data, source_import_row_id=row.id)
                row.status = "committed"; row.target_table = "companies"; row.target_record_id = company["id"]; imported += 1
        batch.status = "committed"; batch.committed_at = datetime.now(timezone.utc); session.commit()
    except Exception: session.rollback(); raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}


def stage_employee_import(session: Session, upload_id: str, sheet_name: str, header_row: int | None = None) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError("上传文件不存在")
    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    aliases = {
        "name": {"姓名", "员工姓名", "人员姓名", "name"},
        "id_card_number": {"身份证号", "身份证号码", "证件号码", "id_card_number", "id_card"},
        "phone": {"手机号", "手机号码", "联系电话", "电话", "phone"},
        "gender": {"性别", "gender"},
        "address": {"地址", "家庭地址", "现住址", "address"},
        "entry_date": {"入职日期", "入职时间", "上班日期", "entry_date"},
        "company_name": {"企业名称", "企业", "公司名称", "单位名称", "company_name", "company"},
        "position_name": {"岗位名称", "岗位", "职位", "工种", "position_name", "position"},
    }
    columns = {str(column).strip(): column for column in dataframe.columns}
    mapping = {field: next((columns[name] for name in names if name in columns), None) for field, names in aliases.items()}
    required = ("name", "id_card_number", "phone", "gender", "entry_date", "company_name")
    missing = [field for field in required if mapping[field] is None]
    if missing:
        raise ValueError("缺少必要列：" + "、".join(missing))

    now = datetime.now(timezone.utc)
    storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()
    batch = ImportBatch(file_id=stored_file.id, module="employee", status="ready", mapping_version="employee-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()
    seen_ids: set[str] = set()
    companies = {normalize_company_name(c.name): c for c in session.scalars(select(Company).where(Company.deleted_at.is_(None))).all()}
    positions = session.scalars(select(Position).where(Position.deleted_at.is_(None))).all()
    for index, source in dataframe.iterrows():
        raw = {str(column): json_safe(source[column]) for column in dataframe.columns}
        values = {field: json_safe(source[column]) if column is not None else "" for field, column in mapping.items()}
        if not any(str(value or "").strip() for value in values.values()):
            continue
        gender_raw = str(values.get("gender") or "").strip().lower()
        gender = {"男": "male", "男性": "male", "m": "male", "male": "male", "女": "female", "女性": "female", "f": "female", "female": "female"}.get(gender_raw, gender_raw)
        company = companies.get(normalize_company_name(str(values.get("company_name") or "")))
        position_name = str(values.get("position_name") or "").strip()
        position = next((p for p in positions if company and p.company_id == company.id and p.name.strip() == position_name), None) if position_name else None
        entry_date = _parse_date(values.get("entry_date"))
        ident = normalize_id(str(values.get("id_card_number") or ""))
        data = {"name": str(values.get("name") or "").strip(), "id_card_number": ident, "phone": re.sub(r"\D", "", str(values.get("phone") or "")), "gender": gender, "address": str(values.get("address") or "").strip(), "entry_date": entry_date.isoformat() if entry_date else None, "company_id": company.id if company else None, "company_name": str(values.get("company_name") or "").strip(), "position_id": position.id if position else None, "position_name": position_name}
        issues = [{**issue, "severity": "blocker"} for issue in validate_employee_data(data)]
        digest = hashlib.sha256(ident.encode()).hexdigest() if ident else ""
        if digest and (digest in seen_ids or session.scalar(select(Employee.id).where(Employee.id_card_hash == digest, Employee.deleted_at.is_(None)))):
            issues.append({"field": "id_card_number", "severity": "blocker", "message": "身份证号重复"})
        if position_name and position is None:
            issues.append({"field": "position_name", "severity": "blocker", "message": "未在该企业下匹配到岗位"})
        seen_ids.add(digest)
        status = "blocked" if issues else "ready"
        session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=int(index) + actual_header + 2, source_region="main", raw_data=raw, normalized_data=data, record_fingerprint=digest or None, status=status, issues=issues, target_table=None, target_record_id=None, created_at=now))
        batch.total_rows += 1; batch.ready_rows += int(status == "ready"); batch.blocked_rows += int(status == "blocked")
    if batch.ready_rows == 0:
        batch.status = "failed"; batch.error_message = "没有可提交的有效人员记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)


def commit_staged_employees(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None: raise LookupError("导入批次不存在")
    if batch.module != "employee" or batch.status != "ready": raise ValueError("批次不允许提交")
    rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "ready").order_by(ImportRow.id)).all()
    imported = 0
    try:
        for row in rows:
            data = dict(row.normalized_data or {})
            data["entry_date"] = _parse_date(data.get("entry_date"))
            # Reactivate soft-deleted employee if exists
            ident = normalize_id(str(data.get("id_card_number") or ""))
            digest = hashlib.sha256(ident.encode()).hexdigest() if ident else ""
            existing = session.scalar(select(Employee).where(Employee.id_card_hash == digest, Employee.deleted_at.isnot(None))) if digest else None
            if existing:
                existing.deleted_at = None; existing.status = "active"; existing.updated_at = datetime.now(timezone.utc)
                existing.source_import_row_id = row.id
                # Also reactivate employment record
                er = session.scalar(select(EmploymentRecord).where(EmploymentRecord.employee_id == existing.id).order_by(EmploymentRecord.id.desc()))
                if er:
                    er.status = "active"; er.leave_date = None; er.company_id = data.get("company_id") or er.company_id
                    er.position_id = data.get("position_id") or er.position_id
                    er.entry_date = data["entry_date"] or er.entry_date
                session.flush()
                row.status = "committed"; row.target_table = "employees"; row.target_record_id = existing.id; imported += 1
            else:
                employee = create_employee(session, data, source_import_row_id=row.id)
                row.status = "committed"; row.target_table = "employees"; row.target_record_id = employee["id"]; imported += 1
        batch.status = "committed"; batch.committed_at = datetime.now(timezone.utc); session.commit()
    except Exception:
        session.rollback(); raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}


# ---- Position staging ----

def stage_position_import(session: Session, upload_id: str, sheet_name: str, header_row: int | None = None) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists(): raise FileNotFoundError("上传文件不存在")
    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    aliases = {
        "company_name": {"所属企业", "企业", "企业名称", "公司", "company_name", "company"},
        "name": {"岗位名称", "岗位", "职位", "工种", "name", "position", "post"},
        "daily_rate": {"日单价", "单价", "日工资", "daily_rate", "rate"},
        "required_count": {"需求人数", "人数", "required_count", "count", "headcount"},
        "status": {"岗位状态", "状态", "status"},
        "description": {"描述", "岗位描述", "说明", "description", "remark"},
    }
    columns = {str(c).strip(): c for c in dataframe.columns}
    mapping = {f: next((columns[n] for n in names if n in columns), None) for f, names in aliases.items()}
    if not mapping["company_name"] or not mapping["name"]: raise ValueError("缺少必要列：所属企业、岗位名称")
    now = datetime.now(timezone.utc); storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()
    batch = ImportBatch(file_id=stored_file.id, module="position", status="ready", mapping_version="position-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()
    companies = {normalize_company_name(c.name): c for c in session.scalars(select(Company).where(Company.deleted_at.is_(None))).all()}
    for index, source in dataframe.iterrows():
        raw = {str(c): json_safe(source[c]) for c in dataframe.columns}
        vals = {f: json_safe(source[c]) if c is not None else "" for f, c in mapping.items()}
        if not str(vals.get("name") or "").strip(): continue
        company = companies.get(normalize_company_name(str(vals.get("company_name") or "")))
        status_map = {"招聘中": "recruiting", "已满": "filled", "已关闭": "closed"}
        data = {"company_name": str(vals["company_name"] or "").strip(), "company_id": company.id if company else None, "name": str(vals["name"] or "").strip(), "daily_rate": str(vals.get("daily_rate") or "").strip(), "required_count": str(vals.get("required_count") or "").strip(), "status": status_map.get(str(vals.get("status") or "").strip(), "recruiting"), "description": str(vals.get("description") or "").strip()}
        issues = []
        if not company: issues.append({"field": "company_name", "severity": "blocker", "message": "未匹配到企业"})
        if company and session.scalar(select(Position.id).where(Position.company_id == company.id, Position.name == data["name"], Position.deleted_at.is_(None))): issues.append({"field": "name", "severity": "blocker", "message": "该企业下已有同名岗位"})
        status = "blocked" if issues else "ready"
        session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=int(index) + actual_header + 2, source_region="main", raw_data=raw, normalized_data=data, record_fingerprint=_record_fingerprint({"company_id": data.get("company_id"), "name": data["name"]}), status=status, issues=issues, target_table=None, target_record_id=None, created_at=now))
        batch.total_rows += 1; batch.ready_rows += int(status == "ready"); batch.blocked_rows += int(status == "blocked")
    if batch.ready_rows == 0: batch.status = "failed"; batch.error_message = "没有可提交的有效岗位记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)


def commit_staged_positions(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None: raise LookupError("导入批次不存在")
    if batch.module != "position" or batch.status != "ready": raise ValueError("批次不允许提交")
    rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "ready").order_by(ImportRow.id)).all()
    imported = 0
    try:
        from app.services.company_db import create_position as cp
        for row in rows:
            data = dict(row.normalized_data or {})
            # Reactivate soft-deleted position if exists
            existing = session.scalar(select(Position).where(Position.company_id == data["company_id"], Position.name == data["name"], Position.deleted_at.isnot(None)))
            if existing:
                existing.deleted_at = None; existing.status = data.get("status", "recruiting"); existing.updated_at = datetime.now(timezone.utc)
                session.flush()
                row.status = "committed"; row.target_table = "positions"; row.target_record_id = existing.id; imported += 1
            else:
                pos = cp(session, {"company_id": data["company_id"], "name": data["name"], "daily_rate": data.get("daily_rate"), "required_count": data.get("required_count"), "status": data.get("status", "recruiting"), "description": data.get("description")})
                row.status = "committed"; row.target_table = "positions"; row.target_record_id = pos["id"]; imported += 1
        batch.status = "committed"; batch.committed_at = datetime.now(timezone.utc); session.commit()
    except Exception: session.rollback(); raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}


def normalize_company_import_data(data: dict[str, Any]) -> dict[str, Any]:
    status_map = {"正常合作": "active", "合作中": "active", "暂停合作": "paused", "暂停": "paused", "终止合作": "terminated", "终止": "terminated"}
    return {
        "name": str(data.get("name") or "").strip(), "contact_person": str(data.get("contact_person") or "").strip(),
        "contact_phone": str(data.get("contact_phone") or "").strip(), "address": str(data.get("address") or "").strip(),
        "business_license_no": str(data.get("business_license_no") or "").strip(),
        "cooperation_status": status_map.get(str(data.get("cooperation_status") or "").strip(), "active"),
        "cooperation_start_date": (_parse_date(data.get("cooperation_start_date")).isoformat() if _parse_date(data.get("cooperation_start_date")) else None),
        "cooperation_end_date": (_parse_date(data.get("cooperation_end_date")).isoformat() if _parse_date(data.get("cooperation_end_date")) else None),
        "default_receivable_days": int(float(data["default_receivable_days"])) if str(data.get("default_receivable_days") or "").strip() else None,
        "remark": str(data.get("remark") or "").strip(),
    }


def normalize_journal_record(record: dict[str, Any], sheet_name: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    is_income = bool(record.get("income_amount"))
    raw_amount = record.get("income_amount") if is_income else record.get("expense_amount")
    raw_method = record.get("income_method") if is_income else record.get("expense_method")
    try:
        amount = Decimal(str(raw_amount)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        amount = Decimal("0")
        issues.append({"field": "amount", "severity": "blocker", "message": "金额必须大于 0"})

    parsed_date = _parse_date(record.get("date"))
    if parsed_date is None:
        issues.append({"field": "transaction_date", "severity": "blocker", "message": "日期无法识别"})

    ledger_type = "cash" if "现金" in sheet_name else "bank" if "银行" in sheet_name else "cash"
    return {
        "transaction_date": parsed_date.isoformat() if parsed_date else "",
        "ledger_type": ledger_type,
        "direction": "income" if is_income else "expense",
        "amount": str(amount),
        "payment_method": str(raw_method or ""),
        "summary": str(record.get("description") or ""),
        "remark": str(record.get("remark") or ""),
    }, issues


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date_parser.parse(str(value), yearfirst=True).date()
    except (ValueError, TypeError, OverflowError):
        return None


def _raw_rows_by_index(dataframe) -> dict[int, dict[str, Any]]:
    columns = [str(column) for column in dataframe.columns]
    return {
        int(index): json_safe({"columns": columns, "values": list(row.values)})
        for index, row in dataframe.iterrows()
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_fingerprint(data: dict[str, Any]) -> str:
    parts = [str(data.get(key, "")) for key in ("transaction_date", "ledger_type", "direction", "amount", "payment_method", "summary")]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


# ---- Attendance staging ----

def stage_attendance_import(session: Session, upload_id: str, sheet_name: str, header_row: int | None = None) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists(): raise FileNotFoundError("上传文件不存在")
    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    aliases = {
        "employee_name": {"员工姓名", "姓名", "员工", "employee_name", "employee", "name"},
        "work_date": {"出勤日期", "日期", "考勤日期", "work_date", "date", "attendance_date"},
        "status": {"出勤状态", "状态", "考勤状态", "attendance_status", "status"},
        "hours": {"工时", "工时(h)", "出勤工时", "hours", "work_hours"},
        "deduction_amount": {"扣款", "扣款金额", "deduction_amount", "deduction"},
        "remark": {"备注", "说明", "remark"},
    }
    columns = {str(c).strip(): c for c in dataframe.columns}
    mapping = {f: next((columns[n] for n in names if n in columns), None) for f, names in aliases.items()}
    if not mapping["employee_name"]: raise ValueError("缺少必要列：员工姓名")
    now = datetime.now(timezone.utc); storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()
    batch = ImportBatch(file_id=stored_file.id, module="attendance", status="ready", mapping_version="attendance-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()
    employees = {e.name.strip(): e for e in session.scalars(select(Employee).where(Employee.deleted_at.is_(None))).all()}
    status_map = {"正常出勤": "normal", "出勤": "normal", "正常": "normal", "迟到": "late", "旷工": "absent", "请假": "leave", "休假": "leave", "normal": "normal", "late": "late", "absent": "absent", "leave": "leave"}
    for index, source in dataframe.iterrows():
        raw = {str(c): json_safe(source[c]) for c in dataframe.columns}
        vals = {f: json_safe(source[c]) if c is not None else "" for f, c in mapping.items()}
        emp_name = str(vals.get("employee_name") or "").strip()
        if not emp_name: continue
        emp = employees.get(emp_name)
        wd = _parse_date(vals.get("work_date"))
        st = status_map.get(str(vals.get("status") or "").strip().lower(), "normal")
        hrs = safe_float(vals.get("hours") or 8)
        ded = safe_float(vals.get("deduction_amount") or 0)
        data = {"employee_name": emp_name, "employee_id": emp.id if emp else None,
                "work_date": wd.isoformat() if wd else None, "status": st,
                "hours": str(hrs), "deduction_amount": str(ded),
                "remark": str(vals.get("remark") or "").strip()}
        issues = []
        if not emp: issues.append({"field": "employee_name", "severity": "blocker", "message": "未匹配到人员"})
        if not wd: issues.append({"field": "work_date", "severity": "blocker", "message": "日期无效"})
        status = "blocked" if issues else "ready"
        session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=int(index) + actual_header + 2, source_region="main", raw_data=raw, normalized_data=data, record_fingerprint=_record_fingerprint({"emp": emp_name, "date": str(wd)}), status=status, issues=issues, target_table=None, target_record_id=None, created_at=now))
        batch.total_rows += 1; batch.ready_rows += int(status == "ready"); batch.blocked_rows += int(status == "blocked")
    if batch.ready_rows == 0: batch.status = "failed"; batch.error_message = "没有可提交的有效考勤记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)


def commit_staged_attendance(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None: raise LookupError("导入批次不存在")
    if batch.module != "attendance" or batch.status != "ready": raise ValueError("批次不允许提交")
    rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "ready").order_by(ImportRow.id)).all()
    imported = 0
    try:
        for row in rows:
            data = dict(row.normalized_data or {})
            from sqlalchemy import text as stext
            employment_id = session.execute(stext("SELECT id FROM employment_records WHERE employee_id=:eid AND status='active' ORDER BY id DESC LIMIT 1"), {"eid": data["employee_id"]}).scalar()
            if not employment_id:
                raise ValueError(f"人员 {data.get('employee_name','')} 没有有效在职记录")
            session.execute(stext("""INSERT INTO attendance_records(employment_id,work_date,status,hours,deduction_amount,remark,created_at,updated_at)
                VALUES(:eid,:wd,:st,:hrs,:ded,:rmk,:now,:now) ON CONFLICT (employment_id,work_date) DO UPDATE SET status=EXCLUDED.status,hours=EXCLUDED.hours,deduction_amount=EXCLUDED.deduction_amount,remark=EXCLUDED.remark,updated_at=EXCLUDED.updated_at"""),
                {"eid": employment_id, "wd": data["work_date"], "st": data["status"], "hrs": float(data["hours"] or 0), "ded": float(data["deduction_amount"] or 0), "rmk": data.get("remark"), "now": datetime.now(timezone.utc)})
            row.status = "committed"; row.target_table = "attendance_records"; imported += 1
        batch.status = "committed"; batch.committed_at = datetime.now(timezone.utc); session.commit()
    except Exception: session.rollback(); raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}


def safe_float(value: Any) -> float:
    try:
        import math
        num = float(value or 0)
        return 0.0 if math.isnan(num) else num
    except (TypeError, ValueError):
        return 0.0


# ---- Journal workbook import (all sheets at once) ----

def stage_journal_workbook_import(session: Session, upload_id: str) -> dict[str, Any]:
    """Import all sheets from a journal workbook into one batch."""
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists(): raise FileNotFoundError("上传文件不存在")
    now = datetime.now(timezone.utc)
    storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()

    batch = ImportBatch(file_id=stored_file.id, module="journal", status="ready", mapping_version="journal-workbook-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()

    # Read all sheet names
    xls = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
    sheet_names = [s for s in xls.keys() if xls[s].shape[0] > 2 and xls[s].shape[1] > 3]
    if not sheet_names: raise ValueError("未找到可导入的工作表")

    for sheet_name in sheet_names:
        header_row = detect_header_row(file_path, sheet_name)
        dataframe = read_sheet_full(file_path, sheet_name, header_row=header_row, fill_merged=False)
        extracted = extract_journal_flows(dataframe, sheet_name)
        if not extracted["records"]: continue
        raw_rows = {}
        for idx, row in dataframe.iterrows():
            raw_rows[int(idx)] = json_safe({"columns": [str(c) for c in dataframe.columns], "values": [json_safe(v) for v in row.values]})
        for record in extracted["records"]:
            normalized, issues = normalize_journal_record(record, sheet_name)
            origin = record.get("_origin", {})
            data_index = max(int(origin.get("row", 1)) - 1, 0)
            excel_row = data_index + header_row + 2
            st = "blocked" if any(i["severity"] == "blocker" for i in issues) else "ready"
            fingerprint = _record_fingerprint(normalized) if st == "ready" else None
            session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=excel_row, source_region=str(origin.get("section") or "main"), raw_data=raw_rows.get(data_index, {}), normalized_data=normalized, record_fingerprint=fingerprint, status=st, issues=issues, target_table=None, target_record_id=None, created_at=now))
            batch.total_rows += 1
            if st == "ready": batch.ready_rows += 1
            else: batch.blocked_rows += 1

    if batch.ready_rows == 0: batch.status = "failed"; batch.error_message = "没有可提交的有效记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)


# ---- Contract staging ----

def stage_contract_import(session: Session, upload_id: str, sheet_name: str, header_row: int | None = None) -> dict[str, Any]:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists(): raise FileNotFoundError("上传文件不存在")
    actual_header = header_row if header_row is not None else detect_header_row(file_path, sheet_name)
    dataframe = read_sheet_full(file_path, sheet_name, header_row=actual_header, fill_merged=False)
    aliases = {
        "employee_name": {"员工姓名", "姓名", "员工", "employee_name", "employee", "name"},
        "contract_no": {"合同编号", "合同号", "contract_no"},
        "sign_date": {"签订日期", "签署日期", "sign_date"},
        "start_date": {"合同起始日期", "开始日期", "起始日期", "start_date", "合同开始"},
        "end_date": {"合同截止日期", "截止日期", "到期日期", "end_date", "合同截止"},
        "contract_type": {"合同类型", "type", "contract_type"},
        "remark": {"备注", "remark"},
    }
    columns = {str(c).strip(): c for c in dataframe.columns}
    mapping = {f: next((columns[n] for n in names if n in columns), None) for f, names in aliases.items()}
    if not mapping["employee_name"]: raise ValueError("缺少必要列：员工姓名")
    now = datetime.now(timezone.utc); storage_key = file_path.name
    stored_file = session.scalar(select(StoredFile).where(StoredFile.storage_key == storage_key))
    if stored_file is None:
        stored_file = StoredFile(original_name=storage_key, storage_key=storage_key, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size_bytes=file_path.stat().st_size, sha256=_file_sha256(file_path), uploaded_by=None, created_at=now)
        session.add(stored_file); session.flush()
    batch = ImportBatch(file_id=stored_file.id, module="contract", status="ready", mapping_version="contract-v1", total_rows=0, ready_rows=0, warning_rows=0, blocked_rows=0, error_message=None, created_by=None, committed_by=None, created_at=now, committed_at=None)
    session.add(batch); session.flush()
    employees = {e.name.strip(): e for e in session.scalars(select(Employee).where(Employee.deleted_at.is_(None))).all()}
    for index, source in dataframe.iterrows():
        raw = {str(c): json_safe(source[c]) for c in dataframe.columns}
        vals = {f: json_safe(source[c]) if c is not None else "" for f, c in mapping.items()}
        emp_name = str(vals.get("employee_name") or "").strip()
        if not emp_name: continue
        emp = employees.get(emp_name)
        sd = _parse_date(vals.get("sign_date")); st = _parse_date(vals.get("start_date")); ed = _parse_date(vals.get("end_date"))
        data = {"employee_name": emp_name, "employee_id": emp.id if emp else None, "contract_no": str(vals.get("contract_no") or "").strip(), "contract_type": str(vals.get("contract_type") or "初始签订").strip() or "初始签订", "sign_date": sd.isoformat() if sd else None, "start_date": st.isoformat() if st else None, "end_date": ed.isoformat() if ed else None, "remark": str(vals.get("remark") or "").strip()}
        issues = []
        if not emp: issues.append({"field": "employee_name", "severity": "blocker", "message": "未匹配到人员"})
        if not st: issues.append({"field": "start_date", "severity": "blocker", "message": "起始日期无效"})
        if not ed: issues.append({"field": "end_date", "severity": "blocker", "message": "截止日期无效"})
        status = "blocked" if issues else "ready"
        session.add(ImportRow(batch_id=batch.id, sheet_name=sheet_name, source_row=int(index) + actual_header + 2, source_region="main", raw_data=raw, normalized_data=data, record_fingerprint=_record_fingerprint({"emp": emp_name, "no": data["contract_no"]}), status=status, issues=issues, target_table=None, target_record_id=None, created_at=now))
        batch.total_rows += 1; batch.ready_rows += int(status == "ready"); batch.blocked_rows += int(status == "blocked")
    if batch.ready_rows == 0: batch.status = "failed"; batch.error_message = "没有可提交的有效合同记录"
    session.commit()
    return get_staged_batch(session, batch.id, include_rows=False)

def commit_staged_contracts(session: Session, batch_id: int) -> dict[str, Any]:
    batch = session.get(ImportBatch, batch_id)
    if batch is None: raise LookupError("导入批次不存在")
    if batch.module != "contract" or batch.status != "ready": raise ValueError("批次不允许提交")
    rows = session.scalars(select(ImportRow).where(ImportRow.batch_id == batch_id, ImportRow.status == "ready").order_by(ImportRow.id)).all()
    imported = 0
    try:
        from app.services.employee_db import create_contract as cc
        for row in rows:
            data = dict(row.normalized_data or {})
            cc(session, {"employee_id": data["employee_id"], "contract_type": data.get("contract_type", "employee"), "contract_no": data.get("contract_no"), "sign_date": _parse_date(data.get("sign_date")), "start_date": _parse_date(data["start_date"]), "end_date": _parse_date(data["end_date"]), "remark": data.get("remark")})
            row.status = "committed"; row.target_table = "contracts"; imported += 1
        batch.status = "committed"; batch.committed_at = datetime.now(timezone.utc); session.commit()
    except Exception: session.rollback(); raise
    return {"batch_id": batch_id, "status": "committed", "imported_rows": imported}
