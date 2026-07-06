"""导入相关 Pydantic 模型"""

from pydantic import BaseModel


class ConfirmedMapping(BaseModel):
    column_index: int
    mapped_field: str | None = None  # null = skip


class ImportRequest(BaseModel):
    upload_id: str
    sheet_name: str
    confirmed_module: str
    confirmed_mappings: list[ConfirmedMapping]
    header_row_index: int = 0


class PrepareImportRequest(BaseModel):
    upload_id: str
    sheet_name: str | None = None
    sample_size: int = 10


class ImportError(BaseModel):
    row: int
    message: str
    data: dict = {}


class ImportResponse(BaseModel):
    import_id: str
    module: str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    error_rows: int
    errors: list[ImportError] = []
    summary: dict = {}
