"""操作日志模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

AUDIT_LOG_MODULE = ModuleDef(
    module_key="audit_log",
    module_label="操作日志",
    description="自动记录所有关键操作：谁、什么时间、在哪个模块、做了什么，不可删除",
    identifying_fields=["operator", "module", "action_type"],
    fields=[
        FieldDef(field_key="operator", field_label="操作人", field_type=FieldType.STRING, required=True,
                 aliases=["用户", "操作者", "操作员", "operator", "user", "username"]),
        FieldDef(field_key="operation_time", field_label="操作时间", field_type=FieldType.DATE, required=True,
                 aliases=["时间", "操作日期", "记录时间", "time", "timestamp", "created_at"]),
        FieldDef(field_key="module", field_label="操作模块", field_type=FieldType.STRING, required=True,
                 aliases=["模块", "功能模块", "所属功能", "module", "feature"]),
        FieldDef(field_key="action_type", field_label="操作类型", field_type=FieldType.ENUM, required=True,
                 aliases=["类型", "操作", "动作", "action", "type", "action_type"],
                 enum_values=["新增", "编辑", "删除", "导出", "导入"]),
        FieldDef(field_key="description", field_label="操作描述", field_type=FieldType.STRING, required=False,
                 aliases=["描述", "说明", "详情", "description", "detail"], max_length=500),
        FieldDef(field_key="ip_address", field_label="IP地址", field_type=FieldType.STRING, required=False,
                 aliases=["IP", "登录IP", "操作IP", "ip", "ip_address"]),
        FieldDef(field_key="is_sensitive", field_label="是否敏感操作", field_type=FieldType.BOOLEAN, required=False,
                 aliases=["敏感", "重要操作", "敏感标记", "sensitive", "is_sensitive"], default_value="否"),
    ],
)
