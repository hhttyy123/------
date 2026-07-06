"""岗位管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

POSITION_MODULE = ModuleDef(
    module_key="position",
    module_label="岗位管理",
    description="为企业创建的招聘岗位，含岗位名称、日单价、需求人数、在岗人数等",
    identifying_fields=["daily_rate", "required_count", "position_name"],
    fields=[
        FieldDef(field_key="company_name", field_label="所属企业", field_type=FieldType.STRING, required=True,
                 aliases=["企业", "公司", "用工企业", "所属公司", "company", "enterprise"], max_length=100),
        FieldDef(field_key="name", field_label="岗位名称", field_type=FieldType.STRING, required=True,
                 aliases=["岗位", "职位", "工种", "岗位名", "position", "job", "post", "name"], max_length=100),
        FieldDef(field_key="description", field_label="岗位描述", field_type=FieldType.STRING, required=False,
                 aliases=["描述", "岗位说明", "工作内容", "description", "desc"], max_length=500),
        FieldDef(field_key="daily_rate", field_label="日单价", field_type=FieldType.DECIMAL, required=True,
                 aliases=["单价", "日工资", "日薪", "每日单价", "rate", "daily_rate", "daily_wage", "price"]),
        FieldDef(field_key="required_count", field_label="需求人数", field_type=FieldType.INTEGER, required=True,
                 aliases=["需求", "需要人数", "招聘人数", "人数", "count", "required", "headcount"]),
        FieldDef(field_key="status", field_label="岗位状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "招聘状态", "position_status", "status"],
                 enum_values=["招聘中", "已满", "已关闭"], default_value="招聘中"),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "备注信息", "remark", "note"], max_length=200),
    ],
)
