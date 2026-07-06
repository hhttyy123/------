import asyncio
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1 import analyze as analyze_api
from app.api.v1 import import_ as import_api
from app.api.v1 import import_chat as import_chat_api
from app.api.auth import require_user
from app.main import app


def test_analyze_all_includes_header_row_index(monkeypatch, tmp_path):
    upload_id = "upload-1"
    upload_file = tmp_path / f"{upload_id}.xlsx"
    upload_file.write_bytes(b"placeholder")

    monkeypatch.setattr(analyze_api.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        analyze_api,
        "read_workbook_meta",
        lambda _path: [SimpleNamespace(name="现金日记账", row_count=10, column_count=4)],
        raising=False,
    )

    async def fake_run_analysis(_file_path, sheet_name, _sample_size):
        return {
            "classification": {"module": "journal", "module_label": "日记账", "confidence": 1.0},
            "header_row_index": 3,
            "field_mappings": [],
            "preview_rows": [],
            "total_rows": 0,
        }

    monkeypatch.setattr(analyze_api, "run_analysis", fake_run_analysis)

    response = asyncio.run(
        analyze_api.analyze_all(SimpleNamespace(upload_id=upload_id, sheet_name="", sample_size=10)),
    )

    assert response["results"][0]["header_row_index"] == 3


def test_import_data_returns_service_summary(monkeypatch, tmp_path):
    upload_id = "upload-2"
    upload_file = tmp_path / f"{upload_id}.xlsx"
    upload_file.write_bytes(b"placeholder")

    monkeypatch.setattr(import_api.settings, "UPLOAD_DIR", str(tmp_path))

    async def fake_run_import(**_kwargs):
        return {
            "import_id": "import-1",
            "module": "journal",
            "total_rows": 2,
            "imported_rows": 2,
            "skipped_rows": 0,
            "error_rows": 0,
            "errors": [],
            "summary": {"new_records": 2, "storage_file": str(Path("journal.json"))},
        }

    monkeypatch.setattr(import_api, "run_import", fake_run_import)

    response = asyncio.run(
        import_api.import_data(SimpleNamespace(
            upload_id=upload_id,
            sheet_name="现金日记账",
            confirmed_module="journal",
            confirmed_mappings=[],
            header_row_index=3,
        )),
    )

    assert response.module == "journal"
    assert response.imported_rows == 2
    assert response.summary["storage_file"] == "journal.json"


def test_import_chat_endpoint_calls_diagnosis_service(monkeypatch):
    async def fake_ask_import_question(batch_id, question, history):
        return {
            "batch_id": batch_id,
            "answer": f"checked: {question}",
            "context_scope": "test",
        }

    monkeypatch.setattr(import_chat_api, "ask_import_question", fake_ask_import_question)

    response = asyncio.run(
        import_chat_api.chat_with_import_batch(
            "batch-1",
            import_chat_api.ImportChatRequest(question="哪里不对？", history=[]),
        ),
    )

    assert response["batch_id"] == "batch-1"
    assert response["answer"] == "checked: 哪里不对？"


def test_import_chat_route_is_registered(monkeypatch):
    async def fake_ask_import_question(batch_id, question, history):
        return {
            "batch_id": batch_id,
            "answer": f"checked: {question}",
            "context_scope": "test",
        }

    monkeypatch.setattr(import_chat_api, "ask_import_question", fake_ask_import_question)

    app.dependency_overrides[require_user] = lambda: SimpleNamespace(id=1, status="active")
    client = TestClient(app)
    response = client.post(
        "/api/v1/import/batches/batch-1/chat",
        json={"question": "哪里不对？", "history": []},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "checked: 哪里不对？"
    app.dependency_overrides.pop(require_user, None)
