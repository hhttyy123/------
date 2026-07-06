"""代招返费模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

RECRUITMENT_FEE_MODULE = ModuleDef(
    module_key="recruitment_fee",
    module_label="代招返费",
    description="为用工企业代招员工后企业支付的招聘服务费记录",
    identifying_fields=["person_count", "amount"],
    fields=[
        FieldDef(field_key="company_name", field_label="企业名称", field_type=FieldType.STRING, required=True,
                 aliases=["企业", "公司", "用工企业", "客户", "company", "enterprise", "client"], max_length=100),
        FieldDef(field_key="date", field_label="日期", field_type=FieldType.DATE, required=True,
                 aliases=["返费日期", "支付日期", "date", "fee_date", "payment_date"]),
        FieldDef(field_key="amount", field_label="金额", field_type=FieldType.DECIMAL, required=True,
                 aliases=["返费金额", "费用", "招聘费", "服务费", "amount", "fee", "money"]),
        FieldDef(field_key="person_count", field_label="涉及人数", field_type=FieldType.INTEGER, required=True,
                 aliases=["人数", "招聘人数", "推荐人数", "count", "person_count", "headcount", "people"]),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "备注信息", "remark", "note"], max_length=300),
    ],
)
