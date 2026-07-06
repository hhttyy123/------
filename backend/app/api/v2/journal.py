from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.journal_db import (
    create_journal_transaction,
    export_journal_excel,
    list_journal_transactions,
    update_journal_transaction,
    void_journal_transaction,
)

router = APIRouter()


class JournalWrite(BaseModel):
    transaction_date: date
    ledger_type: str = Field(pattern="^(cash|bank)$")
    direction: str = Field(pattern="^(income|expense)$")
    category: str = Field(default="other", min_length=1, max_length=40)
    amount: float = Field(gt=0)
    payment_method: str | None = Field(default=None, max_length=50)
    company_id: int | None = None
    employee_id: int | None = None
    summary: str | None = Field(default=None, max_length=500)


class JournalPatch(BaseModel):
    transaction_date: date | None = None
    ledger_type: str | None = Field(default=None, pattern="^(cash|bank)$")
    direction: str | None = Field(default=None, pattern="^(income|expense)$")
    category: str | None = Field(default=None, min_length=1, max_length=40)
    amount: float | None = Field(default=None, gt=0)
    payment_method: str | None = Field(default=None, max_length=50)
    company_id: int | None = None
    employee_id: int | None = None
    summary: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def ensure_non_empty(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个修改字段")
        return self


@router.get("")
def journal_list(
    direction: str | None = Query(default=None, pattern="^(income|expense)$"),
    ledger_type: str | None = Query(default=None, pattern="^(cash|bank)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_journal_transactions(db, direction=direction, ledger_type=ledger_type, date_from=date_from, date_to=date_to, search=search, page=page, page_size=page_size)


@router.post("")
def journal_create(payload: JournalWrite, db: Session = Depends(get_db)):
    return create_journal_transaction(db, payload.model_dump())


@router.patch("/{transaction_id}")
def journal_update(transaction_id: int, payload: JournalPatch, db: Session = Depends(get_db)):
    row = update_journal_transaction(db, transaction_id, payload.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail="日记账记录不存在")
    return row


@router.delete("/{transaction_id}")
def journal_delete(transaction_id: int, db: Session = Depends(get_db)):
    if not void_journal_transaction(db, transaction_id):
        raise HTTPException(status_code=404, detail="日记账记录不存在")
    return {"ok": True}


@router.get("/export/file.xlsx")
def journal_export(
    direction: str | None = Query(default=None, pattern="^(income|expense)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    search: str = "",
    db: Session = Depends(get_db),
):
    stream = export_journal_excel(db, direction=direction, date_from=date_from, date_to=date_to, search=search)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="日记账.xlsx"'},
    )
