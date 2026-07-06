"""首页仪表盘 — PostgreSQL 实时数据"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)

    # 在职人员
    active_employees = db.execute(text(
        "SELECT COUNT(*) FROM employees WHERE status='active' AND deleted_at IS NULL"
    )).scalar() or 0

    # 本月收入
    month_income = db.execute(text(
        """SELECT COALESCE(SUM(amount),0) FROM cash_transactions
           WHERE direction='income' AND status='confirmed'
           AND transaction_date >= :ms"""),
        {"ms": month_start}
    ).scalar() or 0

    # 本月支出
    month_expense = db.execute(text(
        """SELECT COALESCE(SUM(amount),0) FROM cash_transactions
           WHERE direction='expense' AND status='confirmed'
           AND transaction_date >= :ms"""),
        {"ms": month_start}
    ).scalar() or 0

    # 预警数量：合同到期 + 未签合同 + 回款逾期
    expiring = db.execute(text(
        "SELECT COUNT(*) FROM contracts WHERE status='active' AND end_date BETWEEN :today AND :future"
    ), {"today": today, "future": today + timedelta(days=15)}).scalar() or 0

    unsigned = db.execute(text(
        """SELECT COUNT(*) FROM employees e
           JOIN employment_records er ON er.employee_id = e.id AND er.status='active'
           WHERE e.status='active' AND e.deleted_at IS NULL
           AND er.entry_date < :cutoff
           AND NOT EXISTS (SELECT 1 FROM contracts c WHERE c.employee_id=e.id AND c.status='active')"""
    ), {"cutoff": today - timedelta(days=20)}).scalar() or 0

    overdue_receivable = db.execute(text(
        "SELECT COUNT(*) FROM receivables WHERE expected_date < :today AND status NOT IN ('paid','voided')"
    ), {"today": today}).scalar() or 0

    warning_count = expiring + unsigned + overdue_receivable

    # 审批待办
    approval_count = db.execute(text(
        "SELECT COUNT(*) FROM approval_requests WHERE current_status IN ('finance_review','owner_review')"
    )).scalar() or 0

    return {
        "active_employees": active_employees,
        "month_receivable": float(month_income),
        "month_salary": float(month_expense),
        "month_profit": float(month_income - month_expense),
        "warning_count": warning_count,
        "approval_count": approval_count,
        "current_month": today.strftime("%Y-%m"),
    }
