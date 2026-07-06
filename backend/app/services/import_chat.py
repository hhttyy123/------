"""Import diagnosis chat powered by the same DeepSeek client used for analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.deepseek_client import get_client
from app.config import settings
from app.services.excel_reader import format_sheet_as_table, read_workbook_meta
from app.services.import_batch import get_batch


def compact_json(value: Any, limit: int = 12000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str, indent=2)
    return text[:limit] + "\n...(内容过长，已截断)" if len(text) > limit else text


def workbook_context(upload_id: str, max_sheets: int = 6, max_rows: int = 35) -> str:
    file_path = Path(settings.UPLOAD_DIR) / f"{upload_id}.xlsx"
    if not file_path.exists():
        return "未找到原始上传文件，以下只能基于整理批次回答。"

    parts = []
    for sheet in read_workbook_meta(file_path)[:max_sheets]:
        if sheet.row_count <= 0 or sheet.column_count <= 0:
            continue
        try:
            table = format_sheet_as_table(file_path, sheet.name, max_rows=max_rows)
        except Exception as exc:
            table = f"读取失败: {exc}"
        parts.append(
            f"工作表: {sheet.name}\n"
            f"尺寸: {sheet.row_count} 行 x {sheet.column_count} 列\n"
            f"原始抽样:\n{table}"
        )
    return "\n\n---\n\n".join(parts) if parts else "原始工作簿没有可读取的工作表。"


def batch_context(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "filename": batch.get("filename"),
        "status": batch.get("status"),
        "module": batch.get("module"),
        "module_label": batch.get("module_label"),
        "rows_total": batch.get("rows_total"),
        "rows_ready": batch.get("rows_ready"),
        "rows_blocked": batch.get("rows_blocked"),
        "cache_hit": batch.get("cache_hit"),
        "sheet_reports": batch.get("sheet_reports", [])[:20],
        "targets": [
            {
                "module": target.get("module"),
                "module_label": target.get("module_label"),
                "sheet_name": target.get("sheet_name"),
                "rows_total": target.get("rows_total"),
                "rows_ready": target.get("rows_ready"),
                "rows_blocked": target.get("rows_blocked"),
                "display_sample": target.get("display_records", [])[:20],
                "raw_record_sample": target.get("records", [])[:10],
            }
            for target in batch.get("targets", [])[:12]
        ],
        "display_sample": (batch.get("display_records") or batch.get("records") or [])[:40],
        "issues_sample": batch.get("issues", [])[:80],
        "debug_summary": {
            "source": (batch.get("_debug") or {}).get("source"),
            "sheets": (batch.get("_debug") or {}).get("sheets", [])[:10],
            "field_mappings": (batch.get("_debug") or {}).get("field_mappings", [])[:80],
        },
    }


async def ask_import_question(batch_id: str, question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    batch = get_batch(batch_id)
    if not batch:
        raise FileNotFoundError("导入批次不存在")

    question = question.strip()
    if not question:
        raise ValueError("问题不能为空")

    system = """你是劳务派遣管理系统的 Excel 导入诊断助手。
你的任务不是夸系统，而是帮助用户找出导入结果为什么不准确、哪些字段被误读、哪些 sheet/行可能被漏掉，以及下一步该怎么修。

回答规则：
- 用中文，直接、具体、面向业务人员。
- 必须区分“原始表格里看到的内容”和“系统整理后的结果”。
- 如果依据不足，明确说还缺什么，不要编造。
- 不展示置信度、字段映射 JSON、内部推理链。
- 可以指出系统当前处理逻辑的问题，例如：抽样不足、多 sheet 上下文不足、收入支出拆分规则有误、缓存命中导致沿用旧格式。
- 给出可执行建议，优先告诉用户要看哪张 sheet、哪几列、哪类行。"""

    context = {
        "整理批次": batch_context(batch),
        "原始工作簿抽样": workbook_context(str(batch.get("upload_id") or "")),
    }

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in (history or [])[-8:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:2000]})
    messages.append({
        "role": "user",
        "content": f"当前导入上下文如下：\n{compact_json(context, 22000)}\n\n用户问题：{question}",
    })

    client = get_client()
    resp = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        max_tokens=min(settings.DEEPSEEK_MAX_TOKENS, 2500),
        temperature=0.2,
        messages=messages,
    )
    answer = (resp.choices[0].message.content or "").strip()
    return {
        "answer": answer,
        "context_scope": "原始工作簿抽样 + 系统整理批次 + 异常摘要",
        "batch_id": batch_id,
    }
