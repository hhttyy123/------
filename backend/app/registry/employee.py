"""员工管理模块 - Schema 定义"""

from app.registry.base import ModuleDef, FieldDef, FieldType

EMPLOYEE_MODULE = ModuleDef(
    module_key="employee",
    module_label="员工管理",
    description="派遣员工的基本信息，含姓名、身份证号、手机号、性别、地址、入职日期、所属企业、岗位等",
    identifying_fields=["id_card_number", "phone", "entry_date"],
    fields=[
        FieldDef(
            field_key="name",
            field_label="姓名",
            field_type=FieldType.STRING,
            required=True,
            aliases=[
                "名字", "员工姓名", "姓  名", "姓名(中文)", "姓 名",
                "employee_name", "full_name", "worker_name",
            ],
            max_length=50,
            description="员工中文姓名",
        ),
        FieldDef(
            field_key="id_card_number",
            field_label="身份证号",
            field_type=FieldType.ID_CARD,
            required=True,
            unique=True,
            aliases=[
                "身份证", "身份证号码", "证件号", "居民身份证", "证件号码",
                "ID Card", "id_no", "identity_card", "id_card",
            ],
            regex_pattern=r"^\d{17}[\dXx]$",
            description="18 位身份证号码",
        ),
        FieldDef(
            field_key="phone",
            field_label="手机号",
            field_type=FieldType.PHONE,
            required=True,
            aliases=[
                "手机", "联系电话", "电话", "手机号码", "电话号", "电话号码",
                "mobile", "phone_number", "tel", "cellphone",
            ],
            regex_pattern=r"^1\d{10}$",
            description="11 位手机号码",
        ),
        FieldDef(
            field_key="gender",
            field_label="性别",
            field_type=FieldType.ENUM,
            required=True,
            aliases=[
                "性  别", "男/女", "男女", "性别(男/女)", "性别（男/女）",
                "sex", "gender_type", "gender",
            ],
            enum_values=["男", "女"],
            description="性别：男 或 女",
        ),
        FieldDef(
            field_key="address",
            field_label="地址",
            field_type=FieldType.STRING,
            required=False,
            aliases=[
                "住址", "家庭地址", "现住址", "联系地址", "居住地址", "户籍地址",
                "addr", "home_address", "address",
            ],
            max_length=200,
            description="现住地址",
        ),
        FieldDef(
            field_key="entry_date",
            field_label="入职日期",
            field_type=FieldType.DATE,
            required=True,
            aliases=[
                "入职时间", "到岗日期", "进厂日期", "进厂时间", "入职日",
                "entry", "start_date", "hire_date", "onboard_date",
            ],
            description="员工入职日期（YYYY-MM-DD）",
        ),
        FieldDef(
            field_key="status",
            field_label="在职状态",
            field_type=FieldType.ENUM,
            required=True,
            aliases=[
                "员工状态", "状态", "在职/离职", "是否在职", "在职情况",
                "employment_status", "is_active", "status",
            ],
            enum_values=["在职", "离职"],
            default_value="在职",
            description="员工当前在职状态",
        ),
        FieldDef(
            field_key="company_name",
            field_label="所属企业",
            field_type=FieldType.STRING,
            required=True,
            aliases=[
                "企业", "用工单位", "派遣企业", "公司", "用人单位", "用工企业",
                "company", "enterprise", "employer", "company_name",
            ],
            description="派遣员工所属的用工企业名称",
        ),
        FieldDef(
            field_key="position_name",
            field_label="所在岗位",
            field_type=FieldType.STRING,
            required=True,
            aliases=[
                "岗位", "职位", "工种", "岗位名称", "工作岗位",
                "job", "position", "post", "job_title",
            ],
            description="员工所在岗位名称",
        ),
    ],
)
