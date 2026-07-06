from app.services import business
from app.services.repository import JsonRepository


def test_repository_create_record_adds_metadata(tmp_path):
    repository = JsonRepository(tmp_path)

    record = repository.create_record("employee", {"name": "张三"})

    assert record["id"] == 1
    assert record["created_at"]
    assert record["updated_at"]
    assert record["_source"]["type"] == "manual"
    assert repository.list_records("employee")[0]["name"] == "张三"


def test_paid_payroll_creates_journal_entry(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path)
    monkeypatch.setattr(business, "repo", repository)

    payroll = business.create_business_record("payroll", {
        "employee_name": "张三",
        "month": "2026-06",
        "base_salary": 5000,
        "allowance": 0,
        "deduction": 0,
        "net_pay": 5000,
        "status": "已发放",
        "issued_at": "2026-06-20",
    })

    journal = repository.list_records("journal")
    approvals = repository.list_records("approval")
    assert payroll["id"] == 1
    assert journal[0]["expense_amount"] == 5000
    assert journal[0]["source_type"] == "工资发放"
    assert approvals[0]["status"] == "待审核"


def test_profit_calculation_uses_financial_chain(tmp_path):
    repository = JsonRepository(tmp_path)
    repository.create_record("accounts_receivable", {
        "company_name": "A公司",
        "actual_date": "2026-06-10",
        "expected_date": "2026-06-01",
        "amount": 10000,
        "status": "已到账",
    })
    repository.create_record("payroll", {
        "month": "2026-06",
        "net_pay": 4000,
        "status": "已发放",
    })
    repository.create_record("recruitment_fee", {"date": "2026-06-03", "amount": 1000})
    repository.create_record("finance", {"date": "2026-06-04", "type": "支出", "amount": 500})

    profit = business.calculate_profit("2026-06", repository=repository)

    assert profit["total_income"] == 10000
    assert profit["salary_expense"] == 4000
    assert profit["recruitment_fee_expense"] == 1000
    assert profit["other_expense"] == 500
    assert profit["net_profit"] == 4500


def test_overdue_receivable_generates_warning(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path)
    monkeypatch.setattr(business, "repo", repository)
    repository.create_record("accounts_receivable", {
        "company_name": "B公司",
        "expected_date": "2020-01-01",
        "amount": 3000,
        "status": "待回款",
    })

    warnings = business.generate_warnings()

    assert warnings[0]["type"] == "回款逾期"
    assert "B公司" in warnings[0]["title"]
