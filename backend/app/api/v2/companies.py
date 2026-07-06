from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.company_db import (
    create_company, create_position, delete_company, delete_position, export_companies_excel,
    list_companies, list_positions, update_company, update_position,
)

router = APIRouter()


class CompanyWrite(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    contact_person: str | None = Field(default=None, max_length=80)
    contact_phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    business_license_no: str | None = Field(default=None, max_length=80)
    cooperation_status: str = Field(default="active", pattern="^(active|paused|terminated)$")
    cooperation_start_date: date | None = None
    cooperation_end_date: date | None = None
    default_receivable_days: int | None = Field(default=None, ge=0)
    remark: str | None = None


class CompanyPatch(CompanyWrite):
    name: str | None = Field(default=None, min_length=1, max_length=150)

    @model_validator(mode="after")
    def non_empty(self):
        if not self.model_fields_set: raise ValueError("至少提供一个修改字段")
        return self


class PositionWrite(BaseModel):
    company_id: int
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    daily_rate: float | None = Field(default=None, ge=0)
    required_count: int | None = Field(default=None, ge=0)
    status: str = Field(default="recruiting", pattern="^(recruiting|filled|closed)$")


class PositionPatch(PositionWrite):
    company_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


@router.get("")
def companies(search: str = "", status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_companies(db, search, status, page, page_size)


@router.post("")
def company_create(payload: CompanyWrite, db: Session = Depends(get_db)):
    try:
        result = create_company(db, payload.model_dump()); db.commit(); return result
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{company_id}")
def company_update(company_id: int, payload: CompanyPatch, db: Session = Depends(get_db)):
    try: result = update_company(db, company_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None: raise HTTPException(status_code=404, detail="企业不存在")
    return result


@router.delete("/{company_id}")
def company_delete(company_id: int, db: Session = Depends(get_db)):
    if not delete_company(db, company_id): raise HTTPException(status_code=404, detail="企业不存在")
    return {"ok": True}


@router.get("/export/file.xlsx")
def company_export(db: Session = Depends(get_db)):
    return StreamingResponse(export_companies_excel(db), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="companies.xlsx"'})


@router.get("/positions/list")
def positions(company_id: int | None = None, db: Session = Depends(get_db)):
    return {"rows": list_positions(db, company_id)}


@router.post("/positions")
def position_create(payload: PositionWrite, db: Session = Depends(get_db)):
    try: return create_position(db, payload.model_dump())
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/positions/{position_id}")
def position_update(position_id: int, payload: PositionPatch, db: Session = Depends(get_db)):
    result = update_position(db, position_id, payload.model_dump(exclude_unset=True))
    if result is None: raise HTTPException(status_code=404, detail="岗位不存在")
    return result


@router.delete("/positions/{position_id}")
def position_delete(position_id: int, db: Session = Depends(get_db)):
    if not delete_position(db, position_id): raise HTTPException(status_code=404, detail="岗位不存在")
    return {"ok": True}

@router.get("/positions/export/file.xlsx")
def positions_export(db: Session = Depends(get_db)):
    from io import BytesIO
    from openpyxl import Workbook
    rows = list_positions(db)
    wb = Workbook(); ws = wb.active; ws.title = "岗位"
    ws.append(["所属企业", "岗位名称", "日单价", "需求人数", "状态", "描述"])
    for r in rows["rows"]:
        ws.append([r["company_name"], r["name"], r["daily_rate"], r["required_count"], r["status"], r["description"]])
    stream = BytesIO(); wb.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": 'attachment; filename="positions.xlsx"'})
