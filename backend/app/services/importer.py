"""数据导入器 —— JSON 文件存储版"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.registry.loader import get_module
from app.services.excel_reader import read_sheet_full
from app.services.value_converter import convert_value


async def run_import(
    file_path: Path,
    sheet_name: str,
    module_key: str,
    confirmed_mappings: list,
    header_row_index: int = 0,
) -> dict:
    """
    执行数据导入，写入 JSON 文件

    Returns:
        导入结果字典
    """
    import_id = uuid.uuid4().hex

    module_def = get_module(module_key)
    if not module_def:
        raise ValueError(f"未找到模块定义: {module_key}")

    # 1. 确保存储目录存在
    storage_dir = Path(settings.DATA_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    data_file = storage_dir / f"{module_key}.json"

    # 2. 读取已有数据（追加模式）
    existing_data: list[dict] = []
    if data_file.exists():
        try:
            existing_data = json.loads(data_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            existing_data = []

    # 3. 读取 Excel 完整数据
    df = read_sheet_full(file_path, sheet_name, header_row=header_row_index)
    total_rows = len(df)

    # 4. 构建列索引 -> 字段 key 映射
    col_to_field: dict[int, str] = {}
    for m in confirmed_mappings:
        if m.mapped_field:
            col_to_field[m.column_index] = m.mapped_field

    # 5. 获取字段类型信息
    field_types: dict[str, tuple] = {}
    for f in module_def.fields:
        field_types[f.field_key] = (f.field_type.value, f.enum_values)

    # 6. 逐行转换
    errors: list[dict] = []
    new_records: list[dict] = []
    columns = list(df.columns)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, row in df.iterrows():
        record: dict = {"id": len(existing_data) + len(new_records) + 1}
        row_errors: list[str] = []

        for col_idx, field_key in col_to_field.items():
            if col_idx >= len(columns):
                continue
            raw_value = row.iloc[col_idx]

            field_type_str, enum_values = field_types.get(field_key, ("string", None))
            converted, needs_review = convert_value(
                raw_value, field_type_str, field_key, enum_values,
            )

            if converted is None or (isinstance(converted, str) and not converted):
                # 检查是否必填
                field_def = None
                for f in module_def.fields:
                    if f.field_key == field_key:
                        field_def = f
                        break
                if field_def and field_def.required:
                    row_errors.append(f"必填字段「{field_def.field_label}」为空")

            record[field_key] = converted

        record["_imported_at"] = now

        if row_errors:
            errors.append({
                "row": int(idx) + header_row_index + 2,
                "message": "; ".join(row_errors),
                "data": {k: str(v) for k, v in record.items() if k != "_imported_at"},
            })
        else:
            new_records.append(record)

    # 7. 写入 JSON 文件
    all_data = existing_data + new_records
    data_file.write_text(
        json.dumps(all_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    imported = len(new_records)
    skipped = len(errors)

    # 8. 记录导入历史
    history_file = storage_dir / "_import_history.json"
    history: list[dict] = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

    history.append({
        "import_id": import_id,
        "filename": file_path.name,
        "module": module_key,
        "sheet": sheet_name,
        "total_rows": total_rows,
        "imported_rows": imported,
        "error_rows": skipped,
        "imported_at": now,
    })
    history_file.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "import_id": import_id,
        "module": module_key,
        "total_rows": total_rows,
        "imported_rows": imported,
        "skipped_rows": total_rows - imported - skipped,
        "error_rows": skipped,
        "errors": errors,
        "summary": {
            "new_records": imported,
            "validation_failures": skipped,
            "total_records": len(all_data),
            "storage_file": str(data_file),
        },
    }
