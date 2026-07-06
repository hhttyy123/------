"""Schema Registry 核心数据结构"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    MONTH = "month"
    ENUM = "enum"
    BOOLEAN = "boolean"
    PHONE = "phone"
    ID_CARD = "id_card"
    PERCENT = "percent"


@dataclass
class FieldDef:
    """单个标准字段的定义"""
    field_key: str                          # snake_case, e.g. "name", "id_card_number"
    field_label: str                        # 中文显示名，e.g. "姓名"
    field_type: FieldType
    required: bool = False
    unique: bool = False
    aliases: list[str] = field(default_factory=list)    # 常见别名（含中英文、带空格等变体）
    enum_values: Optional[list[str]] = None             # ENUM 类型的可选值
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    regex_pattern: Optional[str] = None                  # 正则校验（phone/id_card 等）
    default_value: Optional[str] = None
    description: str = ""

    def to_dict(self) -> dict:
        result = {
            "field_key": self.field_key,
            "field_label": self.field_label,
            "field_type": self.field_type.value,
            "required": self.required,
            "unique": self.unique,
            "aliases": self.aliases,
            "description": self.description,
        }
        if self.enum_values:
            result["enum_values"] = self.enum_values
        return result


@dataclass
class ModuleDef:
    """单个业务模块的定义"""
    module_key: str                         # e.g. "employee", "payroll"
    module_label: str                       # e.g. "员工管理"
    description: str
    fields: list[FieldDef]
    identifying_fields: list[str] = field(default_factory=list)  # 用于 Agent 模块识别的特征字段

    def to_dict(self) -> dict:
        return {
            "module_key": self.module_key,
            "module_label": self.module_label,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "identifying_fields": self.identifying_fields,
        }
