# AI 财务经营助理重构方案

## 1. 产品定位

本项目不应该定位为“Excel 导入工具”或“劳务派遣后台管理系统”，而应该定位为：

> 面向劳务派遣公司的 AI 财务经营助理。

它的核心价值不是把 Excel 机械地变成表格，而是让 AI 像一个懂业务的财务助理/个人秘书一样，帮助用户完成：

- 读懂混乱、不规范、有错误的 Excel。
- 分清资金流水、经营收入、经营成本、账户往来、结余、汇总。
- 把确定的数据整理进系统。
- 对不确定的数据给出原因和处理建议。
- 支持用户围绕导入数据和经营数据自由提问、比对、追溯。

最终用户不应该感觉自己在操作数据库，而应该感觉：

> 我把乱账丢进去，AI 帮我读、帮我分、帮我算、帮我解释。

## 2. 真实业务口径

### 2.1 资金流水

本项目里的资金流水不是泛泛的“微信、支付宝、现金、银行账户”分类。

当前真实业务里，核心账簿只有两个：

- 现金日记账
- 银行日记账

如果现金日记账里出现“微信零钱”，它只是收支方式，不是独立账簿。

正确数据结构：

```json
{
  "ledger_type": "现金日记账",
  "direction": "收入",
  "date": "2026-01-03",
  "amount": 0.1,
  "method": "微信零钱",
  "summary": "零钱通收益"
}
```

银行日记账：

```json
{
  "ledger_type": "银行日记账",
  "direction": "支出",
  "date": "2026-01-05",
  "amount": 100001.25,
  "method": "农商银行",
  "summary": "转杨总"
}
```

### 2.2 经营收入

经营收入不能等于日记账收入。

经营收入应该来自：

- 企业回款
- 劳务费收入
- 开票收入
- 明确属于经营收入的其他收入

不能计入经营收入的典型项目：

- 年初结余
- 公账结余
- 老板转入
- 账户互转
- 借款
- 还款
- 银行/现金账户之间调拨
- 月度汇总行

### 2.3 经营成本

经营成本不能只统计工资。

至少包括：

- 工资成本
- 返费成本
- 社保/保险
- 税费
- 办公费用
- 房租水电
- 差旅报销
- 其他经营费用

净利润口径：

```text
净利润 = 经营收入 - 经营成本
```

不能用：

```text
日记账收入 - 日记账支出
```

### 2.4 非经营流水

非经营流水应该保留在日记账中，但不进入利润核算。

例如：

```json
{
  "ledger_type": "银行日记账",
  "direction": "收入",
  "amount": 20000,
  "summary": "杨总转入",
  "business_category": "账户往来",
  "count_in_profit": false,
  "ai_reason": "个人转入，不属于企业经营回款"
}
```

## 3. 数据模型重构

### 3.1 日记账 Journal

日记账是资金流水账，按现金日记账和银行日记账分账展示。

建议字段：

```json
{
  "id": 1,
  "ledger_type": "现金日记账|银行日记账",
  "date": "2026-01-01",
  "direction": "收入|支出",
  "amount": 44760.84,
  "method": "微信零钱|农商银行|现金|其他",
  "summary": "年初结余",
  "business_category": "期初结余|企业回款|工资成本|返费成本|账户往来|办公费用|税费|其他",
  "count_in_profit": false,
  "related_company": "",
  "related_employee": "",
  "business_month": "2026-01",
  "source_sheet": "现金日记账",
  "source_row": 5,
  "source_region": "cash_income_flow",
  "ai_reason": "年初结余是余额起点，不计入经营收入",
  "created_at": "...",
  "updated_at": "..."
}
```

说明：

- `ledger_type` 解决现金和银行分账问题。
- `direction` 替代旧的 `income_amount/expense_amount` 双字段，避免一行混合收入支出。
- `business_category` 解决业务归类问题。
- `count_in_profit` 决定是否进入利润核算。
- `source_sheet/source_row/source_region` 用于追溯原始 Excel。
- `ai_reason` 让用户知道 AI 为什么这样分。

### 3.2 财务记录 Finance

财务记录是日记账的业务化结果，不是日记账的重复展示。

建议字段：

```json
{
  "id": 1,
  "date": "2026-01-04",
  "type": "收入|支出",
  "category": "企业回款|工资成本|返费成本|办公费用|账户往来|期初结余|其他",
  "amount": 17739.5,
  "count_in_profit": true,
  "ledger_type": "银行日记账",
  "linked_journal_id": 10,
  "related_company": "明昌金属",
  "related_employee": "",
  "business_month": "2025-12",
  "summary": "支付12月明昌员工工资",
  "ai_reason": "摘要包含支付员工工资，归为工资成本"
}
```

