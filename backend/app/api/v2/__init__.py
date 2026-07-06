from fastapi import APIRouter

from app.api.v2.imports import router as imports_router
from app.api.v2.journal import router as journal_router
from app.api.v2.companies import router as companies_router
from app.api.v2.employees import router as employees_router
from app.api.v2.attendance import router as attendance_router
from app.api.v2.finance import router as finance_router
from app.api.v2.maintenance import router as maintenance_router
from app.api.v2.dashboard import router as dashboard_router
from app.api.v2.reconciliation import router as reconciliation_router
from app.api.v2.overdue import router as overdue_router
from app.api.v2.approvals import router as approvals_router
from app.api.v2.advisor import router as advisor_router

router = APIRouter(prefix="/api/v2")
router.include_router(maintenance_router, prefix="/maintenance", tags=["v2-maintenance"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["v2-dashboard"])
router.include_router(reconciliation_router, prefix="/reconciliation", tags=["v2-reconciliation"])
router.include_router(overdue_router, prefix="/overdue", tags=["v2-overdue"])
router.include_router(approvals_router, prefix="/approvals", tags=["v2-approvals"])
router.include_router(advisor_router, prefix="/advisor", tags=["v2-advisor"])
router.include_router(imports_router, prefix="/imports", tags=["v2-imports"])
router.include_router(journal_router, prefix="/journal", tags=["v2-journal"])
router.include_router(companies_router, prefix="/companies", tags=["v2-companies"])
router.include_router(employees_router, prefix="/employees", tags=["v2-employees"])
router.include_router(attendance_router, prefix="/attendance", tags=["v2-attendance"])
router.include_router(finance_router, prefix="/finance", tags=["v2-finance"])
