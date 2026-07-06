"""按日期范围批量清空模块数据"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()

CLEAR_CONFIG: dict[str, dict] = {
    "journal":    {"table": "cash_transactions",    "date_col": "transaction_date", "date_type": "date", "action": "void"},
    "attendance": {"table": "attendance_records",   "date_col": "work_date",        "date_type": "date", "action": "delete"},
    "salary":     {"table": "payroll_batches",      "date_col": "salary_month",     "date_type": "date", "action": "void"},
    "rebate":     {"table": "recruitment_rebates",  "date_col": "rebate_date",      "date_type": "date", "action": "void"},
    "invoice":    {"table": "invoices",             "date_col": "invoice_date",     "date_type": "date", "action": "void"},
    "payment":    {"table": "payments",             "date_col": "payment_date",     "date_type": "date", "action": "void"},
    "company":    {"table": "companies",            "date_col": "created_at",       "date_type": "timestamptz", "action": "soft_delete"},
    "employee":   {"table": "employees",            "date_col": "created_at",       "date_type": "timestamptz", "action": "soft_delete"},
    "position":   {"table": "positions",            "date_col": "created_at",       "date_type": "timestamptz", "action": "soft_delete"},
    "contract":   {"table": "contracts",            "date_col": "created_at",       "date_type": "timestamptz", "action": "terminate"},
    "profit":     {"table": "profit_periods",       "date_col": "period_start",     "date_type": "date",        "action": "delete"},
}


class ClearRequest(BaseModel):
    module: str = Field(description="模块标识")
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def check_range(self) -> "ClearRequest":
        if self.date_from > self.date_to:
            raise ValueError("开始日期不能晚于结束日期")
        return self


@router.post("/clear")
def clear_records(req: ClearRequest, db: Session = Depends(get_db)):
    config = CLEAR_CONFIG.get(req.module)
    if config is None:
        raise HTTPException(400, f"不支持的模块: {req.module}")

    now = datetime.now(timezone.utc)
    action = config["action"]
    table = config["table"]
    date_col = config["date_col"]
    date_type = config["date_type"]

    if date_type == "timestamptz":
        where = f"{date_col} >= :d1 AND {date_col} < :d2 + INTERVAL '1 day'"
        d2 = datetime.combine(req.date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
    else:
        where = f"{date_col} BETWEEN :d1 AND :d2"
        d2 = req.date_to

    if action == "void":
        result = db.execute(text(
            f"UPDATE {table} SET status='voided', updated_at=:now "
            f"WHERE {where} AND status != 'voided'"
        ), {"now": now, "d1": req.date_from, "d2": d2})
        # 工资和返费作废时联动日记账
        if req.module == "salary":
            db.execute(text(
                "UPDATE cash_transactions SET status='voided', updated_at=:now "
                "WHERE id IN (SELECT tl.transaction_id FROM transaction_links tl "
                "JOIN payroll_items pi ON pi.id = tl.source_id AND tl.source_type = 'payroll_item' "
                f"JOIN payroll_batches pb ON pb.id = pi.batch_id WHERE pb.{where})"
            ), {"now": now, "d1": req.date_from, "d2": d2})
        elif req.module == "rebate":
            db.execute(text(
                "UPDATE cash_transactions SET status='voided', updated_at=:now "
                "WHERE id IN (SELECT tl.transaction_id FROM transaction_links tl "
                f"WHERE tl.source_type = 'rebate' AND tl.source_id IN "
                f"(SELECT id FROM recruitment_rebates WHERE {where}))"
            ), {"now": now, "d1": req.date_from, "d2": d2})
        elif req.module == "payment":
            db.execute(text(
                "UPDATE cash_transactions SET status='voided', updated_at=:now "
                "WHERE id IN (SELECT tl.transaction_id FROM transaction_links tl "
                f"WHERE tl.source_type = 'payment' AND tl.source_id IN "
                f"(SELECT id FROM payments WHERE {where}))"
            ), {"now": now, "d1": req.date_from, "d2": d2})

    elif action == "delete":
        result = db.execute(text(f"DELETE FROM {table} WHERE {where}"),
                            {"d1": req.date_from, "d2": d2})

    elif action == "soft_delete":
        result = db.execute(text(
            f"UPDATE {table} SET deleted_at=:now, updated_at=:now "
            f"WHERE {where} AND deleted_at IS NULL"
        ), {"now": now, "d1": req.date_from, "d2": d2})

    elif action == "terminate":
        result = db.execute(text(
            f"UPDATE {table} SET status='terminated', terminated_at=:today, updated_at=:now "
            f"WHERE {where} AND status NOT IN ('terminated','expired')"
        ), {"today": now.date(), "now": now, "d1": req.date_from, "d2": d2})

    else:
        raise HTTPException(500, f"未知的清除策略: {action}")

    db.commit()
    return {"ok": True, "affected": result.rowcount, "module": req.module,
            "date_from": req.date_from.isoformat(), "date_to": req.date_to.isoformat()}