### 3.3 企业 Company

企业不是简单通讯录，而是经营对象。

建议字段：

```json
{
  "id": 1,
  "company_name": "明昌金属",
  "status": "合作中|暂停|已终止|潜在客户",
  "contact_person": "",
  "phone": "",
  "settlement_method": "按小时|按天|按月|按人头|其他",
  "billing_cycle": "月结|周结|其他",
  "active_employee_count": 0,
  "receivable_balance": 0,
  "overdue_amount": 0,
  "month_income": 0,
  "month_cost": 0,
  "month_profit": 0,
  "risk_tags": []
}
```

### 3.4 员工 Employee

员工是业务链路中心。

建议字段：

```json
{
  "id": 1,
  "name": "张三",
  "phone": "",
  "id_card": "",
  "status": "在职|待入职|离职|黑名单",
  "company_id": 1,
  "company_name": "明昌金属",
  "position_name": "操作工",
  "entry_date": "2026-01-05",
  "leave_date": "",
  "contract_status": "已签|未签|即将到期|已过期",
  "payroll_status": "待发|已发|异常",
  "risk_tags": []
}
```

### 3.5 合同 Contract

合同是风险控制模块。

建议字段：

```json
{
  "id": 1,
  "contract_type": "员工合同|企业合同|派遣协议",
  "subject_type": "employee|company",
  "subject_id": 1,
  "subject_name": "张三",
  "company_id": 1,
  "company_name": "明昌金属",
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "status": "待签|生效中|即将到期|已过期|已终止",
  "days_remaining": 120,
  "risk_tags": []
}
```

## 4. AI 导入架构

旧方案的问题是：Python 写太多死规则，AI 只是兜底。

新方案必须反过来：

> AI 负责理解和判断，程序负责读取、校验、保存、查询。

### 4.1 总流程

```text
上传 Excel
↓
Workbook Profiler 扫描原始结构
↓
AI Structure Planner 生成导入方案
↓
AI Chunk Processor 分块处理全量数据
↓
Deterministic Validator 程序校验
↓
AI Final Reviewer 汇总复审
↓
前端展示整理结果
↓
保存确定数据
↓
用户可对导入结果自由提问
```

### 4.2 Workbook Profiler

Python 只做客观扫描，不做业务判断。

输出内容：

- sheet 名称
- 行列数量
- 非空区域
- 合并单元格
- 表头候选
- 重复表头位置
- 空行位置
- 公式单元格
- 每隔 N 行的抽样
- 大额数字位置
- 包含“合计/小计/结余/余额/月度汇总”的行

示例：

```json
{
  "sheet_name": "现金日记账",
  "non_empty_regions": [
    "A4:D1360",
    "F4:I1360",
    "L4:N16"
  ],
  "header_candidates": [
    ["日期", "收入金额", "收入方式", "摘要说明"],
    ["日期", "支出金额", "支出方式", "摘要说明"],
    ["月份", "收入金额", "支出金额"]
  ],
  "summary_like_regions": ["L4:N16"]
}
```

### 4.3 AI Structure Planner

AI 读取 workbook profile 和原始样本，生成全局导入方案。

示例输出：

```json
{
  "workbook_type": "资金流水账",
  "sheets": [
    {
      "sheet_name": "现金日记账",
      "ledger_type": "现金日记账",
      "regions": [
        {
          "region_id": "cash_income_flow",
          "type": "income_flow",
          "range": "A4:D1360",
          "columns": {
            "date": "A",
            "amount": "B",
            "method": "C",
            "summary": "D"
          },
          "import_as_records": true
        },
        {
          "region_id": "cash_expense_flow",
          "type": "expense_flow",
          "range": "F4:I1360",
          "columns": {
            "date": "F",
            "amount": "G",
            "method": "H",
            "summary": "I"
          },
          "import_as_records": true
        },
        {
          "region_id": "cash_month_summary",
          "type": "monthly_summary",
          "range": "L4:N16",
          "import_as_records": false
        }
      ]
    }
  ],
  "business_rules": [
    "年初结余只进入日记账，不计入经营收入",
    "杨总转入归为账户往来，不计入利润",
    "支付员工工资归为工资成本，计入经营成本",
    "月度汇总区只用于校验，不生成流水"
  ]
}
```

### 4.4 AI Chunk Processor

Excel 可能有 1000 行、5000 行，不能只看前 N 行。

处理方式：

- 按 AI plan 的 region 切块。
- 每块约 30-80 行。
- 每块都带全局 plan 和业务规则。
- AI 不重新定义规则，只按规则处理当前块。
- 每条输出都必须带原始 sheet、行号、区域。

示例输出：

