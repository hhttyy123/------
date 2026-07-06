"""Excel 文件读取层 —— pandas/openpyxl 封装

处理：多 Sheet、合并单元格、多行表头、编码问题
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class SheetInfo:
    name: str
    row_count: int
    column_count: int
    headers: list[str] = field(default_factory=list)


@dataclass
class ExcelFileInfo:
    upload_id: str
    filename: str
    file_path: Path
    sheets: list[SheetInfo]
    sheet_count: int


def save_upload(file_content: bytes, filename: str, upload_dir: Path) -> ExcelFileInfo:
    """保存上传文件并返回文件信息"""
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex
    file_path = upload_dir / f"{upload_id}.xlsx"
    file_path.write_bytes(file_content)

    sheets = read_workbook_meta(file_path)

    return ExcelFileInfo(
        upload_id=upload_id,
        filename=filename,
        file_path=file_path,
        sheets=sheets,
        sheet_count=len(sheets),
    )


def read_workbook_meta(file_path: Path) -> list[SheetInfo]:
    """读取工作簿元信息（Sheet 名称、行列数、表头），不加载全部数据"""
    sheets = []
    try:
        xls = pd.ExcelFile(file_path, engine="openpyxl")
    except Exception:
        # 尝试 xls 格式
        xls = pd.ExcelFile(file_path, engine="xlrd")

    for name in xls.sheet_names:
        try:
            # 读第一行获取列名（nrows=1，不是0）
            df = pd.read_excel(xls, sheet_name=name, nrows=1)
            # 读取行数
            full_df = pd.read_excel(xls, sheet_name=name, usecols=[0])
            row_count = len(full_df)
            sheets.append(SheetInfo(
                name=name,
                row_count=row_count,
                column_count=len(df.columns),
                headers=[str(h).strip() for h in df.columns],
            ))
        except Exception:
            sheets.append(SheetInfo(
                name=name,
                row_count=0,
                column_count=0,
                headers=[],
            ))

    return sheets


def read_sheet_sample(
    file_path: Path,
    sheet_name: str,
    header_row: int = 0,
    sample_size: int = 10,
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    读取指定 Sheet 的表头和样本数据行

    处理合并单元格：fillna(method='ffill') 向下填充
    处理空行空列：自动剔除

    Args:
        file_path: Excel 文件路径
        sheet_name: 工作表名称
        header_row: 表头所在行（0-based）
        sample_size: 返回的样本行数

    Returns:
        (headers, sample_rows) — headers 是清洗后的表头列表，sample_rows 是字典列表
    """
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl",
    )

    # 清洗
    df = _clean_dataframe(df)

    headers = [str(h).strip() for h in df.columns]

    # 取样本行
    sample_df = df.head(sample_size)
    sample_rows = sample_df.to_dict(orient="records")

    # 确保所有值可 JSON 序列化
    clean_rows = []
    for row in sample_rows:
        clean_row = {}
        for k, v in row.items():
            k_str = str(k).strip()
            if pd.isna(v):
                clean_row[k_str] = ""
            elif isinstance(v, (int, float)):
                # 保留整数不转小数
                if isinstance(v, float) and v == int(v):
                    clean_row[k_str] = int(v)
                else:
                    clean_row[k_str] = v
            else:
                clean_row[k_str] = str(v).strip()
        clean_rows.append(clean_row)

    return headers, clean_rows


def read_sheet_full(
    file_path: Path,
    sheet_name: str,
    header_row: int = 0,
    fill_merged: bool = True,
) -> pd.DataFrame:
    """读取整个 Sheet 的完整数据（用于导入）"""
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl",
    )
    return _clean_dataframe(df, fill_merged=fill_merged)


def read_sheet_headers_scan(
    file_path: Path,
    sheet_name: str,
    scan_rows: int = 10,
) -> list[tuple[int, list[str], int]]:
    """
    扫描前 N 行，推测表头位置

    返回：[（行索引, 该行的列名列表, 非空列数）, ...]
    由 Agent 或用户选择最可能的一行作为表头
    """
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=None,
        nrows=scan_rows,
        engine="openpyxl",
    )

    candidates = []
    for idx, row in df.iterrows():
        values = [str(v).strip() for v in row if pd.notna(v) and str(v).strip()]
        content_count = len(values)
        candidates.append((idx, values, content_count))

    return candidates


def detect_header_row(
    file_path: Path,
    sheet_name: str,
    scan_rows: int = 10,
) -> int:
    """自动推测表头所在行（0-based）

    策略：找非空列数最多的一行作为表头
    """
    candidates = read_sheet_headers_scan(file_path, sheet_name, scan_rows)
    if not candidates:
        return 0
    # 选非空列数最多的一行
    best = max(candidates, key=lambda x: x[2])
    return best[0]


def _clean_dataframe(df: pd.DataFrame, fill_merged: bool = True) -> pd.DataFrame:
    """清洗 DataFrame：去全空行列、前向填充合并单元格、统一列名"""
    # 去除全空行
    df = df.dropna(how="all")
    # 去除全空列
    df = df.dropna(axis=1, how="all")
    # 填充合并单元格（向下填充）。并排流水表不能填充，否则会把上一笔收入复制到下面的支出行。
    if fill_merged:
        df = df.ffill()
    # 重置索引
    df = df.reset_index(drop=True)
    return df


def format_sheet_as_table(file_path: Path, sheet_name: str, max_rows: int = 50) -> str:
    """将 Excel 前 max_rows 行格式化为对齐文本表格，直接发给 AI 阅读"""
    import openpyxl

    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb[sheet_name]

    rows_data = []
    for row in ws.iter_rows(max_row=max_rows, values_only=True):
        vals = [str(v).strip() if v is not None else "" for v in row]
        if any(v for v in vals):
            rows_data.append(vals)

    wb.close()
    if not rows_data:
        return ""

    # 补齐到相同列数
    col_count = max(len(r) for r in rows_data)
    for r in rows_data:
        r.extend([""] * (col_count - len(r)))

    # 去掉全空列
    non_empty_cols = [
        i for i in range(col_count)
        if any(r[i] for r in rows_data)
    ]
    rows_data = [[r[i] for i in non_empty_cols] for r in rows_data]
    col_count = len(non_empty_cols)
    if col_count == 0:
        return ""

    # 计算列宽，限制最大宽度
    col_widths = [0] * col_count
    for row in rows_data:
        for i, cell in enumerate(row):
            col_widths[i] = min(max(col_widths[i], _display_width(str(cell))), 24)

    # 格式化
    lines = []
    for row in rows_data:
        cells = []
        for i, cell in enumerate(row):
            s = str(cell)
            if _display_width(s) > col_widths[i]:
                truncated = ""
                w = 0
                for ch in s:
                    cw = 2 if '一' <= ch <= '鿿' else 1
                    if w + cw > col_widths[i] - 1:
                        truncated += "…"
                        break
                    truncated += ch
                    w += cw
                s = truncated
            pad = col_widths[i] - _display_width(s)
            cells.append(" " + s + " " * pad)
        # 跳过全空行（第二次检查，因为截断后可能还有）
        if any(c.strip() for c in cells):
            lines.append("|".join(cells))

    return "\n".join(lines)



def _display_width(s: str) -> int:
    """计算字符串显示宽度（中文字符占2位）"""
    w = 0
    for ch in str(s):
        w += 2 if '一' <= ch <= '鿿' or '　' <= ch <= '〿' or '＀' <= ch <= '￯' else 1
    return w


def cleanup_upload(file_path: Path) -> None:
    """删除临时上传文件"""
    if file_path.exists():
        file_path.unlink()
