"""Finance record module schema."""

from app.registry.base import FieldDef, FieldType, ModuleDef


FINANCE_MODULE = ModuleDef(
    module_key="finance",
    module_label="财务记录",
    description="记录公司账户资金进出明细，包括日期、收支类型、类别、金额和备注。",
    identifying_fields=["type", "category", "amount"],
    fields=[
        FieldDef(
            field_key="date",
            field_label="日期",
            field_type=FieldType.DATE,
            required=True,
            aliases=["交易日期", "记账日期", "发生日期", "日期", "date", "tran_date"],
        ),
        FieldDef(
            field_key="type",
            field_label="类型",
            field_type=FieldType.ENUM,
            required=True,
            aliases=["收支类型", "交易类型", "财务类型", "收支", "类型", "type", "transaction_type"],
            enum_values=["收入", "支出"],
        ),
        FieldDef(
            field_key="category",
            field_label="类别",
            field_type=FieldType.ENUM,
            required=True,
            aliases=["费用类别", "收支类别", "分类", "类别", "category", "expense_type"],
            enum_values=["工资发放", "代招返费", "企业回款", "办公费用", "差旅费用", "其他"],
        ),
        FieldDef(
            field_key="amount",
            field_label="金额",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=["交易金额", "收支金额", "费用", "金额", "amount", "money"],
        ),
        FieldDef(
            field_key="company_name",
            field_label="所属企业",
            field_type=FieldType.STRING,
            required=False,
            aliases=["企业", "关联企业", "公司", "所属企业", "company", "related_company"],
            max_length=100,
        ),
        FieldDef(
            field_key="remark",
            field_label="备注",
            field_type=FieldType.STRING,
            required=False,
            aliases=["说明", "描述", "摘要", "备注", "remark", "note", "description"],
            max_length=300,
        ),
    ],
)
