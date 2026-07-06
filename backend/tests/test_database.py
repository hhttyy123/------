from sqlalchemy import create_engine, text

from app.database import database_status


def test_database_status_reports_database_without_exposing_url():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY)"))

    result = database_status(engine)

    assert result["status"] == "ok"
    assert result["database"] == ":memory:"
    assert result["table_count"] == 1
    assert "url" not in result
