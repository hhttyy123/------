from app.services.company_db import normalize_company_name
from app.services.staged_import import normalize_company_import_data


def test_normalize_company_name_ignores_spacing_and_brackets():
    assert normalize_company_name("苏州 曼克斯（有限公司）") == normalize_company_name("苏州曼克斯有限公司")


def test_company_import_normalizes_status_and_receivable_days():
    result = normalize_company_import_data({
        "name": " 测试企业 ",
        "cooperation_status": "正常合作",
        "default_receivable_days": "30",
    })
    assert result["name"] == "测试企业"
    assert result["cooperation_status"] == "active"
    assert result["default_receivable_days"] == 30
