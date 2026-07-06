"""分析结果相关 Pydantic 模型"""

from pydantic import BaseModel


class Classification(BaseModel):
    module: str
    module_label: str
    confidence: float
    reasoning: str = ""
    alternative_modules: list[dict] = []


class FieldMapping(BaseModel):
    column_index: int
    original_header: str
    mapped_field: str | None = None
    field_label: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    suggested_alternatives: list[str] = []


class ValueSample(BaseModel):
    column_index: int
    field_key: str
    field_label: str = ""
    samples: list[dict] = []


class Warning(BaseModel):
    type: str
    message: str
    severity: str = "warning"
    details: str = ""


class AnalysisResponse(BaseModel):
    upload_id: str
    sheet_name: str
    classification: Classification
    header_row_index: int = 0
    field_mappings: list[FieldMapping]
    value_samples: list[ValueSample] = []
    warnings: list[Warning] = []
    preview_rows: list[dict] = []
