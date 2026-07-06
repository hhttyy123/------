import asyncio

import pandas as pd

from app.services import import_batch


def test_parallel_journal_does_not_forward_fill_income_rows(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    data_dir = tmp_path / "storage"
    upload_dir.mkdir()
    data_dir.mkdir()
    upload_id = "cash-journal-no-duplicate-income"
    file_path = upload_dir / f"{upload_id}.xlsx"

    df = pd.DataFrame({
        "日期": ["2026-01-03", ""],
        "收入金额": [0.1, ""],
        "收入方式": ["微信零钱", ""],
        "摘要说明": ["零钱通收益", ""],
        "日期.1": ["2026-01-04", "2026-01-04"],
        "支出金额": [17739.5, 4809],
        "支出方式": ["微信零钱", "微信零钱"],
        "摘要说明.1": ["支付12月明昌员工工资", "支付12月瑞赞金属员工工资"],
    })
    df.to_excel(file_path, index=False)

    monkeypatch.setattr(import_batch.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(import_batch.settings, "DATA_DIR", str(data_dir))

    batch = asyncio.run(import_batch.prepare_import(upload_id))
    journal_records = batch["targets"][0]["records"]
    income_records = [record for record in journal_records if record["income_amount"]]
    expense_records = [record for record in journal_records if record["expense_amount"]]

    assert len(income_records) == 1
    assert income_records[0]["income_amount"] == 0.1
    assert len(expense_records) == 2


def test_journal_validation_blocks_misaligned_date_values():
    issues = import_batch.validate_records("journal", [
        {
            "date": "income_amount",
            "income_amount": 100,
            "expense_amount": 0,
        },
        {
            "date": "0.1",
            "income_amount": 0.1,
            "expense_amount": 0,
        },
    ])

    date_blockers = [
        issue for issue in issues
        if issue["field"] == "date" and issue["severity"] == "blocker"
    ]
    assert len(date_blockers) == 2
