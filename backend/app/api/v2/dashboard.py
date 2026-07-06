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

    # 正常合作企业
    active_companies = db.execute(text(
        "SELECT COUNT(*) FROM companies WHERE cooperation_status='active' AND deleted_at IS NULL"
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

    # 日记账总笔数
    journal_count = db.execute(text(
        "SELECT COUNT(*) FROM cash_transactions WHERE status='confirmed'"
    )).scalar() or 0

    # 审批待办
    approval_count = db.execute(text(
        "SELECT COUNT(*) FROM payroll_batches WHERE status IN ('finance_review','owner_review')"
    )).scalar() or 0
    approval_count += db.execute(text(
        "SELECT COUNT(*) FROM recruitment_rebates WHERE status IN ('finance_review','owner_review')"
    )).scalar() or 0

    # ---- 预警列表 ----
    warnings = []

    # 合同到期预警
    expiring = db.execute(text(
        """SELECT e.name AS employee_name, c.end_date, (c.end_date - :today) AS days_left
           FROM contracts c JOIN employees e ON e.id=c.employee_id
           WHERE c.status='active' AND c.end_date BETWEEN :today AND :future
           ORDER BY c.end_date"""),
        {"today": today, "future": today + timedelta(days=15)}
    ).mappings().all()
    for r in expiring:
        warnings.append({
            "type": "合同到期",
            "title": f"{r.employee_name} 合同即将到期",
            "message": f"还有 {r.days_left} 天到期（{r.end_date}）",
            "severity": "info",
        })

    # 未签合同预警
    unsigned = db.execute(text(
        """SELECT e.name AS employee_name, er.entry_date, (:today - er.entry_date) AS days_worked
           FROM employees e
           JOIN employment_records er ON er.employee_id = e.id AND er.status='active'
           WHERE e.status='active' AND e.deleted_at IS NULL
           AND er.entry_date < :cutoff
           AND NOT EXISTS (SELECT 1 FROM contracts c WHERE c.employee_id=e.id AND c.status='active')
           ORDER BY er.entry_date"""),
        {"today": today, "cutoff": today - timedelta(days=20)}
    ).mappings().all()
    for r in unsigned:
        warnings.append({
            "type": "未签合同",
            "title": f"{r.employee_name} 入职未签合同",
            "message": f"入职已超过 {r.days_worked} 天",
            "severity": "warning",
        })

    # 回款逾期预警
    overdue_rows = db.execute(text(
        """SELECT c.name AS company_name, r.expected_date, (:today - r.expected_date) AS overdue_days,
                  r.amount, r.received_amount, (r.amount - r.received_amount) AS remaining
           FROM receivables r JOIN companies c ON c.id=r.company_id
           WHERE r.expected_date < :today AND r.status NOT IN ('paid','voided')
           ORDER BY r.expected_date"""),
        {"today": today}
    ).mappings().all()
    for r in overdue_rows:
        warnings.append({
            "type": "回款逾期",
            "title": f"{r.company_name} 回款逾期",
            "message": f"逾期 {r.overdue_days} 天，待回 ¥{float(r.remaining or 0):,.0f}",
            "severity": "warning",
        })

    return {
        "active_employees": active_employees,
        "active_companies": active_companies,
        "journal_count": journal_count,
        "month_income": float(month_income),
        "month_expense": float(month_expense),
        "month_profit": float(month_income - month_expense),
        "approval_count": approval_count,
        "warnings": warnings,
        "current_month": today.strftime("%Y-%m"),
    }
