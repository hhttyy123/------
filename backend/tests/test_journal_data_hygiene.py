from app.services import business
from app.services.repository import JsonRepository


def test_journal_list_hides_invalid_legacy_import_rows(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path)
    monkeypatch.setattr(business, "repo", repository)
    repository.create_record("journal", {
        "date": "income_amount",
        "income_amount": "",
        "expense_amount": "",
        "income_method": "income_amount",
        "description": "expense_amount",
        "_imported_at": "2026-06-18 14:25:45",
    })
    repository.create_record("journal", {
        "date": "0.1",
        "income_amount": "",
        "expense_amount": "",
        "income_method": "99514",
        "description": "118742.52",
        "_imported_at": "2026-06-18 14:25:45",
    })
    valid = repository.create_record("journal", {
        "date": "2026-01-03",
        "income_amount": 0.1,
        "income_method": "wechat",
        "expense_amount": 0,
        "description": "income",
    })

    records = business.list_module_records("journal")

    assert records == [valid]
