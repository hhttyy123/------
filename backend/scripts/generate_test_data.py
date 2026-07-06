"""Generate comprehensive test data Excel files for all modules."""
import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "test_excels"
OUT.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ====== Master data ======
COMPANIES = [
    ("苏州曼克斯人力资源服务有限公司", "张总", "13812345001", "苏州工业园区星湖街328号", "91320594MA1XXXXX1", "active", "2024-01-01", "2027-12-31"),
    ("常州东辉金属制品有限公司", "李经理", "13912345002", "常州市武进区遥观镇", "91320412MA1XXXXX2", "active", "2024-03-15", "2026-09-30"),
    ("无锡温静电梯工程有限公司", "王总", "13712345003", "无锡市滨湖区蠡园开发区", "91320211MA1XXXXX3", "active", "2023-06-01", "2026-06-01"),
    ("上海九金机械制造有限公司", "陈经理", "13612345004", "上海市嘉定区安亭镇", "91310114MA1XXXXX4", "active", "2024-05-01", "2027-05-01"),
    ("昆山联翔佳瑞电子有限公司", "赵总", "13512345005", "昆山市玉山镇", "91320583MA1XXXXX5", "paused", "2022-01-01", "2025-12-31"),
]

POSITIONS = [
    ("苏州曼克斯人力资源服务有限公司", [("普工", 180), ("操作工", 200), ("质检员", 220), ("班组长", 260)]),
    ("常州东辉金属制品有限公司", [("冲压工", 190), ("焊接工", 210), ("打磨工", 180)]),
    ("无锡温静电梯工程有限公司", [("安装工", 250), ("维保工", 230), ("电工", 240)]),
    ("上海九金机械制造有限公司", [("车工", 220), ("铣工", 230), ("钳工", 210), ("质检", 200)]),
    ("昆山联翔佳瑞电子有限公司", [("组装工", 170), ("测试工", 190), ("包装工", 160)]),
]

EMPLOYEES_RAW = [
    ("张三", "320501199001010011", "13900001001", "male", "苏州工业园区斜塘", "苏州曼克斯人力资源服务有限公司", "普工", "2025-03-15"),
    ("李四", "320502199205150022", "13900001002", "female", "苏州吴中区木渎", "苏州曼克斯人力资源服务有限公司", "质检员", "2025-04-01"),
    ("王五", "320503198812200033", "13900001003", "male", "苏州相城区黄埭", "苏州曼克斯人力资源服务有限公司", "操作工", "2025-06-01"),
    ("赵六", "320504199508080044", "13900001004", "female", "常州市武进区", "常州东辉金属制品有限公司", "冲压工", "2025-03-20"),
    ("孙七", "320505199703150055", "13900001005", "male", "无锡市滨湖区", "无锡温静电梯工程有限公司", "安装工", "2025-05-10"),
    ("周八", "320506199911220066", "13900001006", "male", "上海市嘉定区", "上海九金机械制造有限公司", "车工", "2025-04-15"),
    ("吴九", "320507199303180077", "13900001007", "female", "昆山市玉山镇", "昆山联翔佳瑞电子有限公司", "组装工", "2025-02-01"),
    ("郑十", "320508199707250088", "13900001008", "male", "苏州吴江区", "苏州曼克斯人力资源服务有限公司", "普工", "2025-07-01"),  # >20 days no contract
    ("陈十一", "320509198505300099", "13900001009", "male", "常州市新北区", "常州东辉金属制品有限公司", "焊接工", "2025-06-15"),  # >20 days no contract
    ("刘十二", "320510200003120010", "13900001010", "female", "苏州市姑苏区", "苏州曼克斯人力资源服务有限公司", "班组长", "2025-01-10"),
    ("黄十三", "320511199604280011", "13900001011", "male", "无锡市新吴区", "无锡温静电梯工程有限公司", "电工", "2025-03-01"),
    ("林十四", "320512199810050012", "13900001012", "female", "上海市松江区", "上海九金机械制造有限公司", "质检", "2025-05-20"),
]

CONTRACTS_RAW = [
    ("张三", "CT2025-001", "2025-03-15", "2025-03-15", "2026-03-14"),
    ("李四", "CT2025-002", "2025-04-01", "2025-04-01", "2026-03-31"),
    ("王五", "CT2025-003", "2025-06-01", "2025-06-01", "2026-05-31"),
    ("赵六", "CT2025-004", "2025-03-20", "2025-03-20", "2026-03-19"),
    ("孙七", "CT2025-005", "2025-05-10", "2025-05-10", "2026-05-09"),
    ("周八", "CT2025-006", "2025-04-15", "2025-04-15", "2025-07-25"),  # will expire soon
    ("吴九", "CT2025-007", "2025-02-01", "2025-02-01", "2025-07-20"),  # will expire soon
    ("刘十二", "CT2025-008", "2025-01-10", "2025-01-10", "2026-07-15"),  # about to expire
    ("黄十三", "CT2025-009", "2025-03-01", "2025-03-01", "2026-02-28"),
    ("林十四", "CT2025-010", "2025-05-20", "2025-05-20", "2025-07-10"),  # will expire soon
]

