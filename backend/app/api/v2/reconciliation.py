"""数据核对中心 — 日记账与业务记录自动比对"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/check")
def check_reconciliation(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    """比对日记账与工资/返费/回款，找出不一致"""
    items: list[dict] = []

    # ---- 工资核对：已确认工资 vs 日记账支出 ----
    payroll_issues = db.execute(text("""
        SELECT pi.id AS source_id, 'payroll' AS source_type,
               e.name AS source_label, pb.salary_month AS ref_date,
               pi.net_pay AS expected_amount,
               COALESCE((
                   SELECT SUM(ct.amount) FROM transaction_links tl
                   JOIN cash_transactions ct ON ct.id = tl.transaction_id AND ct.status != 'voided'
                   WHERE tl.source_type = 'payroll_item' AND tl.source_id = pi.id
               ), 0) AS journal_amount
        FROM payroll_items pi
        JOIN employees e ON e.id = pi.employee_id
        JOIN payroll_batches pb ON pb.id = pi.batch_id
        WHERE pb.status = 'confirmed'
          AND (:df IS NULL OR pb.salary_month >= :df)
          AND (:dt IS NULL OR pb.salary_month <= :dt)
    """), {"df": date_from, "dt": date_to}).mappings().all()

    for r in payroll_issues:
        diff = float(r["expected_amount"] or 0) - float(r["journal_amount"] or 0)
        if abs(diff) > 0.01:
            items.append({
                "source_type": "工资发放",
                "source_id": r["source_id"],
                "source_label": r["source_label"],
                "ref_date": str(r["ref_date"]) if r["ref_date"] else "",
                "expected_amount": float(r["expected_amount"] or 0),
                "journal_amount": float(r["journal_amount"] or 0),
                "difference": round(diff, 2),
                "issue": "日记账缺失" if float(r["journal_amount"] or 0) == 0 else "金额不一致",
            })

    # ---- 返费核对 ----
    rebate_issues = db.execute(text("""
        SELECT r.id AS source_id, 'rebate' AS source_type,
               COALESCE(e.name, c.name) AS source_label,
               r.rebate_date AS ref_date, r.amount AS expected_amount,
               COALESCE((
                   SELECT SUM(ct.amount) FROM transaction_links tl
                   JOIN cash_transactions ct ON ct.id = tl.transaction_id AND ct.status != 'voided'
                   WHERE tl.source_type = 'rebate' AND tl.source_id = r.id
               ), 0) AS journal_amount
        FROM recruitment_rebates r
        LEFT JOIN employees e ON e.id = r.employee_id
        LEFT JOIN companies c ON c.id = r.company_id
        WHERE r.status = 'confirmed'
          AND (:df IS NULL OR r.rebate_date >= :df)
          AND (:dt IS NULL OR r.rebate_date <= :dt)
    """), {"df": date_from, "dt": date_to}).mappings().all()

    for r in rebate_issues:
        diff = float(r["expected_amount"] or 0) - float(r["journal_amount"] or 0)
        if abs(diff) > 0.01:
            items.append({
                "source_type": "返费支出",
                "source_id": r["source_id"],
                "source_label": r["source_label"] or "",
                "ref_date": str(r["ref_date"]) if r["ref_date"] else "",
                "expected_amount": float(r["expected_amount"] or 0),
                "journal_amount": float(r["journal_amount"] or 0),
                "difference": round(diff, 2),
                "issue": "日记账缺失" if float(r["journal_amount"] or 0) == 0 else "金额不一致",
            })

    # ---- 回款核对 ----
    payment_issues = db.execute(text("""
        SELECT p.id AS source_id, 'payment' AS source_type,
               c.name AS source_label, p.payment_date AS ref_date,
               p.amount AS expected_amount,
               COALESCE((
                   SELECT SUM(ct.amount) FROM transaction_links tl
                   JOIN cash_transactions ct ON ct.id = tl.transaction_id AND ct.status != 'voided'
                   WHERE tl.source_type = 'payment' AND tl.source_id = p.id
               ), 0) AS journal_amount
        FROM payments p
        JOIN companies c ON c.id = p.company_id
        WHERE p.status = 'confirmed'
          AND (:df IS NULL OR p.payment_date >= :df)
          AND (:dt IS NULL OR p.payment_date <= :dt)
    """), {"df": date_from, "dt": date_to}).mappings().all()

    for r in payment_issues:
        diff = float(r["expected_amount"] or 0) - float(r["journal_amount"] or 0)
        if abs(diff) > 0.01:
            items.append({
                "source_type": "回款收入",
                "source_id": r["source_id"],
                "source_label": r["source_label"] or "",
                "ref_date": str(r["ref_date"]) if r["ref_date"] else "",
                "expected_amount": float(r["expected_amount"] or 0),
                "journal_amount": float(r["journal_amount"] or 0),
                "difference": round(diff, 2),
                "issue": "日记账缺失" if float(r["journal_amount"] or 0) == 0 else "金额不一致",
            })

    # 排序：差异最大的排前面
    items.sort(key=lambda x: abs(x["difference"]), reverse=True)

    return {
        "items": items,
        "total": len(items),
        "ok": len(items) == 0,
    }
