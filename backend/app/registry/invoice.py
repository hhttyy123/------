"""开票管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

INVOICE_MODULE = ModuleDef(
    module_key="invoice",
    module_label="开票管理",
    description="按企业记录开票信息，发票号唯一，可关联回款记录",
    identifying_fields=["invoice_no", "invoice_date"],
    fields=[
        FieldDef(field_key="company_name", field_label="企业名称", field_type=FieldType.STRING, required=True,
                 aliases=["企业", "公司", "开票企业", "客户", "company", "enterprise"], max_length=100),
        FieldDef(field_key="invoice_no", field_label="发票号", field_type=FieldType.STRING, required=True, unique=True,
                 aliases=["发票号码", "发票编号", "发票代码", "invoice", "invoice_no", "invoice_number"], max_length=50),
        FieldDef(field_key="invoice_date", field_label="开票日期", field_type=FieldType.DATE, required=True,
                 aliases=["日期", "开票时间", "发票日期", "date", "invoice_date", "billing_date"]),
        FieldDef(field_key="amount", field_label="金额", field_type=FieldType.DECIMAL, required=True,
                 aliases=["开票金额", "发票金额", "价税合计", "amount", "invoice_amount", "total"]),
        FieldDef(field_key="is_received", field_label="是否已回款", field_type=FieldType.BOOLEAN, required=False,
                 aliases=["回款", "已收款", "是否到账", "received", "is_paid"], default_value="否"),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "发票备注", "remark", "note"], max_length=300),
    ],
)
