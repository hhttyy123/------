"""回款管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

ACCOUNTS_RECEIVABLE_MODULE = ModuleDef(
    module_key="accounts_receivable",
    module_label="回款管理",
    description="按企业记录回款情况，含预计/实际回款日期、金额、付款方式、逾期判定",
    identifying_fields=["expected_date", "payment_method", "actual_date"],
    fields=[
        FieldDef(field_key="company_name", field_label="企业名称", field_type=FieldType.STRING, required=True,
                 aliases=["企业", "公司", "用工企业", "客户", "回款企业", "company", "enterprise", "customer"], max_length=100),
        FieldDef(field_key="expected_date", field_label="预计回款日期", field_type=FieldType.DATE, required=True,
                 aliases=["预计日期", "应收日期", "预计回款", "计划回款日", "expected", "expected_date", "due_date"]),
        FieldDef(field_key="actual_date", field_label="实际回款日期", field_type=FieldType.DATE, required=False,
                 aliases=["实际日期", "到账日期", "实际回款", "actual", "received_date", "paid_date"]),
        FieldDef(field_key="amount", field_label="金额", field_type=FieldType.DECIMAL, required=True,
                 aliases=["回款金额", "应收金额", "到账金额", "amount", "money", "sum"]),
        FieldDef(field_key="payment_method", field_label="付款方式", field_type=FieldType.ENUM, required=True,
                 aliases=["方式", "付款", "回款方式", "到款方式", "method", "payment", "payment_method"],
                 enum_values=["直接给付", "银行承兑"]),
        FieldDef(field_key="acceptance_due_date", field_label="承兑到期日", field_type=FieldType.DATE, required=False,
                 aliases=["承兑日", "承兑到期", "汇票到期日", "acceptance", "draft_due_date"]),
        FieldDef(field_key="status", field_label="回款状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "收款状态", "回款情况", "status", "payment_status"],
                 enum_values=["待回款", "已到账", "已逾期"], default_value="待回款"),
        FieldDef(field_key="overdue_days", field_label="逾期天数", field_type=FieldType.INTEGER, required=False,
                 aliases=["逾期", "超期天数", "延迟天数", "overdue", "overdue_days", "delay_days"]),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "跟进备注", "催收记录", "remark", "note"], max_length=500),
    ],
)
