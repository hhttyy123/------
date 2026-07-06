from app.services import business, import_batch
from app.services.repository import JsonRepository


def test_commit_batch_writes_journal_and_finance_targets(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path / "storage")
    monkeypatch.setattr(business, "repo", repository)
    monkeypatch.setattr(import_batch.settings, "DATA_DIR", str(tmp_path / "storage"))

    batch = import_batch.save_batch({
        "batch_id": "sync-batch",
        "filename": "cash.xlsx",
        "module": "workbook",
        "module_label": "整本工作簿",
        "sheet_name": "全部工作表",
        "status": "prepared",
        "rows_total": 2,
        "rows_ready": 2,
        "rows_blocked": 0,
        "records": [],
        "display_records": [],
        "targets": [
            {
                "module": "journal",
                "module_label": "日记账",
                "sheet_name": "现金日记账",
                "selected": True,
                "rows_total": 1,
                "rows_ready": 1,
                "rows_blocked": 0,
                "records": [{
                    "date": "2026-01-03",
                    "income_amount": 0.1,
                    "income_method": "微信零钱",
                    "expense_amount": 0,
                    "expense_method": "",
                    "description": "零钱通收益",
                }],
                "issues": [],
            },
            {
                "module": "finance",
                "module_label": "财务记录",
                "sheet_name": "现金日记账",
                "selected": True,
                "rows_total": 1,
                "rows_ready": 1,
                "rows_blocked": 0,
                "records": [{
                    "date": "2026-01-03",
                    "type": "收入",
                    "category": "其他",
                    "amount": 0.1,
                    "remark": "零钱通收益",
                }],
                "issues": [],
            },
        ],
        "issues": [],
        "fingerprint": "test",
        "cache_hit": False,
        "header_row_index": 0,
        "created_at": "2026-01-03 00:00:00",
    })

    committed = import_batch.commit_batch(batch["batch_id"])

    assert committed["status"] == "committed"
    assert committed["committed_rows"] == 2
    assert repository.list_records("journal")[0]["income_amount"] == 0.1
    assert repository.list_records("finance")[0]["amount"] == 0.1


def test_commit_batch_reports_target_error_when_batch_create_fails(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path / "storage")
    monkeypatch.setattr(business, "repo", repository)
    monkeypatch.setattr(import_batch.settings, "DATA_DIR", str(tmp_path / "storage"))

    def flaky_create_many(module, rows, source=None):
        raise ValueError("bad target")

    monkeypatch.setattr(import_batch, "create_business_records", flaky_create_many)

    batch = import_batch.save_batch({
        "batch_id": "partial-sync-batch",
        "filename": "cash.xlsx",
        "module": "workbook",
        "module_label": "整本工作簿",
        "sheet_name": "全部工作表",
        "status": "prepared",
        "rows_total": 2,
        "rows_ready": 2,
        "rows_blocked": 0,
        "records": [],
        "display_records": [],
        "targets": [{
            "module": "journal",
            "module_label": "日记账",
            "sheet_name": "现金日记账",
            "selected": True,
            "rows_total": 2,
            "rows_ready": 2,
            "rows_blocked": 0,
            "records": [
                {"date": "2026-01-03", "income_amount": 0.1, "expense_amount": 0, "description": "ok"},
                {"date": "2026-01-03", "income_amount": 0.2, "expense_amount": 0, "description": "bad"},
            ],
            "issues": [],
        }],
        "issues": [],
        "fingerprint": "test",
        "cache_hit": False,
        "header_row_index": 0,
        "created_at": "2026-01-03 00:00:00",
    })

    committed = import_batch.commit_batch(batch["batch_id"])

    assert committed["status"] == "failed"
    assert committed["committed_rows"] == 0
    assert committed["commit_errors"][0]["message"] == "bad target"
