"""PostgreSQL journal CRUD, filtering, and Excel export."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CashTransaction


def list_journal_transactions(
    session: Session,
    *,
    direction: str | None = None,
    ledger_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    conditions = [CashTransaction.status != "voided"]
    if direction:
        conditions.append(CashTransaction.direction == direction)
    if ledger_type:
        conditions.append(CashTransaction.ledger_type == ledger_type)
    if date_from:
        conditions.append(CashTransaction.transaction_date >= date_from)
    if date_to:
        conditions.append(CashTransaction.transaction_date <= date_to)
    if search.strip():
        keyword = f"%{search.strip()}%"
        conditions.append(or_(
            CashTransaction.summary.ilike(keyword),
            CashTransaction.payment_method.ilike(keyword),
            CashTransaction.category.ilike(keyword),
        ))

    total = session.scalar(select(func.count()).select_from(CashTransaction).where(*conditions)) or 0
    rows = session.scalars(
        select(CashTransaction)
        .where(*conditions)
        .order_by(CashTransaction.transaction_date.asc(), CashTransaction.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    income_total, expense_total = session.execute(
        select(
            func.coalesce(func.sum(CashTransaction.amount).filter(CashTransaction.direction == "income"), 0),
            func.coalesce(func.sum(CashTransaction.amount).filter(CashTransaction.direction == "expense"), 0),
        ).where(*conditions)
    ).one()
    return {
        "rows": [serialize_transaction(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "income_total": float(income_total),
        "expense_total": float(expense_total),
        "net_flow": float(income_total - expense_total),
    }


def create_journal_transaction(session: Session, data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    row = CashTransaction(
        transaction_date=data["transaction_date"],
        ledger_type=data["ledger_type"],
        direction=data["direction"],
        category=data.get("category") or "other",
        amount=Decimal(str(data["amount"])),
        payment_method=data.get("payment_method") or None,
        company_id=data.get("company_id"),
        employee_id=data.get("employee_id"),
        summary=data.get("summary") or None,
        status="confirmed",
        reversal_of_id=None,
        source_import_row_id=None,
        created_by=None,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return serialize_transaction(row)


def update_journal_transaction(session: Session, transaction_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    row = session.get(CashTransaction, transaction_id)
    if row is None or row.status == "voided":
        return None
    for field in ("transaction_date", "ledger_type", "direction", "category", "payment_method", "company_id", "employee_id", "summary"):
        if field in data:
            setattr(row, field, data[field] or None if field in {"payment_method", "summary"} else data[field])
    if "amount" in data:
        row.amount = Decimal(str(data["amount"]))
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return serialize_transaction(row)


def void_journal_transaction(session: Session, transaction_id: int) -> bool:
    row = session.get(CashTransaction, transaction_id)
    if row is None or row.status == "voided":
        return False
    row.status = "voided"
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
    return True


def export_journal_excel(session: Session, **filters: Any) -> BytesIO:
    result = list_journal_transactions(session, page=1, page_size=100000, **filters)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "日记账"
    sheet.append(["日期", "账簿", "收支", "类别", "金额", "方式", "摘要", "来源"])
    for row in result["rows"]:
        sheet.append([
            row["transaction_date"],
            "现金日记账" if row["ledger_type"] == "cash" else "银行日记账",
            "收入" if row["direction"] == "income" else "支出",
            row["category"],
            row["amount"],
            row["payment_method"] or "",
            row["summary"] or "",
            "Excel导入" if row["source_import_row_id"] else "手工录入",
        ])
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def serialize_transaction(row: CashTransaction) -> dict[str, Any]:
    return {
        "id": row.id,
        "transaction_date": row.transaction_date.isoformat(),
        "ledger_type": row.ledger_type,
        "direction": row.direction,
        "category": row.category,
        "amount": float(row.amount),
        "payment_method": row.payment_method,
        "company_id": row.company_id,
        "employee_id": row.employee_id,
        "summary": row.summary,
        "status": row.status,
        "source_import_row_id": row.source_import_row_id,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