```json
{
  "records": [
    {
      "source_sheet": "银行日记账",
      "source_row": 8,
      "source_region": "bank_expense_flow",
      "target": "journal",
      "ledger_type": "银行日记账",
      "direction": "支出",
      "date": "2026-01-05",
      "amount": 100001.25,
      "method": "农商银行",
      "summary": "转杨总",
      "business_category": "账户往来",
      "count_in_profit": false,
      "ai_reason": "摘要为转杨总，属于账户往来，不是经营支出"
    }
  ],
  "skipped_rows": [
    {
      "source_row": 20,
      "reason": "月度汇总区，不生成流水"
    }
  ],
  "uncertain_rows": []
}
```

### 4.5 Deterministic Validator

程序校验 AI 输出，但不替 AI 做业务判断。

校验内容：

- 日期是否合法。
- 金额是否合法。
- 枚举是否合法。
- 同一 source row 是否重复导入。
- summary region 是否被误导入流水。
- `count_in_profit` 和 `business_category` 是否冲突。
- 日记账必须有 `ledger_type/direction/date/amount`。
- 财务记录必须有 `type/category/amount/count_in_profit`。

校验失败的记录不保存，进入异常摘要。

### 4.6 AI Final Reviewer

所有分块处理完成后，AI 做汇总复审。

它需要回答：

- 现金日记账整理了多少收入/支出流水。
- 银行日记账整理了多少收入/支出流水。
- 哪些是经营收入。
- 哪些是经营成本。
- 哪些只是账户往来。
- 哪些是结余。
- 哪些数据被跳过。
- 哪些数据不确定。
- 有没有明显异常。

示例：

```json
{
  "review_summary": {
    "现金日记账": {
      "flow_income": 472181.1,
      "flow_expense": 417863.64,
      "operating_income": 0,
      "operating_cost": 390000,
      "non_operating_flow": 82181.1
    },
    "银行日记账": {
      "flow_income": 5516246.77,
      "flow_expense": 5064535.73,
      "operating_income": 2300000,
      "operating_cost": 4100000,
      "non_operating_flow": 800000
    }
  },
  "warnings": [
    "银行日记账流水收入较大，但包含账户往来和结余，不应直接作为经营收入",
    "右侧月度汇总区已跳过，仅用于校验"
  ]
}
```

## 5. 对话助手设计

系统需要两个对话入口。

### 5.1 导入批次问答

围绕当前 Excel 和导入结果提问。

用户可以问：

- 为什么收入这么高？
- 哪些不计入利润？
- 现金日记账和银行日记账分别是多少？
- 哪些行没有保存？
- 杨总转入算不算收入？
- 这笔 100001.25 是什么？

AI 回答必须基于当前导入批次上下文。

上下文包括：

- workbook profile
- AI import plan
- chunk outputs
- validator issues
- final review summary
- records ready
- uncertain rows
- skipped rows

### 5.2 经营数据问答

围绕已保存系统数据提问。

用户可以问：

- 1 月和 2 月利润差异？
- 哪个企业利润最好？
- 哪些企业人数多但利润低？
- 本月银行日记账里不计入利润的大额流水有哪些？
- 某个员工对应哪些工资和合同？

AI 不应该直接凭空回答，而是生成查询计划：

```json
{
  "intent": "compare_profit",
  "time_range": ["2026-01", "2026-02"],
  "group_by": "month",
  "metrics": ["operating_income", "operating_cost", "net_profit"],
  "filters": {
    "count_in_profit": true
  }
}
```

后端执行查询，再把结果交给 AI 解释。

## 6. 前端设计

### 6.1 首页经营概览

首页不展示“日记账总收入”。

应该展示：

- 本月经营收入
- 本月经营成本
- 本月净利润
- 待回款金额
- 逾期金额
- 在职员工
- 合作企业
- 待处理风险

资金流水独立展示：

- 现金日记账收入流水
- 现金日记账支出流水
- 银行日记账收入流水
- 银行日记账支出流水

并明确标注：

```text
流水累计不等于经营收入
```

### 6.2 导入页

导入页应该像 AI 工作台，而不是字段映射工具。

布局：

```text
左侧：上传和处理进度
中间：AI 整理结论
右侧：AI 对话助手
下方：可保存数据 / 暂不保存数据 / 跳过区域
```

用户看到：

```text
AI 已读完整本表格

识别到：
- 现金日记账：收入流水、支出流水、月度汇总区
- 银行日记账：收入流水、支出流水、月度汇总区

可保存：
- 日记账 3219 条
- 财务记录 3219 条

暂不保存：
- 1 条日期缺失

跳过：
- 现金日记账月度汇总区
- 银行日记账月度汇总区
```

### 6.3 日记账页

日记账页按账簿分组，而不是混成一张表。

