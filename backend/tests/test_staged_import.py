from app.services.staged_import import normalize_journal_record


def test_normalize_journal_income_record():
    normalized, issues = normalize_journal_record({
        "date": "2026-01-03",
        "income_amount": 100.1,
        "income_method": "微信零钱",
        "expense_amount": 0,
        "description": "客户回款",
        "remark": "",
    }, "现金日记账")

    assert issues == []
    assert normalized["transaction_date"] == "2026-01-03"
    assert normalized["ledger_type"] == "cash"
    assert normalized["direction"] == "income"
    assert normalized["amount"] == "100.10"


def test_normalize_journal_blocks_invalid_date_and_amount():
    normalized, issues = normalize_journal_record({
        "date": "不是日期",
        "income_amount": 0,
        "expense_amount": "abc",
    }, "银行日记账")

    assert normalized["ledger_type"] == "bank"
    assert {issue["field"] for issue in issues} == {"amount", "transaction_date"}
