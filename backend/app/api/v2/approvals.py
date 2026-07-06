"""审批中心"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/pending")
def list_pending(db: Session = Depends(get_db)):
    """列出所有待审批项"""
    # 待审批工资
    salary = db.execute(text("""
        SELECT pi.id, 'salary' AS module, e.name AS label, pb.salary_month AS ref_date,
               pi.net_pay AS amount, pb.status
        FROM payroll_items pi
        JOIN employees e ON e.id = pi.employee_id
        JOIN payroll_batches pb ON pb.id = pi.batch_id
        WHERE pb.status IN ('finance_review','owner_review')
        ORDER BY pb.salary_month DESC
        LIMIT 50
    """)).mappings().all()

    # 待审批返费
    rebate = db.execute(text("""
        SELECT r.id, 'rebate' AS module, c.name AS label, r.rebate_date AS ref_date,
               r.amount, r.status
        FROM recruitment_rebates r
        JOIN companies c ON c.id = r.company_id
        WHERE r.status IN ('finance_review','owner_review')
        ORDER BY r.rebate_date DESC
        LIMIT 50
    """)).mappings().all()

    items = []
    for r in salary:
        items.append({"id": r["id"], "module": "salary", "label": f"工资 - {r['label']}",
                       "ref_date": str(r["ref_date"]), "amount": float(r["amount"] or 0),
                       "status": r["status"]})
    for r in rebate:
        items.append({"id": r["id"], "module": "rebate", "label": f"返费 - {r['label']}",
                       "ref_date": str(r["ref_date"]), "amount": float(r["amount"] or 0),
                       "status": r["status"]})

    return {"items": items, "total": len(items)}
