"""Read-only smoke test against the configured PostgreSQL database."""
from app.api.v2.attendance import list_attendance
from app.api.v2.finance import listing
from app.database import SessionLocal, database_status
from app.services.company_db import list_companies, list_positions
from app.services.employee_db import list_contracts, list_employees
from app.services.journal_db import list_journal_transactions


def main():
    checks = {}
    with SessionLocal() as db:
        checks["database"] = database_status()["status"]
        checks["companies"] = list_companies(db)["total"]
        checks["positions"] = len(list_positions(db))
        checks["employees"] = list_employees(db)["total"]
        checks["contracts"] = len(list_contracts(db))
        checks["attendance"] = list_attendance(db=db)["total"]
        checks["journal"] = list_journal_transactions(db)["total"]
        for module in ("salary", "rebate", "invoice", "receivable", "payment"):
            checks[module] = listing(module, db)["total"]
    for name, result in checks.items():
        print(f"PASS {name}: {result}")


if __name__ == "__main__":
    main()