# ====== 1. Companies Excel ======
df_company = pd.DataFrame([
    {"企业名称": c[0], "联系人": c[1], "联系电话": c[2], "地址": c[3], "营业执照号": c[4],
     "合作状态": {"active":"正常合作","paused":"暂停合作","terminated":"终止合作"}[c[5]],
     "合作起始日期": c[6], "合作截止日期": c[7]}
    for c in COMPANIES
])
df_company.to_excel(OUT / "测试_企业.xlsx", index=False)
print(f"Companies: {len(df_company)} rows")

# ====== 2. Positions Excel ======
df_position = pd.DataFrame([
    {"所属企业": company, "岗位名称": pos[0], "日单价": pos[1], "需求人数": random.randint(3, 20), "岗位状态": "招聘中"}
    for company, positions in POSITIONS for pos in positions
])
df_position.to_excel(OUT / "测试_岗位.xlsx", index=False)
print(f"Positions: {len(df_position)} rows")

# ====== 3. Employees Excel ======
df_employee = pd.DataFrame([
    {"姓名": e[0], "身份证号": e[1], "手机号": e[2], "性别": "男" if e[3]=="male" else "女",
     "地址": e[4], "企业名称": e[5], "岗位名称": e[6], "入职日期": e[7]}
    for e in EMPLOYEES_RAW
])
df_employee.to_excel(OUT / "测试_人员.xlsx", index=False)
print(f"Employees: {len(df_employee)} rows")

# ====== 4. Contracts Excel ======
df_contract = pd.DataFrame([
    {"员工姓名": c[0], "合同编号": c[1], "签订日期": c[2], "合同起始日期": c[3], "合同截止日期": c[4], "合同类型": "初始签订"}
    for c in CONTRACTS_RAW
])
df_contract.to_excel(OUT / "测试_合同.xlsx", index=False)
print(f"Contracts: {len(df_contract)} rows")

# ====== 5. Attendance Excel ======
attendance_records = []
for emp in EMPLOYEES_RAW:
    work_days = random.randint(18, 22)
    for d in range(work_days):
        day = date(2026, 7, 1) + timedelta(days=d)
        if day > date.today():
            break
        status = random.choices(["正常出勤","正常出勤","正常出勤","正常出勤","正常出勤","正常出勤","正常出勤","迟到","请假"], k=1)[0]
        hours = 8 if status == "正常出勤" else (7 if status == "迟到" else 0)
        attendance_records.append({
            "员工姓名": emp[0], "出勤日期": day.strftime("%Y-%m-%d"),
            "出勤状态": status, "工时": hours, "是否异常": "否" if status == "正常出勤" else "是",
            "备注": "" if status == "正常出勤" else f"{status}记录"
        })
df_attendance = pd.DataFrame(attendance_records)
df_attendance.to_excel(OUT / "测试_考勤.xlsx", index=False)
print(f"Attendance: {len(df_attendance)} rows")

# ====== 6. Payroll Excel ======
payroll_records = []
for month_int in range(2, 7):
    month_str = f"2026-{month_int:02d}"
    for emp in EMPLOYEES_RAW:
        base = random.randint(4000, 8000)
        allowance = random.randint(0, 2000)
        deduction = random.randint(0, 500)
        payroll_records.append({
            "员工姓名": emp[0], "月份": month_str, "基本工资": base, "津贴": allowance,
            "扣款": deduction, "实发金额": base + allowance - deduction,
            "发放状态": random.choices(["已发放","已发放","已发放","待发放"], k=1)[0],
            "发放日期": f"2026-{month_int:02d}-{random.randint(5,15):02d}",
        })
df_payroll = pd.DataFrame(payroll_records)
df_payroll.to_excel(OUT / "测试_工资.xlsx", index=False)
print(f"Payroll: {len(df_payroll)} rows")

# ====== 7. Rebate Excel ======
rebate_records = []
for month_int in range(2, 7):
    for _ in range(random.randint(1, 3)):
        c = random.choice(COMPANIES)
        rebate_records.append({
            "企业名称": c[0], "日期": f"2026-{month_int:02d}-{random.randint(1,28):02d}",
            "金额": random.randint(2000, 15000), "涉及人数": random.randint(1, 5),
            "备注": random.choice(["代招普工", "代招技工", "临时用工", ""])
        })
df_rebate = pd.DataFrame(rebate_records)
df_rebate.to_excel(OUT / "测试_返费.xlsx", index=False)
print(f"Rebates: {len(df_rebate)} rows")

