"""PostgreSQL company and position business services."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Company, Position


def normalize_company_name(value: str) -> str:
    return re.sub(r"[\s（）()·\-]", "", value).lower()


def list_companies(session: Session, search: str = "", status: str | None = None, page: int = 1, page_size: int = 100) -> dict[str, Any]:
    conditions = [Company.deleted_at.is_(None)]
    if search.strip():
        keyword = f"%{search.strip()}%"
        conditions.append(or_(Company.name.ilike(keyword), Company.contact_person.ilike(keyword), Company.contact_phone.ilike(keyword)))
    if status:
        conditions.append(Company.cooperation_status == status)
    total = session.scalar(select(func.count()).select_from(Company).where(*conditions)) or 0
    rows = session.scalars(select(Company).where(*conditions).order_by(Company.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"rows": [serialize_company(row) for row in rows], "total": total, "page": page, "page_size": page_size}


def create_company(session: Session, data: dict[str, Any], source_import_row_id: int | None = None) -> dict[str, Any]:
    normalized_name = normalize_company_name(data["name"])
    if session.scalar(select(Company.id).where(Company.normalized_name == normalized_name, Company.deleted_at.is_(None))):
        raise ValueError("企业名称已存在")
    now = datetime.now(timezone.utc)
    row = Company(
        name=data["name"].strip(), normalized_name=normalized_name,
        contact_person=data.get("contact_person") or None, contact_phone=data.get("contact_phone") or None,
        address=data.get("address") or None, business_license_no=data.get("business_license_no") or None,
        cooperation_status=data.get("cooperation_status") or "active",
        cooperation_start_date=data.get("cooperation_start_date"), cooperation_end_date=data.get("cooperation_end_date"),
        default_receivable_days=data.get("default_receivable_days"), remark=data.get("remark") or None,
        source_import_row_id=source_import_row_id, version_no=1, created_by=None, updated_by=None,
        created_at=now, updated_at=now, deleted_at=None,
    )
    session.add(row); session.flush()
    return serialize_company(row)


def update_company(session: Session, company_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    row = session.get(Company, company_id)
    if row is None or row.deleted_at is not None: return None
    if "name" in data:
        normalized = normalize_company_name(data["name"])
        duplicate = session.scalar(select(Company.id).where(Company.normalized_name == normalized, Company.id != company_id, Company.deleted_at.is_(None)))
        if duplicate: raise ValueError("企业名称已存在")
        row.name, row.normalized_name = data["name"].strip(), normalized
    for field in ("contact_person", "contact_phone", "address", "business_license_no", "cooperation_status", "cooperation_start_date", "cooperation_end_date", "default_receivable_days", "remark"):
        if field in data: setattr(row, field, data[field])
    row.version_no += 1; row.updated_at = datetime.now(timezone.utc)
    session.commit(); session.refresh(row)
    return serialize_company(row)


def delete_company(session: Session, company_id: int) -> bool:
    row = session.get(Company, company_id)
    if row is None or row.deleted_at is not None: return False
    row.deleted_at = datetime.now(timezone.utc); row.cooperation_status = "terminated"; row.version_no += 1
    session.commit(); return True


def list_positions(session: Session, company_id: int | None = None, page: int = 1, page_size: int = 100) -> dict[str, Any]:
    conditions = [Position.deleted_at.is_(None)]
    if company_id: conditions.append(Position.company_id == company_id)
    total = session.scalar(select(func.count()).select_from(Position).where(*conditions)) or 0
    rows = session.scalars(select(Position).where(*conditions).order_by(Position.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    company_names = dict(session.execute(select(Company.id, Company.name)).all())
    return {"rows": [serialize_position(row, company_names.get(row.company_id, "")) for row in rows], "total": total, "page": page, "page_size": page_size}


def create_position(session: Session, data: dict[str, Any]) -> dict[str, Any]:
    if session.get(Company, data["company_id"]) is None: raise ValueError("所属企业不存在")
    now = datetime.now(timezone.utc)
    row = Position(company_id=data["company_id"], name=data["name"].strip(), description=data.get("description") or None,
        daily_rate=Decimal(str(data["daily_rate"])) if data.get("daily_rate") is not None else None,
        required_count=data.get("required_count"), status=data.get("status") or "recruiting", created_at=now, updated_at=now, deleted_at=None)
    session.add(row); session.commit(); session.refresh(row)
    company_name = session.get(Company, row.company_id).name
    return serialize_position(row, company_name)


def update_position(session: Session, position_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    row = session.get(Position, position_id)
    if row is None or row.deleted_at is not None: return None
    for field in ("company_id", "name", "description", "required_count", "status"):
        if field in data: setattr(row, field, data[field])
    if "daily_rate" in data: row.daily_rate = Decimal(str(data["daily_rate"])) if data["daily_rate"] is not None else None
    row.updated_at = datetime.now(timezone.utc); session.commit(); session.refresh(row)
    return serialize_position(row, session.get(Company, row.company_id).name)


def delete_position(session: Session, position_id: int) -> bool:
    row = session.get(Position, position_id)
    if row is None or row.deleted_at is not None: return False
    row.deleted_at = datetime.now(timezone.utc); row.status = "closed"; session.commit(); return True


def export_companies_excel(session: Session) -> BytesIO:
    rows = list_companies(session, page_size=100000)["rows"]
    wb = Workbook(); ws = wb.active; ws.title = "企业"
    ws.append(["企业名称", "联系人", "联系电话", "地址", "营业执照号", "合作状态", "合作开始", "合作结束", "默认回款天数", "备注"])
    status_labels = {"active": "正常合作", "paused": "暂停合作", "terminated": "终止合作"}
    for row in rows: ws.append([row["name"], row["contact_person"], row["contact_phone"], row["address"], row["business_license_no"], status_labels.get(row["cooperation_status"], row["cooperation_status"]), row["cooperation_start_date"], row["cooperation_end_date"], row["default_receivable_days"], row["remark"]])
    stream = BytesIO(); wb.save(stream); stream.seek(0); return stream


def serialize_company(row: Company) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "contact_person": row.contact_person, "contact_phone": row.contact_phone, "address": row.address, "business_license_no": row.business_license_no, "cooperation_status": row.cooperation_status, "cooperation_start_date": row.cooperation_start_date.isoformat() if row.cooperation_start_date else None, "cooperation_end_date": row.cooperation_end_date.isoformat() if row.cooperation_end_date else None, "default_receivable_days": row.default_receivable_days, "remark": row.remark, "version_no": row.version_no}


def serialize_position(row: Position, company_name: str) -> dict[str, Any]:
    return {"id": row.id, "company_id": row.company_id, "company_name": company_name, "name": row.name, "description": row.description, "daily_rate": float(row.daily_rate) if row.daily_rate is not None else None, "required_count": row.required_count, "status": row.status}
