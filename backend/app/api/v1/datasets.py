"""Generic dataset APIs for simple Excel import and CRUD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.services.datasets import (
    create_dataset_from_sheet,
    create_workbook_dataset,
    create_row,
    delete_dataset,
    delete_row,
    export_dataset_csv,
    get_dataset,
    list_datasets,
    list_rows,
    preview_sheet,
    query_dataset,
    update_dataset_meta,
    update_row,
)

router = APIRouter()


class DatasetCreateRequest(BaseModel):
    upload_id: str
    sheet_name: str
    name: str | None = None
    header_row: int | None = None
    category: str | None = None


class DatasetPatchRequest(BaseModel):
    name: str | None = None
    category: str | None = None


class RowRequest(BaseModel):
    data: dict


class QueryRequest(BaseModel):
    filters: list[dict] = []
    group_by: list[str] = []
    aggregations: list[dict] = []
    limit: int = 500


@router.get("/simple-import/{upload_id}/sheets/{sheet_name}/preview")
async def simple_preview(
    upload_id: str,
    sheet_name: str,
    header_row: int | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    try:
        return preview_sheet(upload_id, sheet_name, header_row=header_row, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法预览工作表：{exc}")


@router.post("/datasets")
async def create_dataset(req: DatasetCreateRequest):
    try:
        return create_dataset_from_sheet(
            req.upload_id,
            req.sheet_name,
            name=req.name,
            header_row=req.header_row,
            category=req.category,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法保存数据集：{exc}")


class WorkbookCreateRequest(BaseModel):
    upload_id: str
    name: str
    category: str = "other"


@router.post("/datasets/from-workbook")
async def create_workbook(req: WorkbookCreateRequest):
    try:
        return create_workbook_dataset(req.upload_id, req.name, req.category)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法导入工作簿：{exc}")


@router.get("/datasets")
async def datasets():
    return {"datasets": list_datasets()}


@router.get("/datasets/{dataset_id}")
async def dataset_detail(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


@router.patch("/datasets/{dataset_id}")
async def patch_dataset(dataset_id: str, req: DatasetPatchRequest):
    dataset = update_dataset_meta(dataset_id, req.model_dump(exclude_none=True))
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


@router.delete("/datasets/{dataset_id}")
async def remove_dataset(dataset_id: str):
    if not delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="数据集不存在")
    return {"ok": True}


@router.get("/datasets/{dataset_id}/rows")
async def dataset_rows(
    dataset_id: str,
    search: str = "",
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    result = list_rows(dataset_id, search=search, limit=limit, offset=offset)
    if not result:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return result


@router.post("/datasets/{dataset_id}/rows")
async def add_row(dataset_id: str, req: RowRequest):
    row = create_row(dataset_id, req.data)
    if not row:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return row


@router.patch("/datasets/{dataset_id}/rows/{row_id}")
async def patch_row(dataset_id: str, row_id: int, req: RowRequest):
    row = update_row(dataset_id, row_id, req.data)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return row


@router.delete("/datasets/{dataset_id}/rows/{row_id}")
async def remove_row(dataset_id: str, row_id: int):
    if not delete_row(dataset_id, row_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


@router.post("/datasets/{dataset_id}/query")
async def dataset_query(dataset_id: str, req: QueryRequest):
    result = query_dataset(dataset_id, req.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return result


@router.get("/datasets/{dataset_id}/export")
async def dataset_export(dataset_id: str):
    csv_text = export_dataset_csv(dataset_id)
    if csv_text is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dataset_id}.csv"'},
    )
