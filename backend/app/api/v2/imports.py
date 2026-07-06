from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.staged_import import commit_staged_attendance, commit_staged_companies, commit_staged_contracts, commit_staged_employees, commit_staged_journal, commit_staged_positions, get_staged_batch, stage_attendance_import, stage_company_import, stage_contract_import, stage_employee_import, stage_journal_import, stage_journal_workbook_import, stage_position_import

router = APIRouter()


class StageJournalRequest(BaseModel):
    upload_id: str = Field(min_length=1, max_length=64)
    sheet_name: str = Field(min_length=1, max_length=160)
    header_row: int | None = Field(default=None, ge=0)


StageCompanyRequest = StageJournalRequest
StageEmployeeRequest = StageJournalRequest


@router.post("/journal/stage")
def stage_journal(request: StageJournalRequest, db: Session = Depends(get_db)):
    try:
        return stage_journal_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="数据库暂不可用") from exc


@router.post("/company/stage")
def stage_company(request: StageCompanyRequest, db: Session = Depends(get_db)):
    try: return stage_company_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/employee/stage")
def stage_employee(request: StageEmployeeRequest, db: Session = Depends(get_db)):
    try: return stage_employee_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/batches/{batch_id}")
def staged_batch(batch_id: int, include_rows: bool = Query(True), db: Session = Depends(get_db)):
    try:
        return get_staged_batch(db, batch_id, include_rows)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/commit")
def commit_journal(batch_id: int, db: Session = Depends(get_db)):
    try:
        return commit_staged_journal(db, batch_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="数据库提交失败") from exc


@router.post("/batches/{batch_id}/commit-companies")
def commit_companies(batch_id: int, db: Session = Depends(get_db)):
    try: return commit_staged_companies(db, batch_id)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/commit-employees")
def commit_employees(batch_id: int, db: Session = Depends(get_db)):
    try: return commit_staged_employees(db, batch_id)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/position/stage")
def stage_position(request: StageJournalRequest, db: Session = Depends(get_db)):
    try: return stage_position_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/commit-positions")
def commit_positions(batch_id: int, db: Session = Depends(get_db)):
    try: return commit_staged_positions(db, batch_id)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/contract/stage")
def stage_contract(request: StageJournalRequest, db: Session = Depends(get_db)):
    try: return stage_contract_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/commit-contracts")
def commit_contracts(batch_id: int, db: Session = Depends(get_db)):
    try: return commit_staged_contracts(db, batch_id)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


class WorkbookRequest(BaseModel):
    upload_id: str = Field(min_length=1, max_length=64)

@router.post("/journal/stage-workbook")
def stage_journal_workbook(request: WorkbookRequest, db: Session = Depends(get_db)):
    try: return stage_journal_workbook_import(db, request.upload_id)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/attendance/stage")
def stage_attendance(request: StageJournalRequest, db: Session = Depends(get_db)):
    try: return stage_attendance_import(db, request.upload_id, request.sheet_name, request.header_row)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/commit-attendance")
def commit_attendance(batch_id: int, db: Session = Depends(get_db)):
    try: return commit_staged_attendance(db, batch_id)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
