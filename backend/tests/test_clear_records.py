from app.services import business
from app.services.repository import JsonRepository


def test_clear_test_records_clears_modules_and_import_artifacts(monkeypatch, tmp_path):
    storage = tmp_path / "storage"
    repository = JsonRepository(storage)
    monkeypatch.setattr(business, "repo", repository)
    monkeypatch.setattr(business.settings, "DATA_DIR", str(storage))

    repository.create_record("journal", {"date": "2026-01-01", "income_amount": 1})
    repository.create_record("finance", {"date": "2026-01-01", "type": "收入", "amount": 1})
    (storage / "_import_history.json").write_text("[{}]", encoding="utf-8")
    (storage / "_fingerprint_cache.json").write_text('{"x": 1}', encoding="utf-8")
    batch_dir = storage / "_import_batches"
    batch_dir.mkdir()
    (batch_dir / "batch.json").write_text("{}", encoding="utf-8")

    result = business.clear_test_records()

    assert result["ok"] is True
    assert "journal" in result["cleared_modules"]
    assert repository.list_records("journal") == []
    assert repository.list_records("finance") == []
    assert (storage / "_import_history.json").read_text(encoding="utf-8") == "[]"
    assert (storage / "_fingerprint_cache.json").read_text(encoding="utf-8") == "{}"
    assert list(batch_dir.glob("*.json")) == []
