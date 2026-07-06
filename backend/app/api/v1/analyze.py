"""分析 API"""

import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.schemas.upload import AnalyzeRequest
from app.schemas.analysis import AnalysisResponse, Classification, FieldMapping, ValueSample, Warning
from app.services.agent_pipeline import run_analysis
from app.services.excel_reader import read_workbook_meta

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_sheet(req: AnalyzeRequest):
    file_path = Path(settings.UPLOAD_DIR) / f"{req.upload_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="上传文件不存在")

    result = await run_analysis(file_path, req.sheet_name, req.sample_size)
    return AnalysisResponse(
        upload_id=req.upload_id, sheet_name=req.sheet_name,
        classification=Classification(**result["classification"]),
        header_row_index=result["header_row_index"],
        field_mappings=[FieldMapping(**fm) for fm in result["field_mappings"]],
        value_samples=[ValueSample(**vs) for vs in result.get("value_samples", [])],
        warnings=[Warning(**w) for w in result.get("warnings", [])],
        preview_rows=result.get("preview_rows", []),
    )


@router.post("/analyze-all")
async def analyze_all(req: AnalyzeRequest):
    file_path = Path(settings.UPLOAD_DIR) / f"{req.upload_id}.xlsx"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="上传文件不存在")

    sheets = [s for s in read_workbook_meta(file_path) if s.row_count > 0 and s.column_count > 0]

    async def analyze_one(sheet):
        try:
            r = await run_analysis(file_path, sheet.name, req.sample_size)
            return {"sheet_name": sheet.name, "classification": r["classification"],
                    "header_row_index": r["header_row_index"],
                    "field_mappings": r["field_mappings"], "preview_rows": r["preview_rows"],
                    "total_rows": r.get("total_rows", 0),
                    "_debug": r.get("_debug", {})}
        except Exception as e:
            return {"sheet_name": sheet.name, "error": str(e)}

    # 并行分析
    results = await asyncio.gather(*[analyze_one(s) for s in sheets])

    return {"upload_id": req.upload_id, "results": list(results)}
