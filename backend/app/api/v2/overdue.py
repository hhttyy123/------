"""回款逾期跟进"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/receivables")
def overdue_receivables(db: Session = Depends(get_db)):
    today = date.today()
    rows = db.execute(text("""
        SELECT r.id, r.expected_date, r.amount, r.received_amount,
               r.amount - r.received_amount AS remaining,
               :today - r.expected_date AS overdue_days,
               c.name AS company_name, r.status, r.remark
        FROM receivables r
        JOIN companies c ON c.id = r.company_id
        WHERE r.expected_date < :today AND r.status NOT IN ('paid','voided')
        ORDER BY overdue_days DESC, remaining DESC
    """), {"today": today}).mappings().all()

    items = [{
        "id": r["id"], "company_name": r["company_name"],
        "expected_date": str(r["expected_date"]),
        "amount": float(r["amount"]),
        "received_amount": float(r["received_amount"] or 0),
        "remaining": float(r["remaining"] or 0),
        "overdue_days": int(r["overdue_days"] or 0),
        "status": r["status"], "remark": r["remark"] or "",
    } for r in rows]

    total_remaining = sum(i["remaining"] for i in items)

    return {"items": items, "total": len(items), "total_remaining": round(total_remaining, 2)}


@router.get("/acceptances")
def bank_acceptances(db: Session = Depends(get_db)):
    """银行承兑即将到期"""
    today = date.today()
    rows = db.execute(text("""
        SELECT p.id, p.payment_date, p.amount, p.acceptance_due_date,
               p.acceptance_due_date - :today AS days_left,
               c.name AS company_name, p.bank_reference, p.status
        FROM payments p
        JOIN companies c ON c.id = p.company_id
        WHERE p.payment_method = 'bank_acceptance'
          AND p.status = 'confirmed'
          AND p.acceptance_due_date IS NOT NULL
          AND p.acceptance_due_date >= :today
        ORDER BY p.acceptance_due_date
    """), {"today": today}).mappings().all()

    return {"items": [{
        "id": r["id"], "company_name": r["company_name"],
        "amount": float(r["amount"]),
        "acceptance_due_date": str(r["acceptance_due_date"]),
        "days_left": int(r["days_left"] or 0),
        "bank_reference": r["bank_reference"] or "",
    } for r in rows]}
