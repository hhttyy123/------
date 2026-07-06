"""上传相关 Pydantic 模型"""

from pydantic import BaseModel


class SheetInfo(BaseModel):
    name: str
    row_count: int
    column_count: int
    headers: list[str] = []


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    sheets: list[SheetInfo]
    sheet_count: int


class AnalyzeRequest(BaseModel):
    upload_id: str
    sheet_name: str
    header_row_index: int | None = None  # None = auto-detect
    sample_size: int = 10
