"""合同管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

CONTRACT_MODULE = ModuleDef(
    module_key="contract",
    module_label="合同管理",
    description="员工合同全生命周期管理，含签订、续签、终止，支持到期预警",
    identifying_fields=["contract_type", "sign_date", "end_date"],
    fields=[
        FieldDef(field_key="employee_name", field_label="员工姓名", field_type=FieldType.STRING, required=True,
                 aliases=["姓名", "员工", "名字", "name", "employee"], max_length=50),
        FieldDef(field_key="contract_type", field_label="合同类型", field_type=FieldType.ENUM, required=True,
                 aliases=["类型", "合同类别", "签订类型", "type", "contract_type"],
                 enum_values=["初始签订", "续签", "终止"]),
        FieldDef(field_key="sign_date", field_label="签订日期", field_type=FieldType.DATE, required=True,
                 aliases=["签订时间", "签定日期", "签署日期", "sign_date", "signed_date"]),
        FieldDef(field_key="start_date", field_label="合同起始日期", field_type=FieldType.DATE, required=True,
                 aliases=["起始日期", "开始日期", "生效日期", "start", "start_date", "effective_date"]),
        FieldDef(field_key="end_date", field_label="合同截止日期", field_type=FieldType.DATE, required=True,
                 aliases=["截止日期", "到期日期", "结束日期", "终止日期", "end", "end_date", "expiry_date"]),
        FieldDef(field_key="status", field_label="合同状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "合同当前状态", "contract_status", "status"],
                 enum_values=["生效中", "已到期", "已终止"]),
        FieldDef(field_key="file_path", field_label="合同文件", field_type=FieldType.STRING, required=False,
                 aliases=["附件", "扫描件", "合同附件", "文件", "file", "attachment"], max_length=500),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "合同备注", "remark", "note"], max_length=200),
    ],
)
