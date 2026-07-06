# advisor.py - AI assistant with function calling
"""AI advisor powered by DeepSeek function calling."""
import json
from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.agents.deepseek_client import get_client
from app.config import settings
from app.database import get_db

router = APIRouter()
client = get_client()

# ---- Tool definitions for function calling ----

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_journal",
            "description": "查询日记账流水明细。可指定日期范围、现金/银行、收入/支出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "开始日期 YYYY-MM-DD，如 2026-01-02"},
                    "date_to": {"type": "string", "description": "结束日期 YYYY-MM-DD，如 2026-01-03"},
                    "ledger_type": {"type": "string", "enum": ["cash", "bank"], "description": "现金或银行"},
                    "direction": {"type": "string", "enum": ["income", "expense"], "description": "收入或支出"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_receivables",
            "description": "查询应收账款/回款情况，包括逾期、待回、已回。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "overdue", "paid", "all"], "description": "回款状态"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_payroll",
            "description": "查询工资发放记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "开始月份 YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "结束月份 YYYY-MM-DD"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_rebates",
            "description": "查询代招返费记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "开始日期"},
                    "date_to": {"type": "string", "description": "结束日期"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_profit",
            "description": "查询利润趋势，按月统计收入和支出。",
            "parameters": {
                "type": "object",
                "properties": {
                    "months": {"type": "integer", "description": "查询最近几个月，默认6"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_companies",
            "description": "查询合作企业列表及状态。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_employees",
            "description": "查询在职人员列表。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_contracts",
            "description": "查询合同情况，包括即将到期和未签合同的预警。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_attendance",
            "description": "查询考勤记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "description": "开始日期"},
                    "date_to": {"type": "string", "description": "结束日期"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_invoices",
            "description": "查询开票记录。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": "获取公司经营概况汇总（人员、资金、预警、审批等）。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
]

# ---- Tool implementations ----

def _exec_journal(db: Session, date_from=None, date_to=None, ledger_type=None, direction=None):
    sql = "SELECT transaction_date, ledger_type, direction, amount, payment_method, summary FROM cash_transactions WHERE status='confirmed'"
    params = {}
    if date_from: sql += " AND transaction_date >= :df"; params["df"] = date_from
    if date_to: sql += " AND transaction_date <= :dt"; params["dt"] = date_to
    if ledger_type: sql += " AND ledger_type = :lt"; params["lt"] = ledger_type
    if direction: sql += " AND direction = :dir"; params["dir"] = direction
    sql += " ORDER BY transaction_date, id"
    rows = db.execute(text(sql), params).mappings().all()
    total_in = sum(r.amount for r in rows if r.direction == "income")
    total_out = sum(r.amount for r in rows if r.direction == "expense")
    items = [{"date": str(r.transaction_date), "type": r.direction, "amount": float(r.amount), "ledger": r.ledger_type, "method": r.payment_method or "", "summary": r.summary or ""} for r in rows]
    return {"count": len(rows), "total_income": round(total_in, 2), "total_expense": round(total_out, 2), "items": items}

def _exec_receivables(db: Session, status=None):
    today = date.today()
    sql = """SELECT c.name AS company, r.expected_date, r.amount, r.received_amount, r.status,
                    r.amount - r.received_amount AS remaining, :today - r.expected_date AS overdue_days
             FROM receivables r JOIN companies c ON c.id=r.company_id WHERE r.status!='voided'"""
    params = {"today": today}
    if status == "overdue": sql += " AND r.expected_date < :today AND r.status NOT IN ('paid','voided')"
    elif status == "pending": sql += " AND r.status = 'pending'"
    elif status == "paid": sql += " AND r.status = 'paid'"
    sql += " ORDER BY overdue_days DESC NULLS LAST"
    rows = db.execute(text(sql), params).mappings().all()
    total_remaining = sum(r.remaining or 0 for r in rows)
    items = [{"company": r.company, "expected_date": str(r.expected_date), "amount": float(r.amount), "received": float(r.received_amount or 0), "remaining": float(r.remaining or 0), "overdue_days": int(r.overdue_days or 0), "status": r.status} for r in rows]
    return {"count": len(rows), "total_remaining": round(float(total_remaining), 2), "items": items}

def _exec_payroll(db: Session, date_from=None, date_to=None):
    sql = """SELECT e.name, pb.salary_month, pi.net_pay, pb.status
             FROM payroll_items pi JOIN employees e ON e.id=pi.employee_id
             JOIN payroll_batches pb ON pb.id=pi.batch_id WHERE pb.status!='voided'"""
    params = {}
    if date_from: sql += " AND pb.salary_month >= :df"; params["df"] = date_from
    if date_to: sql += " AND pb.salary_month <= :dt"; params["dt"] = date_to
    sql += " ORDER BY pb.salary_month DESC, e.name"
    rows = db.execute(text(sql), params).mappings().all()
    total = sum(r.net_pay or 0 for r in rows)
    items = [{"employee": r.name, "month": str(r.salary_month)[:7], "net_pay": float(r.net_pay), "status": r.status} for r in rows]
    return {"count": len(rows), "total": round(float(total), 2), "items": items}

def _exec_rebates(db: Session, date_from=None, date_to=None):
    sql = """SELECT c.name AS company, r.rebate_date, r.amount, r.person_count, r.status
             FROM recruitment_rebates r JOIN companies c ON c.id=r.company_id WHERE r.status!='voided'"""
    params = {}
    if date_from: sql += " AND r.rebate_date >= :df"; params["df"] = date_from
    if date_to: sql += " AND r.rebate_date <= :dt"; params["dt"] = date_to
    sql += " ORDER BY r.rebate_date DESC"
    rows = db.execute(text(sql), params).mappings().all()
    total = sum(r.amount or 0 for r in rows)
    items = [{"company": r.company, "date": str(r.rebate_date), "amount": float(r.amount), "persons": r.person_count, "status": r.status} for r in rows]
    return {"count": len(rows), "total": round(float(total), 2), "items": items}

def _exec_profit(db: Session, months=6):
    rows = db.execute(text("""
        SELECT to_char(transaction_date,'YYYY-MM') AS month,
               COALESCE(SUM(amount) FILTER (WHERE direction='income'),0) AS income,
               COALESCE(SUM(amount) FILTER (WHERE direction='expense'),0) AS expense
        FROM cash_transactions WHERE status='confirmed'
          AND transaction_date >= date_trunc('month', CURRENT_DATE) - (:m || ' months')::INTERVAL
        GROUP BY month ORDER BY month
    """), {"m": str(months - 1)}).mappings().all()
    items = [{"month": r.month, "income": float(r.income), "expense": float(r.expense), "profit": round(float(r.income - r.expense), 2)} for r in rows]
    return {"months": months, "data": items}

def _exec_companies(db: Session):
    rows = db.execute(text("SELECT name, contact_person, contact_phone, cooperation_status, cooperation_start_date, cooperation_end_date FROM companies WHERE deleted_at IS NULL ORDER BY name")).mappings().all()
    return {"count": len(rows), "items": [{"name": r.name, "contact": r.contact_person or "", "phone": r.contact_phone or "", "status": r.cooperation_status, "start": str(r.cooperation_start_date) if r.cooperation_start_date else "", "end": str(r.cooperation_end_date) if r.cooperation_end_date else ""} for r in rows]}

def _exec_employees(db: Session):
    rows = db.execute(text("SELECT e.name, e.phone, e.gender, e.status, c.name AS company FROM employees e LEFT JOIN employment_records er ON er.employee_id=e.id AND er.status='active' LEFT JOIN companies c ON c.id=er.company_id WHERE e.deleted_at IS NULL ORDER BY e.name")).mappings().all()
    return {"count": len(rows), "items": [{"name": r.name, "phone": r.phone or "", "gender": r.gender or "", "status": r.status, "company": r.company or ""} for r in rows]}

def _exec_contracts(db: Session):
    today = date.today()
    rows = db.execute(text("SELECT e.name AS employee, c.contract_no, c.start_date, c.end_date, c.status FROM contracts c JOIN employees e ON e.id=c.employee_id ORDER BY c.end_date")).mappings().all()
    expiring = db.execute(text("SELECT e.name FROM contracts c JOIN employees e ON e.id=c.employee_id WHERE c.status='active' AND c.end_date BETWEEN :t AND :t + INTERVAL '15 days'"), {"t": today}).mappings().all()
    unsigned = db.execute(text("SELECT e.name FROM employees e JOIN employment_records er ON er.employee_id=e.id AND er.status='active' WHERE e.status='active' AND e.deleted_at IS NULL AND er.entry_date < :t - INTERVAL '20 days' AND NOT EXISTS (SELECT 1 FROM contracts c WHERE c.employee_id=e.id AND c.status='active')"), {"t": today}).mappings().all()
    return {"count": len(rows), "items": [{"employee": r.employee, "contract_no": r.contract_no or "", "start": str(r.start_date), "end": str(r.end_date), "status": r.status} for r in rows], "expiring_soon": [e.name for e in expiring], "unsigned_contract": [e.name for e in unsigned]}

def _exec_attendance(db: Session, date_from=None, date_to=None):
    sql = """SELECT e.name, a.work_date, a.status, a.hours, a.deduction_amount
             FROM attendance_records a JOIN employment_records er ON er.id=a.employment_id JOIN employees e ON e.id=er.employee_id WHERE 1=1"""
    params = {}
    if date_from: sql += " AND a.work_date >= :df"; params["df"] = date_from
    if date_to: sql += " AND a.work_date <= :dt"; params["dt"] = date_to
    sql += " ORDER BY a.work_date DESC, e.name"
    rows = db.execute(text(sql), params).mappings().all()
    items = [{"employee": r.name, "date": str(r.work_date), "status": r.status, "hours": float(r.hours or 0), "deduction": float(r.deduction_amount or 0)} for r in rows]
    return {"count": len(rows), "items": items}

def _exec_invoices(db: Session):
    rows = db.execute(text("SELECT c.name AS company, i.invoice_no, i.invoice_date, i.amount, i.status FROM invoices i JOIN companies c ON c.id=i.company_id ORDER BY i.invoice_date DESC")).mappings().all()
    total = sum(r.amount or 0 for r in rows)
    return {"count": len(rows), "total": round(float(total), 2), "items": [{"company": r.company, "invoice_no": r.invoice_no, "date": str(r.invoice_date), "amount": float(r.amount), "status": r.status} for r in rows]}

def _exec_summary(db: Session):
    today = date.today()
    month_start = today.replace(day=1)
    employees = db.execute(text("SELECT COUNT(*) FROM employees WHERE status='active' AND deleted_at IS NULL")).scalar() or 0
    companies = db.execute(text("SELECT COUNT(*) FROM companies WHERE cooperation_status='active' AND deleted_at IS NULL")).scalar() or 0
    cash = db.execute(text("SELECT COALESCE(SUM(amount) FILTER (WHERE direction='income'),0) AS income, COALESCE(SUM(amount) FILTER (WHERE direction='expense'),0) AS expense FROM cash_transactions WHERE status='confirmed' AND transaction_date >= :ms"), {"ms": month_start}).mappings().one()
    year_cash = db.execute(text("SELECT COALESCE(SUM(amount) FILTER (WHERE direction='income'),0) AS income, COALESCE(SUM(amount) FILTER (WHERE direction='expense'),0) AS expense FROM cash_transactions WHERE status='confirmed' AND transaction_date >= :ys"), {"ys": today.replace(month=1, day=1)}).mappings().one()
    overdue = db.execute(text("SELECT COUNT(*) AS count, COALESCE(SUM(amount - received_amount),0) AS total FROM receivables WHERE expected_date < :t AND status NOT IN ('paid','voided')"), {"t": today}).mappings().one()
    expiring = db.execute(text("SELECT COUNT(*) FROM contracts WHERE status='active' AND end_date BETWEEN :t AND :t + INTERVAL '15 days'"), {"t": today}).scalar() or 0
    unsigned = db.execute(text("SELECT COUNT(*) FROM employees e JOIN employment_records er ON er.employee_id=e.id AND er.status='active' WHERE e.status='active' AND e.deleted_at IS NULL AND er.entry_date < :t - INTERVAL '20 days' AND NOT EXISTS (SELECT 1 FROM contracts c WHERE c.employee_id=e.id AND c.status='active')"), {"t": today}).scalar() or 0
    approvals = db.execute(text("SELECT COUNT(*) FROM payroll_batches WHERE status IN ('finance_review','owner_review')")).scalar() or 0
    return {"date": str(today), "employees_active": employees, "companies_active": companies, "month_income": float(cash["income"] or 0), "month_expense": float(cash["expense"] or 0), "year_income": float(year_cash["income"] or 0), "year_expense": float(year_cash["expense"] or 0), "overdue_count": overdue["count"], "overdue_amount": float(overdue["total"] or 0), "contract_expiring": expiring, "unsigned_contract": unsigned, "pending_approvals": approvals}

TOOL_EXECUTORS = {
    "query_journal": _exec_journal,
    "query_receivables": _exec_receivables,
    "query_payroll": _exec_payroll,
    "query_rebates": _exec_rebates,
    "query_profit": _exec_profit,
    "query_companies": _exec_companies,
    "query_employees": _exec_employees,
    "query_contracts": _exec_contracts,
    "query_attendance": _exec_attendance,
    "query_invoices": _exec_invoices,
    "get_summary": _exec_summary,
}


class AskRequest(BaseModel):
    question: str
    history: list[dict] = []


@router.get("/context")
def advisor_context(db: Session = Depends(get_db)):
    return _exec_summary(db)


@router.post("/ask")
async def advisor_ask(req: AskRequest, db: Session = Depends(get_db)):
    system = """你是曼克斯劳务派遣公司的数据分析助手。你可以调用工具函数来查询公司的各项数据。

使用规则：
1. 分析用户问题的意图，主动调用相关工具获取数据
2. 可以同时调用多个工具（如同时查日记账和回款）
3. 日期参数始终用 YYYY-MM-DD 格式；如果用户说"昨天""上周""本月"，自己推算当前日期
4. 用查询到的真实数据回答问题，不要编造
5. 如果查询结果为空，明确告知"当前没有符合条件的数据"
6. 回答简洁，先给结论再列明细"""

    messages = [{"role": "system", "content": system}]
    for h in (req.history or [])[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:2000]})
    messages.append({"role": "user", "content": req.question})

    # First call: let AI decide which tools to call
    resp = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        max_tokens=1500,
        temperature=0.1,
        messages=messages,
        tools=TOOLS,
    )

    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None) or []

    # Execute tool calls
    tool_results = []
    if tool_calls:
        for tc in tool_calls:
            func_name = tc.function.name
            func_args = json.loads(tc.function.arguments)
            executor = TOOL_EXECUTORS.get(func_name)
            if executor:
                try:
                    result = executor(db, **func_args)
                    tool_results.append({"id": tc.id, "name": func_name, "result": result})
                except Exception as e:
                    tool_results.append({"id": tc.id, "name": func_name, "error": str(e)})

        # Add AI response and tool results to messages
        messages.append({"role": "assistant", "content": None, "tool_calls": [tc.model_dump() for tc in tool_calls]})
        for tr in tool_results:
            messages.append({"role": "tool", "tool_call_id": tr["id"], "content": json.dumps(tr.get("result", tr.get("error", "")), ensure_ascii=False, default=str)})

        # Second call: AI synthesizes the answer
        resp2 = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            max_tokens=2000,
            temperature=0.1,
            messages=messages,
        )
        answer = (resp2.choices[0].message.content or "").strip()
    else:
        # No tool calls needed - AI answered directly from context
        answer = msg.content or ""

    return {"answer": answer, "tools_used": [t["name"] for t in tool_results]}
