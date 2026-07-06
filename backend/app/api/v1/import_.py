"""导入 API"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas.import_ import ImportRequest, ImportResponse, ImportError, PrepareImportRequest
from app.services.import_batch import commit_batch, get_batch, prepare_import
from app.services.importer import run_import

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/import/prepare")
async def prepare(req: PrepareImportRequest):
    """自动整理 Excel 为待保存批次。"""
    try:
        return await prepare_import(req.upload_id, req.sheet_name, req.sample_size)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("import prepare failed")
        raise HTTPException(status_code=400, detail=f"整理失败: {str(e)}")


@router.get("/import/batches/{batch_id}")
async def get_import_batch(batch_id: str):
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    return batch


@router.post("/import/batches/{batch_id}/commit")
async def commit_import_batch(batch_id: str):
    try:
        return commit_batch(batch_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"保存失败: {str(e)}")


@router.post("/import", response_model=ImportResponse)
async def import_data(req: ImportRequest):
    """确认并执行数据导入"""
    file_path = Path(settings.UPLOAD_DIR) / f"{req.upload_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="上传文件不存在或已过期，请重新上传")

    try:
        result = await run_import(
            file_path=file_path,
            sheet_name=req.sheet_name,
            module_key=req.confirmed_module,
            confirmed_mappings=req.confirmed_mappings,
            header_row_index=req.header_row_index,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

    return ImportResponse(
        import_id=result["import_id"],
        module=result["module"],
        total_rows=result["total_rows"],
        imported_rows=result["imported_rows"],
        skipped_rows=result["skipped_rows"],
        error_rows=result["error_rows"],
        errors=[ImportError(**e) for e in result.get("errors", [])],
        summary=result.get("summary", {}),
    )
