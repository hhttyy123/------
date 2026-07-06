"""审批流程 + 操作日志模块（轻量，合并定义）"""

from app.registry.base import ModuleDef, FieldDef, FieldType

APPROVAL_MODULE = ModuleDef(
    module_key="approval",
    module_label="审批流程",
    description="三级审批链：员工录入→财务审核→老板确认，每次审批记录审批人和时间",
    identifying_fields=["submitter", "reviewer", "approver", "status"],
    fields=[
        FieldDef(field_key="module", field_label="所属模块", field_type=FieldType.STRING, required=True,
                 aliases=["业务模块", "模块", "来源模块", "module", "source_module"]),
        FieldDef(field_key="data_id", field_label="数据ID", field_type=FieldType.STRING, required=True,
                 aliases=["记录ID", "业务ID", "关联ID", "data_id", "record_id"]),
        FieldDef(field_key="submitter", field_label="提交人", field_type=FieldType.STRING, required=True,
                 aliases=["录入人", "发起人", "申请人", "submitter", "creator"]),
        FieldDef(field_key="reviewer", field_label="审核人", field_type=FieldType.STRING, required=False,
                 aliases=["财务审核", "审核", "reviewer", "checked_by"]),
        FieldDef(field_key="approver", field_label="审批人", field_type=FieldType.STRING, required=False,
                 aliases=["老板确认", "最终审批", "审批", "approver", "confirmed_by"]),
        FieldDef(field_key="status", field_label="审批状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "审批进度", "approval_status", "status"],
                 enum_values=["待审核", "待审批", "已通过", "已驳回"], default_value="待审核"),
        FieldDef(field_key="submit_time", field_label="提交时间", field_type=FieldType.DATE, required=True,
                 aliases=["录入时间", "发起时间", "submit_time", "created_at"]),
        FieldDef(field_key="review_time", field_label="审核时间", field_type=FieldType.DATE, required=False,
                 aliases=["财务审核时间", "review_time", "checked_at"]),
        FieldDef(field_key="approve_time", field_label="审批时间", field_type=FieldType.DATE, required=False,
                 aliases=["老板审批时间", "确认时间", "approve_time", "confirmed_at"]),
        FieldDef(field_key="review_comment", field_label="审核意见", field_type=FieldType.STRING, required=False,
                 aliases=["财务意见", "审核备注", "review_comment"], max_length=500),
        FieldDef(field_key="approve_comment", field_label="审批意见", field_type=FieldType.STRING, required=False,
                 aliases=["老板意见", "审批备注", "approve_comment"], max_length=500),
    ],
)
