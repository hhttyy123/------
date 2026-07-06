"""考勤管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

ATTENDANCE_MODULE = ModuleDef(
    module_key="attendance",
    module_label="考勤管理",
    description="逐条记录员工每日出勤情况，含出勤日期、状态、工时，异常出勤自动关联工资扣款",
    identifying_fields=["attendance_date", "status", "hours"],
    fields=[
        FieldDef(field_key="employee_name", field_label="员工姓名", field_type=FieldType.STRING, required=True,
                 aliases=["姓名", "名字", "员工", "姓名(中文)", "name", "employee", "worker_name"], max_length=50),
        FieldDef(field_key="attendance_date", field_label="出勤日期", field_type=FieldType.DATE, required=True,
                 aliases=["日期", "考勤日期", "出勤日", "上班日期", "date", "attendance_date", "work_date"]),
        FieldDef(field_key="status", field_label="出勤状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "出勤", "考勤状态", "打卡状态", "attendance_status", "status"],
                 enum_values=["正常出勤", "迟到", "旷工", "请假"]),
        FieldDef(field_key="hours", field_label="工时", field_type=FieldType.DECIMAL, required=True,
                 aliases=["工时(h)", "出勤工时", "工作时长", "小时", "work_hours", "hours", "duration"]),
        FieldDef(field_key="is_abnormal", field_label="是否异常", field_type=FieldType.BOOLEAN, required=False,
                 aliases=["异常", "是否异常出勤", "异常标记", "abnormal", "is_abnormal"], default_value="否"),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "考勤备注", "备注信息", "remark", "note"], max_length=200),
    ],
)
