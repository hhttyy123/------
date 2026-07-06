"""Module metadata, generic records, dashboard, warnings, and profit APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.registry.loader import get_module
from app.services.business import (
    calculate_profit,
    clear_test_records,
    create_business_record,
    dashboard_summary,
    delete_business_record,
    generate_warnings,
    list_module_records,
    module_payloads,
    repo,
    save_profit,
    schema_payload,
    update_business_record,
)

router = APIRouter()


class RecordRequest(BaseModel):
    data: dict


@router.get("/modules")
async def list_modules():
    return {"modules": module_payloads()}


@router.post("/maintenance/clear-records")
async def clear_records():
    return clear_test_records()


@router.get("/modules/{module}/schema")
async def get_schema(module: str):
    schema = schema_payload(module)
    if not schema:
        raise HTTPException(status_code=404, detail="模块不存在")
    return schema


@router.get("/modules/{module}/records")
async def list_records(module: str, search: str = "", limit: int = Query(200, ge=1, le=1000)):
    if not get_module(module):
        raise HTTPException(status_code=404, detail="模块不存在")
    return {"module": module, "records": list_module_records(module, search=search, limit=limit)}


@router.get("/modules/{module}/records/{record_id}")
async def get_record(module: str, record_id: int):
    if not get_module(module):
        raise HTTPException(status_code=404, detail="模块不存在")
    record = repo.get_record(module, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.post("/modules/{module}/records")
async def create_record(module: str, req: RecordRequest):
    if not get_module(module):
        raise HTTPException(status_code=404, detail="模块不存在")
    return create_business_record(module, req.data)


@router.patch("/modules/{module}/records/{record_id}")
async def update_record(module: str, record_id: int, req: RecordRequest):
    if not get_module(module):
        raise HTTPException(status_code=404, detail="模块不存在")
    record = update_business_record(module, record_id, req.data)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record


@router.delete("/modules/{module}/records/{record_id}")
async def delete_record(module: str, record_id: int):
    if not get_module(module):
        raise HTTPException(status_code=404, detail="模块不存在")
    if not delete_business_record(module, record_id):
        raise HTTPException(status_code=403, detail="该模块记录暂不支持删除或记录不存在")
    return {"ok": True}


@router.get("/dashboard/summary")
async def dashboard():
    return dashboard_summary()


@router.get("/warnings")
async def warnings():
    return {"warnings": generate_warnings()}


@router.get("/profit/calculate")
async def profit_calculate(month: str | None = None):
    return calculate_profit(month)


@router.post("/profit/calculate")
async def profit_save(month: str | None = None):
    return save_profit(month)
