"""企业管理模块"""

from app.registry.base import ModuleDef, FieldDef, FieldType

COMPANY_MODULE = ModuleDef(
    module_key="company",
    module_label="企业管理",
    description="合作用工企业的基本信息，含企业名称、联系人、资质、合作状态等",
    identifying_fields=["business_license", "cooperation_status", "contact_person"],
    fields=[
        FieldDef(field_key="name", field_label="企业名称", field_type=FieldType.STRING, required=True, unique=True,
                 aliases=["企业", "公司名称", "单位名称", "用工企业", "公司", "name", "company", "enterprise"], max_length=100),
        FieldDef(field_key="contact_person", field_label="联系人", field_type=FieldType.STRING, required=False,
                 aliases=["联系人姓名", "对接人", "负责人", "contact", "contact_person"], max_length=50),
        FieldDef(field_key="contact_phone", field_label="联系电话", field_type=FieldType.PHONE, required=False,
                 aliases=["手机", "电话", "联系方式", "手机号", "phone", "tel", "contact_phone"]),
        FieldDef(field_key="address", field_label="地址", field_type=FieldType.STRING, required=False,
                 aliases=["公司地址", "企业地址", "办公地址", "addr", "address"], max_length=200),
        FieldDef(field_key="business_license", field_label="营业执照号", field_type=FieldType.STRING, required=False,
                 aliases=["营业执照", "执照号", "工商注册号", "license", "business_license"], max_length=50),
        FieldDef(field_key="cooperation_status", field_label="合作状态", field_type=FieldType.ENUM, required=True,
                 aliases=["状态", "合作情况", "合作", "status", "cooperation"],
                 enum_values=["正常合作", "暂停合作", "终止合作"], default_value="正常合作"),
        FieldDef(field_key="cooperation_start_date", field_label="合作起始日期", field_type=FieldType.DATE, required=False,
                 aliases=["合作开始", "开始合作", "起始日期", "start", "cooperation_start"]),
        FieldDef(field_key="cooperation_end_date", field_label="合作截止日期", field_type=FieldType.DATE, required=False,
                 aliases=["合作结束", "终止日期", "截止日期", "end", "cooperation_end"]),
        FieldDef(field_key="remark", field_label="备注", field_type=FieldType.STRING, required=False,
                 aliases=["说明", "备注信息", "remark", "note"], max_length=200),
    ],
)
