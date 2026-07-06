"""Schema Registry 加载器 —— 汇总所有模块定义，构建别名索引"""

from app.registry.base import ModuleDef
from app.registry.employee import EMPLOYEE_MODULE
from app.registry.attendance import ATTENDANCE_MODULE
from app.registry.contract import CONTRACT_MODULE
from app.registry.company import COMPANY_MODULE
from app.registry.position import POSITION_MODULE
from app.registry.payroll import PAYROLL_MODULE
from app.registry.recruitment_fee import RECRUITMENT_FEE_MODULE
from app.registry.accounts_receivable import ACCOUNTS_RECEIVABLE_MODULE
from app.registry.invoice import INVOICE_MODULE
from app.registry.journal import JOURNAL_MODULE
from app.registry.finance import FINANCE_MODULE
from app.registry.profit import PROFIT_MODULE
from app.registry.approval import APPROVAL_MODULE
from app.registry.audit_log import AUDIT_LOG_MODULE

_registry: dict[str, ModuleDef] | None = None
_alias_index: dict[str, list[tuple[str, str]]] | None = None


def _normalize(s: str) -> str:
    """统一标准化字符串：去空格、小写，用于模糊匹配"""
    return s.strip().lower().replace(" ", "").replace("　", "").replace("\t", "")


def load_registry() -> dict[str, ModuleDef]:
    """加载所有模块定义，构建内存索引，应用启动时调用一次"""
    global _registry, _alias_index

    modules = [
        EMPLOYEE_MODULE,
        ATTENDANCE_MODULE,
        CONTRACT_MODULE,
        COMPANY_MODULE,
        POSITION_MODULE,
        PAYROLL_MODULE,
        RECRUITMENT_FEE_MODULE,
        ACCOUNTS_RECEIVABLE_MODULE,
        INVOICE_MODULE,
        JOURNAL_MODULE,
        FINANCE_MODULE,
        PROFIT_MODULE,
        APPROVAL_MODULE,
        AUDIT_LOG_MODULE,
    ]

    _registry = {}
    _alias_index = {}

    for mod in modules:
        _registry[mod.module_key] = mod
        for field in mod.fields:
            # 标准字段名本身也是可匹配的
            all_names = [field.field_key, field.field_label] + field.aliases
            for name in all_names:
                normalized = _normalize(name)
                if normalized not in _alias_index:
                    _alias_index[normalized] = []
                _alias_index[normalized].append((mod.module_key, field.field_key))

    return _registry


def get_registry() -> dict[str, ModuleDef]:
    """获取已加载的注册表（若未加载则自动加载）"""
    global _registry
    if _registry is None:
        load_registry()
    return _registry


def get_alias_index() -> dict[str, list[tuple[str, str]]]:
    """获取别名倒排索引"""
    global _alias_index
    if _alias_index is None:
        load_registry()
    return _alias_index


def get_module(module_key: str) -> ModuleDef | None:
    """按 key 获取单个模块定义"""
    return get_registry().get(module_key)


def search_alias(query: str, module_key: str | None = None) -> list[tuple[str, str, str]]:
    """
    模糊搜索别名，返回匹配的 [(module_key, field_key, field_label), ...]

    Args:
        query: 用户输入的列名
        module_key: 如果已知模块，可限定范围
    """
    normalized = _normalize(query)
    index = get_alias_index()
    results: list[tuple[str, str, str]] = []

    # 1. 精确匹配
    if normalized in index:
        for mod_key, field_key in index[normalized]:
            if module_key and mod_key != module_key:
                continue
            mod = get_module(mod_key)
            if mod:
                for f in mod.fields:
                    if f.field_key == field_key:
                        results.append((mod_key, field_key, f.field_label))
                        break

    # 2. 子串匹配（如果精确匹配不充分）
    if not results:
        for alias_key, entries in index.items():
            if normalized in alias_key or alias_key in normalized:
                for mod_key, field_key in entries:
                    if module_key and mod_key != module_key:
                        continue
                    mod = get_module(mod_key)
                    if mod:
                        for f in mod.fields:
                            if f.field_key == field_key:
                                results.append((mod_key, field_key, f.field_label))
                                break

    # 去重
    seen = set()
    unique_results = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique_results.append(r)
    return unique_results


def get_compact_field_list() -> str:
    """返回极简字段表（每模块一行），用于 AI prompt（~2000 字符）"""
    registry = get_registry()
    lines = []
    for mod_key, mod in registry.items():
        fields_str = " ".join(
            f"{f.field_key}({f.field_label})" for f in mod.fields
        )
        lines.append(f"{mod.module_label}({mod_key}): {fields_str}")
    return "\n".join(lines)
