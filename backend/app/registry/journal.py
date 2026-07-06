"""Journal module schema."""

from app.registry.base import FieldDef, FieldType, ModuleDef


JOURNAL_MODULE = ModuleDef(
    module_key="journal",
    module_label="日记账",
    description="按日期记录资金进出明细，包括收入、支出、方式、摘要和来源。",
    identifying_fields=["date", "income_amount", "expense_amount"],
    fields=[
        FieldDef(
            field_key="date",
            field_label="日期",
            field_type=FieldType.DATE,
            required=True,
            aliases=["日期", "交易日期", "记账日期", "发生日期", "date", "tran_date", "transaction_date"],
        ),
        FieldDef(
            field_key="income_amount",
            field_label="收入金额",
            field_type=FieldType.DECIMAL,
            required=False,
            aliases=["收入", "收入金额", "收款金额", "进账金额", "借方金额", "income", "credit", "revenue", "in_amount"],
        ),
        FieldDef(
            field_key="income_method",
            field_label="收入方式",
            field_type=FieldType.STRING,
            required=False,
            aliases=["收入方式", "收款方式", "进账方式", "income_method", "payment_method_in"],
        ),
        FieldDef(
            field_key="expense_amount",
            field_label="支出金额",
            field_type=FieldType.DECIMAL,
            required=False,
            aliases=["支出", "支出金额", "付款金额", "出账金额", "贷方金额", "expense", "debit", "out_amount", "expenditure"],
        ),
        FieldDef(
            field_key="expense_method",
            field_label="支出方式",
            field_type=FieldType.STRING,
            required=False,
            aliases=["支出方式", "付款方式", "出账方式", "expense_method", "payment_method_out"],
        ),
        FieldDef(
            field_key="description",
            field_label="摘要/说明",
            field_type=FieldType.STRING,
            required=False,
            aliases=["摘要", "摘要说明", "说明", "备注", "用途", "事由", "description", "summary", "memo", "remark", "note"],
            max_length=500,
        ),
        FieldDef(
            field_key="source_type",
            field_label="来源类型",
            field_type=FieldType.ENUM,
            required=True,
            aliases=["来源", "来源类型", "数据来源", "业务类型", "source", "source_type", "entry_type", "category"],
            enum_values=["工资发放", "返费支出", "回款到账", "财务记录", "手动录入"],
            default_value="手动录入",
        ),
        FieldDef(
            field_key="source_id",
            field_label="来源记录ID",
            field_type=FieldType.STRING,
            required=False,
            aliases=["来源ID", "关联ID", "业务ID", "source_id", "ref_id", "related_id"],
        ),
        FieldDef(
            field_key="remark",
            field_label="备注",
            field_type=FieldType.STRING,
            required=False,
            aliases=["备注信息", "补充说明", "附注", "remark", "notes", "comments"],
            max_length=500,
        ),
    ],
)