```text
日记账

Tabs:
- 现金日记账
- 银行日记账

每个 Tab 内：
- 收入流水
- 支出流水
- 流水累计
- 不计入利润金额
- 明细表
```

### 6.4 财务记录页

财务记录页按经营分类展示。

字段：

- 日期
- 类型
- 类别
- 金额
- 是否计入利润
- 关联企业
- 关联员工
- 来源账簿
- AI 原因

### 6.5 经营分析页

需要一个灵活查询和比对页面。

筛选维度：

- 时间范围
- 企业
- 员工
- 账簿类型
- 业务分类
- 是否计入利润

指标：

- 经营收入
- 经营成本
- 净利润
- 工资成本
- 返费成本
- 其他成本
- 回款金额
- 逾期金额
- 流水收入
- 流水支出

展示方式：

- 指标卡
- 趋势图
- 企业排行
- 成本构成
- 明细穿透
- AI 总结

## 7. 后端 API 设计

### 7.1 导入相关

```http
POST /api/v2/import/upload
POST /api/v2/import/{upload_id}/profile
POST /api/v2/import/{upload_id}/plan
POST /api/v2/import/{batch_id}/process
POST /api/v2/import/{batch_id}/review
POST /api/v2/import/{batch_id}/commit
GET  /api/v2/import/{batch_id}
POST /api/v2/import/{batch_id}/chat
```

### 7.2 查询分析

```http
POST /api/v2/analytics/query
POST /api/v2/analytics/chat
GET  /api/v2/dashboard/summary
```

查询请求：

```json
{
  "time_range": {
    "start": "2026-01-01",
    "end": "2026-01-31"
  },
  "group_by": ["company", "business_category"],
  "metrics": ["operating_income", "operating_cost", "net_profit"],
  "filters": {
    "count_in_profit": true,
    "ledger_type": "银行日记账"
  }
}
```

## 8. 实施计划

### 第一阶段：重构数据模型

目标：

- 统一日记账为 `ledger_type + direction + amount`。
- 财务记录增加 `count_in_profit`。
- 所有记录增加 AI 原因和来源追溯。

任务：

- 新建 v2 schema。
- 写数据 repository。
- 保留旧接口兼容一段时间。
- 新导入只写 v2 数据。

### 第二阶段：重构 AI 导入引擎

目标：

- AI 成为导入主导。
- Python 只做读取、校验、保存。

任务：

- 实现 Workbook Profiler。
- 实现 AI Structure Planner。
- 实现 Chunk Processor。
- 实现 Validator。
- 实现 Final Reviewer。
- 保存完整 AI 上下文。

### 第三阶段：重做导入前端

目标：

- 从“表格导入器”变成“AI 整理工作台”。

任务：

- 上传进度。
- AI 整理结论。
- 按现金/银行展示。
- 可保存/暂不保存/跳过区域展示。
- 导入批次问答。

### 第四阶段：重做经营概览和日记账

目标：

- 资金流水和经营收入分开。

任务：

- Dashboard 改经营口径。
- 日记账按现金/银行分 Tab。
- 财务记录展示是否计入利润。
- 利润核算按经营分类计算。

### 第五阶段：经营分析和 AI 问答

目标：

- 支持灵活查询、对比、多维度分析。

任务：

- Analytics Query API。
- AI Query Planner。
- 趋势图、排行、构成图。
- 系统级 AI 问答。

## 9. 判断系统是否成功的标准

成功标准不是“能导入 Excel”，而是：

- 用户上传混乱 Excel 后，AI 能说清楚每个 sheet 是什么。
- 现金日记账和银行日记账分开展示。
- 日记账流水收入不会被误当成经营收入。
- 年初结余、老板转入、账户往来不会进入利润。
- 工资、返费、办公、税费等经营成本能进入利润。
- 每一笔分类都有原始行号和 AI 原因。
- 用户能问“为什么收入这么高”，AI 能基于数据解释。
- 用户能按月份、企业、账簿、业务分类自由查询和比对。

## 10. 当前项目需要立即停止的做法

- 不再用硬编码金额上限判断异常。
- 不再把日记账总收入当经营收入。
- 不再把现金/银行/微信/支付宝泛泛混分账户。
- 不再用 Python 死规则替代 AI 的业务判断。
- 不再在主流程展示字段映射、置信度、调试细节。
- 不再为了“保存更多数据”而把不确定数据硬塞进系统。

## 11. 核心原则

```text
AI 负责理解、归类、解释。
程序负责读取、校验、保存、查询。
前端负责让用户看懂、追问、复核。
```

最终体验应该是：

> 用户上传一份混乱账表，AI 像财务助理一样完整读完、拆清口径、整理入账、指出异常，并能随时回答为什么。

