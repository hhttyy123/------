"""确定性值转换器 —— 将 Excel 原始值转换为系统标准格式

Agent 负责"理解"（列名映射），转换器负责"执行"（确定性的值转换规则）。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from dateutil.parser import parse as parse_date


# ---- 枚举值映射表 ----

GENDER_VALUES = {
    # 男
    "男": "男", "男性": "男", "male": "男", "m": "男", "man": "男",
    "boy": "男", "1": "男", "先生": "男",
    # 女
    "女": "女", "女性": "女", "female": "女", "f": "女", "woman": "女",
    "girl": "女", "0": "女", "女士": "女",
}

STATUS_VALUES = {
    "在职": "在职", "在职员工": "在职", "在職": "在职", "active": "在职",
    "是": "在职", "1": "在职", "true": "在职", "yes": "在职",
    "离职": "离职", "已离职": "离职", "離職": "离职", "inactive": "离职",
    "否": "离职", "0": "离职", "false": "离职", "no": "离职",
}

BOOL_VALUES = {
    "是": True, "yes": True, "true": True, "1": True, "y": True, "✓": True, "√": True,
    "否": False, "no": False, "false": False, "0": False, "n": False, "✗": False, "×": False,
}

CONTRACT_TYPE_VALUES = {
    "初始签订": "初始签订", "签订": "初始签订", "新签": "初始签订", "new": "初始签订",
    "续签": "续签", "renew": "续签",
    "终止": "终止", "terminate": "终止", "结束": "终止", "end": "终止",
}

COOPERATION_STATUS_VALUES = {
    "正常合作": "正常合作", "合作中": "正常合作", "active": "正常合作",
    "暂停合作": "暂停合作", "暂停": "暂停合作", "suspended": "暂停合作",
    "终止合作": "终止合作", "终止": "终止合作", "已终止": "终止合作", "ended": "终止合作",
}

ATTENDANCE_STATUS_VALUES = {
    "正常出勤": "正常出勤", "出勤": "正常出勤", "正常": "正常出勤", "present": "正常出勤",
    "迟到": "迟到", "late": "迟到",
    "旷工": "旷工", "absent": "旷工",
    "请假": "请假", "leave": "请假", "休假": "请假",
}

PAYMENT_METHOD_VALUES = {
    "直接给付": "直接给付", "转账": "直接给付", "现金": "直接给付",
    "银行转账": "直接给付", "微信": "直接给付", "支付宝": "直接给付",
    "银行承兑": "银行承兑", "承兑": "银行承兑", "承兑汇票": "银行承兑",
}

SOURCE_TYPE_VALUES = {
    "工资发放": "工资发放", "工资": "工资发放", "发薪": "工资发放",
    "返费支出": "返费支出", "返费": "返費支出", "代招返费": "返费支出", "招聘费": "返费支出",
    "回款到账": "回款到账", "回款": "回款到账", "收款": "回款到账",
    "财务记录": "财务记录", "财务": "财务记录", "其他收支": "财务记录",
    "手动录入": "手动录入", "手动": "手动录入", "手工": "手动录入",
}


def convert_enum_value(raw_value: str, enum_values: list[str] | None = None, enum_type: str = "") -> tuple[str | None, bool]:
    """
    将原始值转换为标准枚举值

    Args:
        raw_value: 原始值字符串
        enum_values: 允许的标准值列表
        enum_type: 枚举类型（用于选择映射表）

    Returns:
        (converted_value, needs_review): 转换结果 + 是否需要人工确认
    """
    raw = str(raw_value).strip()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a"):
        return "", False

    # 先精确匹配标准值
    if enum_values:
        if raw in enum_values:
            return raw, False
        # 大小写不敏感的精确匹配
        for ev in enum_values:
            if ev.lower() == raw.lower():
                return ev, False

    # 根据类型选择映射表
    mapping: dict[str, Any] = {}
    if enum_type in ("gender", "性别"):
        mapping = GENDER_VALUES
    elif enum_type in ("status", "员工状态", "在职状态"):
        mapping = STATUS_VALUES
    elif enum_type in ("contract_type", "合同类型"):
        mapping = CONTRACT_TYPE_VALUES
    elif enum_type in ("cooperation_status", "合作状态"):
        mapping = COOPERATION_STATUS_VALUES
    elif enum_type in ("attendance_status", "出勤状态"):
        mapping = ATTENDANCE_STATUS_VALUES
    elif enum_type in ("payment_method", "付款方式", "回款方式"):
        mapping = PAYMENT_METHOD_VALUES
    elif enum_type in ("source_type", "来源类型"):
        mapping = SOURCE_TYPE_VALUES

    # 模糊匹配
    lower_raw = raw.lower().replace(" ", "").replace("　", "")
    for key, value in mapping.items():
        if key.lower().replace(" ", "").replace("　", "") == lower_raw:
            return value, False

    # 无法转换
    return raw, True


def convert_date_value(raw_value: Any) -> tuple[str | None, bool]:
    """将原始值转换为标准日期格式 YYYY-MM-DD

    支持从混合文本中提取日期，如 "3/11微信转账" → "2026-03-11"
    """
    # 处理 Excel datetime 对象
    if hasattr(raw_value, "strftime"):
        return raw_value.strftime("%Y-%m-%d"), False

    raw = str(raw_value).strip()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a", "/"):
        return "", False

    # 已经是标准格式
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw, False

    # 尝试直接解析
    try:
        dt = parse_date(raw, dayfirst=False)
        return dt.strftime("%Y-%m-%d"), False
    except Exception:
        pass

    # 尝试常见格式
    for fmt in [
        "%Y/%m/%d", "%Y.%m.%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y年%m月%d日", "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d"), False
        except ValueError:
            continue

    # 从混合文本中提取日期模式
    # "3/11微信转账" or "4/29於微信" → extract "3/11" or "4/29"
    date_match = re.search(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})", raw)
    if date_match:
        m, d = int(date_match.group(1)), int(date_match.group(2))
        if 1 <= m <= 12 and 1 <= d <= 31:
            year = datetime.now().year
            # 如果月份大于当前月份，可能是去年
            if m > datetime.now().month:
                year -= 1
            try:
                dt = datetime(year, m, d)
                return dt.strftime("%Y-%m-%d"), False
            except ValueError:
                pass

    # "2026-5-8开票" or "2026/5/8..." → extract date prefix
    date_match = re.match(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})", raw)
    if date_match:
        try:
            dt = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            return dt.strftime("%Y-%m-%d"), False
        except ValueError:
            pass

    # "25年12月转" or "25年12月..." → extract
    date_match = re.search(r"(\d{2})\s*年\s*(\d{1,2})\s*月", raw)
    if date_match:
        try:
            y = 2000 + int(date_match.group(1))
            m = int(date_match.group(2))
            dt = datetime(y, m, 1)
            return dt.strftime("%Y-%m-%d"), False
        except ValueError:
            pass

    # "1月20日" or "3/11" → extract month+day, assume current year
    date_match = re.match(r"^(\d{1,2})\s*月\s*(\d{1,2})\s*日?$", raw)
    if date_match:
        try:
            m, d = int(date_match.group(1)), int(date_match.group(2))
            year = datetime.now().year
            dt = datetime(year, m, d)
            return dt.strftime("%Y-%m-%d"), False
        except ValueError:
            pass

    return raw, True


def convert_month_value(raw_value: Any) -> tuple[str | None, bool]:
    """将原始值转换为标准月份格式 YYYY-MM"""
    raw = str(raw_value).strip()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a"):
        return "", False

    # 已经是标准格式
    if re.match(r"^\d{4}-\d{2}$", raw):
        return raw, False

    try:
        if hasattr(raw_value, "strftime"):
            return raw_value.strftime("%Y-%m"), False
        dt = parse_date(raw, dayfirst=False)
        return dt.strftime("%Y-%m"), False
    except Exception:
        for fmt in ["%Y/%m", "%Y.%m", "%Y年%m月", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.strftime("%Y-%m"), False
            except ValueError:
                continue
        return raw, True


def convert_phone_value(raw_value: Any) -> tuple[str | None, bool]:
    """转换为标准手机号格式（11位纯数字）"""
    raw = str(raw_value).strip()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a"):
        return "", False

    # 处理科学计数法
    if "e" in raw.lower() or "E" in raw:
        try:
            raw = f"{float(raw):.0f}"
        except ValueError:
            pass

    digits = re.sub(r"\D", "", raw)

    # 11 位数字，1 开头
    if len(digits) == 11 and digits.startswith("1"):
        return digits, False
    # 有些导出可能前面多了 86
    if len(digits) == 13 and digits.startswith("86") and digits[2] == "1":
        return digits[2:], False

    return raw, True


def convert_id_card_value(raw_value: Any) -> tuple[str | None, bool]:
    """转换为标准身份证号格式（18位，末位可为 X）"""
    raw = str(raw_value).strip().upper()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a"):
        return "", False

    # 处理科学计数法
    if "e" in raw.lower() or "E" in raw:
        try:
            raw = f"{float(raw):.0f}"
        except ValueError:
            pass

    cleaned = raw.strip().upper().replace(" ", "")
    if re.match(r"^\d{17}[\dX]$", cleaned):
        return cleaned, False

    # 尝试从含有多余字符的字符串中提取
    digits_match = re.search(r"(\d{17}[\dXx])", raw)
    if digits_match:
        return digits_match.group(1).upper(), False

    return raw, True


def convert_decimal_value(raw_value: Any) -> tuple[float | None, bool]:
    """转换为金额数值（返回 float，后续入库时转为分）"""
    raw = str(raw_value).strip()
    if not raw or raw.lower() in ("none", "null", "nan", "", "#n/a"):
        return 0.0, False

    if isinstance(raw_value, (int, float)):
        return float(raw_value), False

    # 去除常见符号
    cleaned = raw.replace(",", "").replace("，", "").replace("￥", "").replace("$", "").replace("¥", "").replace("元", "").replace(" ", "")
    try:
        return float(cleaned), False
    except ValueError:
        return None, True


def convert_value(
    raw_value: Any,
    field_type: str,
    field_label: str = "",
    enum_values: list[str] | None = None,
) -> tuple[Any, bool]:
    """
    统一入口：根据字段类型转换值

    Returns:
        (converted_value, needs_review): 转换结果 + 是否需要人工确认
    """
    if raw_value is None:
        return "", False

    raw_str = str(raw_value).strip()
    if not raw_str or raw_str.lower() in ("none", "null", "nan", "", "#n/a"):
        return "", False

    if field_type in ("enum",):
        return convert_enum_value(raw_str, enum_values, field_label)
    elif field_type in ("date",):
        return convert_date_value(raw_value)
    elif field_type in ("month",):
        return convert_month_value(raw_value)
    elif field_type in ("phone",):
        return convert_phone_value(raw_value)
    elif field_type in ("id_card",):
        return convert_id_card_value(raw_value)
    elif field_type in ("decimal", "integer"):
        return convert_decimal_value(raw_value)
    elif field_type in ("string",):
        return raw_str, False
    elif field_type in ("boolean",):
        lower = raw_str.lower().replace(" ", "")
        if lower in BOOL_VALUES:
            return BOOL_VALUES[lower], False
        return raw_str, True
    else:
        return raw_str, False
