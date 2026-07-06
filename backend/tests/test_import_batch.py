import asyncio

import pandas as pd

from app.services import import_batch


def test_prepare_import_uses_rules_when_ai_would_fail(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    data_dir = tmp_path / "storage"
    upload_dir.mkdir()
    data_dir.mkdir()
    upload_id = "journal-upload"
    file_path = upload_dir / f"{upload_id}.xlsx"

    df = pd.DataFrame({
        "日期": ["2026-06-01", "2026-06-02"],
        "收入金额": [1000, 0],
        "收入方式": ["银行转账", ""],
        "摘要说明": ["客户回款", "发工资"],
        "支出金额": [0, 500],
        "支出方式": ["", "现金"],
    })
    df.to_excel(file_path, index=False)

    monkeypatch.setattr(import_batch.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(import_batch.settings, "DATA_DIR", str(data_dir))

    async def fail_ai(*_args, **_kwargs):
        raise RuntimeError("AI empty response")

    monkeypatch.setattr(import_batch, "run_analysis", fail_ai)

    batch = asyncio.run(import_batch.prepare_import(upload_id))

    assert batch["module"] == "workbook"
    assert batch["rows_total"] == 4
    assert batch["rows_ready"] == 4
    assert batch["rows_blocked"] == 0
    assert batch["targets"][0]["module"] == "journal"


def test_workbook_prepare_splits_parallel_cash_journal(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    data_dir = tmp_path / "storage"
    upload_dir.mkdir()
    data_dir.mkdir()
    upload_id = "cash-journal"
    file_path = upload_dir / f"{upload_id}.xlsx"

    df = pd.DataFrame({
        "日期": ["2026-01-06"],
        "收入金额": [635],
        "收入方式": ["现金"],
        "摘要说明": ["收款"],
        "日期.1": ["2026-01-06"],
        "支出金额": [426],
        "支出方式": ["现金"],
        "摘要说明.1": ["沙溪房租及水电费"],
        "备注信息": ["电：31774-31924"],
    })
    df.to_excel(file_path, index=False)

    monkeypatch.setattr(import_batch.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(import_batch.settings, "DATA_DIR", str(data_dir))

    batch = asyncio.run(import_batch.prepare_import(upload_id))

    assert batch["module"] == "workbook"
    assert batch["rows_total"] == 4
    assert [target["module"] for target in batch["targets"]] == ["journal", "finance"]
    assert batch["targets"][0]["records"][0]["income_amount"] == 635
    assert batch["targets"][0]["records"][1]["expense_amount"] == 426
    assert batch["display_records"][0]["收支"] == "收入"
    assert batch["display_records"][1]["收支"] == "支出"
