"""工资发放模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

PAYROLL_MODULE = ModuleDef(
    module_key="payroll",
    module_label="工资发放",
    description="按员工、按月份录入工资发放记录，工资构成拆分为基本工资+津贴-扣款=实发金额",
    identifying_fields=["month", "base_salary", "net_pay", "deduction"],
    fields=[
        FieldDef(field_key="employee_name", field_label="员工姓名", field_type=FieldType.STRING, required=True,
                 aliases=["姓名", "员工", "名字", "name", "employee", "worker"], max_length=50),
        FieldDef(field_key="month", field_label="月份", field_type=FieldType.MONTH, required=True,
                 aliases=["工资月份", "所属月份", "发放月份", "month", "period", "salary_month"]),
        FieldDef(field_key="base_salary", field_label="基本工资", field_type=FieldType.DECIMAL, required=True,
                 aliases=["基本", "底薪", "基础工资", "base", "base_salary", "basic_wage"]),
        FieldDef(field_key="allowance", field_label="津贴", field_type=FieldType.DECIMAL, required=False,
                 aliases=["补贴", "补助", "津贴补助", "allowance", "subsidy", "bonus"]),
        FieldDef(field_key="deduction", field_label="扣款", field_type=FieldType.DECIMAL, required=False,
                 aliases=["扣", "扣款金额", "罚款", "扣除", "deduction", "penalty", "fine"]),
        FieldDef(field_key="net_pay", field_label="实发金额", field_type=FieldType.DECIMAL, required=True,
                 aliases=["实发", "实发工资", "到手金额", "净发", "net", "net_pay", "take_home", "actual_pay"]),
        FieldDef(field_key="status", field_label="发放状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "工资状态", "是否发放", "pay_status", "status"],
                 enum_values=["待发放", "已发放"], default_value="待发放"),
        FieldDef(field_key="issued_at", field_label="发放日期", field_type=FieldType.DATE, required=False,
                 aliases=["发放时间", "到账日期", "issued", "pay_date", "paid_at"]),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "工资备注", "remark", "note"], max_length=200),
    ],
)
