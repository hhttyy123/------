"""上传 API"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.schemas.upload import UploadResponse, SheetInfo
from app.services.excel_reader import save_upload

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传 Excel 文件，返回文件信息和工作表概览"""
    # 校验文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，仅支持 .xlsx 或 .xls")

    # 校验文件大小
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)")

    # 保存并分析
    try:
        info = save_upload(
            file_content=content,
            filename=file.filename,
            upload_dir=Path(settings.UPLOAD_DIR),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析 Excel 文件: {str(e)}")

    return UploadResponse(
        upload_id=info.upload_id,
        filename=info.filename,
        sheets=[
            SheetInfo(
                name=s.name,
                row_count=s.row_count,
                column_count=s.column_count,
                headers=s.headers,
            )
            for s in info.sheets
        ],
        sheet_count=info.sheet_count,
    )
