"""Agent 管道 —— 原始表格文本直接发给 AI"""

from __future__ import annotations

import json
from pathlib import Path

from app.agents.deepseek_client import get_client
from app.config import settings
from app.registry.loader import get_compact_field_list, get_module
from app.services.excel_reader import format_sheet_as_table, read_sheet_full, detect_header_row
from app.services.value_converter import convert_value

client = get_client()


async def run_analysis(file_path: Path, sheet_name: str, sample_size: int = 50) -> dict:
    """分析单个 Sheet：发原始表格文本给 AI，一次调用搞定"""

    # 1. 读前 50 行格式化成文本表格
    table_text = format_sheet_as_table(file_path, sheet_name, max_rows=sample_size)

    # 2. 读全部数据（用于后续转换）
    header_row = detect_header_row(file_path, sheet_name, scan_rows=10)
    full_df = read_sheet_full(file_path, sheet_name, header_row=header_row)

    # 3. 构建 prompt
    field_list = get_compact_field_list()

    system = f"""你是表格数据分析专家。根据表格的列名和数据值，判断每一列对应哪个标准字段。

标准字段列表（每模块一行）:
{field_list}

规则:
- 综合列名语义和数据值特征判断。例如: 列名"实发数"+全是数字→net_pay；列名不明但数据全是"男/女"→gender
- 看到人名不要直接判断为员工模块，要看其他列是否匹配员工特征
- 每列必须给出确定映射，并在reasoning字段说明判断依据（根据什么列名、什么数据特征做出的判断）
- 返回JSON格式: {{"mappings":[{{"col":列索引(0起),"field":"字段key","reasoning":"判断依据"}}]}}
- 忽略空列
"""

    user = f"""工作表: {sheet_name}

{table_text}

请分析以上表格，返回每列对应的标准字段。只返回JSON。"""

    # 4. 调 AI
    resp = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        max_tokens=settings.DEEPSEEK_MAX_TOKENS,
        temperature=settings.DEEPSEEK_TEMPERATURE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )

    # 5. 解析结果
    raw_response = (resp.choices[0].message.content or "").strip()
    usage = resp.usage
    content = raw_response
    if "```" in content:
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        ai_data = json.loads(content)
        ai_mappings = ai_data if isinstance(ai_data, list) else ai_data.get("mappings", [])
    except json.JSONDecodeError:
        ai_mappings = []

    if not ai_mappings:
        raise RuntimeError(f"AI 未返回有效映射结果。AI 返回内容: {raw_response[:500]}")

    # 6. 确定模块
    from app.registry.loader import get_registry
    registry = get_registry()
    field_to_module: dict[str, str] = {}
    for mk, mod in registry.items():
        for f in mod.fields:
            field_to_module[f.field_key] = mk

    module_votes: dict[str, int] = {}
    for m in ai_mappings:
        fk = m.get("field", "")
        mk = field_to_module.get(fk, "")
        if mk:
            module_votes[mk] = module_votes.get(mk, 0) + 1

    module_key = max(module_votes, key=module_votes.get) if module_votes else ""
    module = get_module(module_key)

    # 7. 按模块全字段展开
    field_mappings = []
    ai_map = {m.get("col", m.get("column_index", -1)): m.get("field", "") for m in ai_mappings}

    if module:
        headers = list(full_df.columns)
        for field in module.fields:
            col_idx = -1
            for c, fk in ai_map.items():
                if fk == field.field_key:
                    col_idx = c
                    break
            field_mappings.append({
                "column_index": col_idx,
                "original_header": str(headers[col_idx]).strip() if 0 <= col_idx < len(headers) else "",
                "mapped_field": field.field_key,
                "field_label": field.field_label,
                "confidence": 1.0 if col_idx >= 0 else 0,
                "reasoning": "AI 映射" if col_idx >= 0 else "Excel 中无此列",
            })
    else:
        headers = list(full_df.columns)
        for m in ai_mappings:
            ci = m.get("col", m.get("column_index", 0))
            field_mappings.append({
                "column_index": ci,
                "original_header": str(headers[ci]).strip() if ci < len(headers) else "",
                "mapped_field": m.get("field", ""),
                "field_label": m.get("field", ""),
                "confidence": 1.0,
                "reasoning": "AI 映射",
            })

    # 8. 读全部数据，用映射转换
    all_rows = _convert_all(full_df, field_mappings, module)

    mod_label = module.module_label if module else ""
    return {
        "classification": {"module": module_key, "module_label": mod_label, "confidence": 1.0, "reasoning": f"AI 分析完成，识别 {len(ai_mappings)} 列"},
        "header_row_index": header_row,
        "field_mappings": field_mappings,
        "value_samples": [],
        "warnings": [],
        "preview_rows": all_rows,
        "total_rows": len(all_rows),
        "_debug": {
            "module": module_key,
            "columns_mapped": len(ai_mappings),
            "total_rows": len(all_rows),
            "ai_request": {
                "system_prompt": system,
                "user_message": user,
                "token_usage": {"prompt": usage.prompt_tokens if usage else 0, "completion": usage.completion_tokens if usage else 0, "total": usage.total_tokens if usage else 0},
            },
            "ai_response": {
                "raw": raw_response,
                "parsed_mappings": ai_mappings,
            },
        },
    }


def _convert_all(df, field_mappings, module):
    col_to_field = {m["column_index"]: m["mapped_field"] for m in field_mappings if m["column_index"] >= 0}
    columns = list(df.columns)
    rows = []
    for _, row in df.iterrows():
        pr = {m["mapped_field"]: "待填写" for m in field_mappings}
        for ci, fk in col_to_field.items():
            if ci < len(columns):
                v = row.iloc[ci]
                if v is not None and str(v).strip() and str(v).strip().lower() not in ("none", "null", "nan", ""):
                    field_def = next((f for f in (module.fields if module else []) if f.field_key == fk), None)
                    ft = field_def.field_type.value if field_def else "string"
                    ev = field_def.enum_values if field_def else None
                    cv, _ = convert_value(v, ft, field_def.field_label if field_def else "", ev)
                    pr[fk] = cv if cv is not None else str(v).strip()
        rows.append(pr)
    return rows
