"""预览 API —— 返回原始数据供前端渲染"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.services.excel_reader import read_sheet_sample, read_workbook_meta, detect_header_row

router = APIRouter()


@router.get("/preview/{upload_id}")
async def preview_sheet(
    upload_id: str,
    sheet_name: str = Query(..., description="工作表名称"),
    rows: int = Query(50, description="返回行数"),
):
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="上传文件不存在或已过期")

    try:
        # 自动检测表头行
        header_row = detect_header_row(file_path, sheet_name, scan_rows=10)
        headers, samples = read_sheet_sample(file_path, sheet_name, header_row=header_row, sample_size=rows)

        sheets = read_workbook_meta(file_path)
        total_rows = 0
        for s in sheets:
            if s.name == sheet_name:
                total_rows = s.row_count
                break

        return {
            "upload_id": upload_id,
            "sheet_name": sheet_name,
            "headers": headers,
            "rows": [[str(row.get(h, "")) for h in headers] for row in samples],
            "total_rows": total_rows,
            "preview_rows": len(samples),
            "header_row": header_row,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
