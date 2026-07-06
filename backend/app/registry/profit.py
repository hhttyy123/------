"""利润核算模块 - Schema 定义"""

from app.registry.base import ModuleDef, FieldDef, FieldType

PROFIT_MODULE = ModuleDef(
    module_key="profit",
    module_label="利润核算",
    description="月度利润核算，汇总收入与各项支出，计算净利润",
    identifying_fields=["month", "total_income", "net_profit"],
    fields=[
        FieldDef(
            field_key="month",
            field_label="月份",
            field_type=FieldType.MONTH,
            required=True,
            aliases=[
                "月份", "核算月份", "统计月份", "所属月份", "月  份",
                "month", "period", "year_month",
            ],
            description="核算月份（YYYY-MM）",
        ),
        FieldDef(
            field_key="total_income",
            field_label="总收入",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=[
                "收入", "总收入", "收入总额", "回款收入", "收入合计",
                "income", "total_income", "revenue", "total_revenue",
            ],
            description="当月回款到账总额（单位：元）",
        ),
        FieldDef(
            field_key="salary_expense",
            field_label="工资支出",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=[
                "工资", "工资支出", "工资总额", "人工成本", "发薪总额",
                "salary", "salary_expense", "payroll_expense", "labor_cost",
            ],
            description="当月已发放工资总额（单位：元）",
        ),
        FieldDef(
            field_key="recruitment_fee_expense",
            field_label="返费支出",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=[
                "返费", "代招返费", "返费支出", "招聘返费", "返费总额",
                "recruitment_fee", "fee_expense", "hiring_fee",
            ],
            description="当月返费支出总额（单位：元）",
        ),
        FieldDef(
            field_key="other_expense",
            field_label="其他支出",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=[
                "其他支出", "其它支出", "其他费用", "其他成本",
                "other", "other_expense", "misc_expense", "other_cost",
            ],
            description="当月其他财务支出总额（单位：元）",
        ),
        FieldDef(
            field_key="net_profit",
            field_label="净利润",
            field_type=FieldType.DECIMAL,
            required=True,
            aliases=[
                "净利润", "净利", "利润", "纯利润",
                "profit", "net_profit", "net_income",
            ],
            description="净利润 = 收入 - 工资支出 - 返费支出 - 其他支出",
        ),
        FieldDef(
            field_key="remark",
            field_label="备注",
            field_type=FieldType.STRING,
            required=False,
            aliases=[
                "备注", "说明", "核算说明",
                "remark", "note", "memo",
            ],
            max_length=500,
            description="备注信息",
        ),
    ],
)