# ====== 8. Invoice Excel ======
invoice_records = []
for c in COMPANIES:
    for month_int in range(2, 7):
        if random.random() > 0.4:
            invoice_records.append({
                "企业名称": c[0],
                "发票号": f"FP2026{month_int:02d}{random.randint(100,999)}",
                "开票日期": f"2026-{month_int:02d}-{random.randint(1,28):02d}",
                "金额": random.randint(10000, 200000),
                "是否已回款": random.choice(["是","是","是","否"]),
                "备注": ""
            })
df_invoice = pd.DataFrame(invoice_records)
df_invoice.to_excel(OUT / "测试_开票.xlsx", index=False)
print(f"Invoices: {len(df_invoice)} rows")

# ====== 9. Receivables Excel ======
receivable_records = []
for c in COMPANIES[:4]:
    for month_int in range(2, 7):
        amount = random.randint(10000, 80000)
        received = random.choice([0, 0, amount, amount // 2, amount])
        expected = f"2026-{month_int:02d}-{random.randint(15,28):02d}"
        status = "已到账" if received >= amount else ("部分回款" if received > 0 else ("已逾期" if expected < "2026-07-01" else "待回款"))
        receivable_records.append({
            "企业名称": c[0], "预计回款日期": expected, "金额": amount,
            "实际回款日期": f"2026-{month_int:02d}-{random.randint(5,20):02d}" if received > 0 else "",
            "付款方式": random.choice(["直接给付","直接给付","银行承兑"]),
            "回款状态": status, "逾期天数": 0,
            "备注": ""
        })
df_receivable = pd.DataFrame(receivable_records)
df_receivable.to_excel(OUT / "测试_回款.xlsx", index=False)
print(f"Receivables: {len(df_receivable)} rows")

# ====== 10. Payment Excel ======
payment_records = []
for r in receivable_records:
    if r["回款状态"] in ("已到账", "部分回款"):
        payment_records.append({
            "企业名称": r["企业名称"], "回款日期": r["实际回款日期"],
            "金额": r["金额"] if r["回款状态"] == "已到账" else r["金额"] // 2,
            "付款方式": r["付款方式"], "承兑到期日": f"2026-{random.randint(8,12):02d}-{random.randint(1,28):02d}" if r["付款方式"] == "银行承兑" else "",
            "银行流水": f"BANK{random.randint(10000,99999)}", "备注": ""
        })
df_payment = pd.DataFrame(payment_records)
df_payment.to_excel(OUT / "测试_实收回款.xlsx", index=False)
print(f"Payments: {len(df_payment)} rows")

# ====== 11. Cash Journal ======
cash_records = []
for month_int in range(1, 6):
    days = random.randint(8, 15)
    for _ in range(days):
        day = f"2026-{month_int:02d}-{random.randint(1,28):02d}"
        is_income = random.random() > 0.55
        amount = random.randint(500, 50000) if is_income else random.randint(100, 30000)
        cash_records.append({
            "日期": day,
            "收入金额": amount if is_income else 0,
            "收入方式": random.choice(["现金","微信","支付宝","银行转账"]) if is_income else "",
            "摘要说明": random.choice(["客户回款","劳务费","服务费收入",""]) if is_income else random.choice(["工资支出","返费支出","办公费用","房租水电","差旅费",""]),
            "支出金额": amount if not is_income else 0,
            "支出方式": random.choice(["现金","微信","银行转账"]) if not is_income else "",
            "备注信息": "",
        })
df_cash = pd.DataFrame(cash_records)
# Sort by date
df_cash = df_cash.sort_values("日期").reset_index(drop=True)
df_cash.to_excel(OUT / "测试_现金日记账.xlsx", index=False, sheet_name="现金日记账")
print(f"Cash journal: {len(df_cash)} rows")

# ====== 12. Bank Journal ======
bank_records = []
for month_int in range(1, 6):
    days = random.randint(5, 10)
    for _ in range(days):
        day = f"2026-{month_int:02d}-{random.randint(1,28):02d}"
        is_income = random.random() > 0.5
        amount = random.randint(5000, 200000) if is_income else random.randint(1000, 80000)
        bank_records.append({
            "日期": day,
            "收入金额": amount if is_income else 0,
            "收入方式": "银行转账",
            "摘要说明": random.choice(["企业回款","开票回款","劳务费到账",""]) if is_income else random.choice(["工资发放","返费支付","供应商付款","税金缴纳","社保公积金",""]),
            "支出金额": amount if not is_income else 0,
            "支出方式": "银行转账",
            "备注信息": "",
        })
df_bank = pd.DataFrame(bank_records)
df_bank = df_bank.sort_values("日期").reset_index(drop=True)
df_bank.to_excel(OUT / "测试_银行日记账.xlsx", index=False, sheet_name="银行日记账")
print(f"Bank journal: {len(df_bank)} rows")

print(f"\nAll test files written to: {OUT}")
