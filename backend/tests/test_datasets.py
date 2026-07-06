import pandas as pd

from app.services import datasets


def test_dataset_import_crud_query_and_export(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    storage_dir = tmp_path / "storage"
    upload_dir.mkdir()
    storage_dir.mkdir()
    monkeypatch.setattr(datasets.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(datasets.settings, "DATA_DIR", str(storage_dir))

    upload_id = "simple"
    file_path = upload_dir / f"{upload_id}.xlsx"
    pd.DataFrame({
        "日期": ["2026-01-01", "2026-01-02"],
        "收入金额": [100, 200],
        "摘要": ["A", "B"],
    }).to_excel(file_path, sheet_name="现金日记账", index=False)

    preview = datasets.preview_sheet(upload_id, "现金日记账")
    assert [column["key"] for column in preview["columns"]] == ["日期", "收入金额", "摘要"]

    dataset = datasets.create_dataset_from_sheet(upload_id, "现金日记账", name="现金")
    dataset_id = dataset["dataset_id"]
    assert len(dataset["rows"]) == 2

    created = datasets.create_row(dataset_id, {"日期": "2026-01-03", "收入金额": 300, "摘要": "C"})
    assert created["id"] == 3

    updated = datasets.update_row(dataset_id, 3, {"摘要": "C2"})
    assert updated["摘要"] == "C2"

    result = datasets.query_dataset(dataset_id, {
        "filters": [{"field": "收入金额", "operator": "gte", "value": 200}],
        "group_by": ["摘要"],
        "aggregations": [{"field": "收入金额", "type": "sum"}],
    })
    assert result["total"] == 2
    assert result["summary"]["收入金额"]["sum"] == 500

    csv_text = datasets.export_dataset_csv(dataset_id)
    assert "收入金额" in csv_text
    assert "C2" in csv_text

    assert datasets.delete_row(dataset_id, 3) is True
    assert datasets.delete_dataset(dataset_id) is True
