from app.services.repository import JsonRepository


def test_repository_create_many_writes_once(monkeypatch, tmp_path):
    repository = JsonRepository(tmp_path)
    write_count = 0
    original_write = repository.write_records

    def counted_write(module, records):
        nonlocal write_count
        write_count += 1
        original_write(module, records)

    monkeypatch.setattr(repository, "write_records", counted_write)

    created = repository.create_many("journal", [{"date": "2026-01-01"} for _ in range(1000)])

    assert len(created) == 1000
    assert created[0]["id"] == 1
    assert created[-1]["id"] == 1000
    assert write_count == 1
