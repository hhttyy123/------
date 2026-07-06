# 劳务派遣管理系统 — MVP 实施计划

> 版本：1.0 | 日期：2026-06-15 | 状态：待执行

---

## 1. 项目目标

构建以 **「表格分析 Agent」** 为核心的智能 Excel 导入系统。

**核心链路**：用户上传任意格式 Excel → Agent 自动识别、映射、转换 → 用户预览确认 → 一键导入数据库。

**MVP 范围限制**：先把智能导入跑通，17 个业务模块的增删改查、预警、审批、利润核算等功能后续再叠加。

---

## 2. 技术选型

| 层     | 选型                                              | 理由                             |
| ------ | ------------------------------------------------- | -------------------------------- |
| 后端   | Python 3.11.9 + FastAPI + SQLAlchemy 2.0 async    | 数据处理生态好，与 LLM SDK 配合成熟 |
| 数据库 | SQLite（MVP）→ PostgreSQL（后期迁移）              | 零安装，SQLAlchemy 一行配置即可切换 |
| Agent  | Anthropic Claude API（结构化 Tool Use）            | 强制返回 JSON Schema，杜绝解析错误 |
| Excel  | pandas + openpyxl                                 | 多 Sheet、合并单元格、类型推断     |
| 前端   | Vite + React + TypeScript + shadcn/ui + Tailwind  | 组件化，响应式，快速出界面         |
| 金额   | INTEGER（分）                                      | 精确到分，消除浮点误差             |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────┐
│                  前端（React）                    │
│   📤 上传 Excel                                   │
│   🔍 预览分析结果（分类 + 列映射 + 数据预览）        │
│   ✏️ 手动调整映射                                  │
│   ✅ 确认导入 → 查看结果                            │
└────────────────────┬────────────────────────────┘
                     │ HTTP REST API
┌────────────────────▼────────────────────────────┐
│              🧠 表格分析 Agent（核心）              │
│                                                   │
│  ① 分类器：这是什么数据？（员工/工资/回款/…）        │
│  ② 解析器：表头映射 + 值转换 + 校验                 │
│  ③ 路由层：分发到对应业务模块                       │
│  ④ 查询层：自然语言 → 数据库查询（后期）             │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              业务逻辑层（确定性规则）                │
│                                                   │
│  数据校验 → 入库 → 返回结果明细                     │
│  （后续扩展：业务联动、状态流转、预警、审批等）       │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              数据层（SQLite）                     │
│  员工、考勤、工资、回款、日记账、操作日志 …         │
└─────────────────────────────────────────────────┘
```

**核心原则**：Agent 负责「理解」（模糊 → 精确），业务逻辑层负责「执行」（确定性的规则计算）。

---

## 4. Agent 四大职责

### 4.1 智能分类 — "这是什么数据？"

任意 Excel 扔进来，Agent 先判断属于哪个业务模块：

| 特征                           | 判断为     |
| ------------------------------ | ---------- |
| 有姓名 + 身份证号 + 手机号       | 员工花名册  |
| 有日期 + 出勤状态 + 工时         | 考勤表     |
| 有月份 + 基本工资 + 实发金额     | 工资表     |
| 有企业名 + 预计回款日期 + 金额   | 回款表     |
| 有日期 + 收入/支出 + 来源类型    | 日记账     |

多 Sheet 的 Excel 可能跨模块，Agent 需能拆解。

### 4.2 列映射 — "这一列对应哪个标准字段？"

系统维护一份 **Schema Registry**（标准字段字典），每个字段记录了标准名和常见别名：

```python
FieldDef(
    field_key="gender",
    field_label="性别",
    field_type=FieldType.ENUM,
    required=True,
    aliases=["性  别", "男/女", "男女", "sex", "gender_type", "性别(男/女)"],
    enum_values=["男", "女"],
)
```

Agent 的映射逻辑：

```
输入列名："男/女"  →  模糊匹配 aliases  →  命中 gender (confidence: 0.95)
输入列名："性别类型" →  LLM 语义理解  →  命中 gender (confidence: 0.78)
输入列名："Sex"    →  别名匹配  →  命中 gender (confidence: 0.90)
```

### 4.3 值转换 — "这个值怎么标准化？"

```
输入值："男"     →  枚举精确匹配  →  "男" ✓
输入值："男性"   →  LLM 语义理解  →  "男" ✓
输入值："M"      →  LLM 语义理解  →  "男" ✓
输入值："female" →  LLM 语义理解  →  "女" ✓
输入值："未知"   →  无法转换  →  标记为待处理 ⚠️
输入值："2025/2/29" → 日期解析失败 → 标记错误 ❌
```

### 4.4 结构化返回

```json
{
  "classification": {
    "module": "employee",
    "module_label": "员工管理",
    "confidence": 0.92,
    "reasoning": "检测到'身份证号'、'手机号'、'入职日期'等唯一识别字段"
  },
  "field_mappings": [
    { "column_index": 0, "original_header": "姓名", "mapped_field": "name", "confidence": 0.97 },
    { "column_index": 1, "original_header": "男/女", "mapped_field": "gender", "confidence": 0.85 },
    { "column_index": 2, "original_header": "身份证", "mapped_field": "id_card_number", "confidence": 0.93 }
  ],
  "warnings": [
    { "type": "missing_field", "message": "未找到必填字段'手机号'的映射", "severity": "warning" }
  ]
}
```

---

## 5. Schema Registry 设计

### 5.1 核心数据结构

```python
class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    MONTH = "month"
    ENUM = "enum"
    PHONE = "phone"
    ID_CARD = "id_card"

@dataclass
class FieldDef:
    field_key: str           # snake_case, e.g., "id_card_number"
    field_label: str         # 中文显示名，e.g., "身份证号"
    field_type: FieldType
    required: bool = False
    unique: bool = False
    aliases: list[str]       # 常见别名，用于模糊匹配
    enum_values: list[str] | None = None  # ENUM 类型的可选值
    regex_pattern: str | None = None      # 正则校验
    default_value: str | None = None
    description: str = ""

@dataclass
class ModuleDef:
    module_key: str          # e.g., "employee", "payroll"
    module_label: str        # 中文显示名
    description: str
    fields: list[FieldDef]
    identifying_fields: list[str]  # 用于模块识别的特征字段
```

### 5.2 MVP 阶段先实现 3 个模块（与现有 Excel 对齐）

| module_key | module_label | 识别特征字段                |
| ---------- | ------------ | -------------------------- |
| employee   | 员工管理     | id_card_number, phone       |
| journal    | 日记账       | income_amount, expense_amount, source_type |
| profit     | 利润核算     | month, total_income, net_profit |

### 5.3 完整 17 个模块（MVP 之后再补）

employee, attendance, contract, company, position, payroll, recruitment_fee, accounts_receivable, invoice, journal, finance, profit, bank_journal, cash_journal, accounts_payable, audit_log, approval

---

## 6. API 设计（三端点流水线）

### 6.1 POST /api/v1/upload — 上传文件

```
Request:  multipart/form-data (file: .xlsx/.xls, max 10MB)

Response: {
  "upload_id": "uuid",
  "filename": "原文件名.xlsx",
  "sheets": [
    {"name": "Sheet1", "row_count": 500, "column_count": 18},
    {"name": "Sheet2", "row_count": 10, "column_count": 5}
  ],
  "sheet_count": 2
}
```

### 6.2 POST /api/v1/analyze — Agent 分析

```
Request: {
  "upload_id": "uuid",
  "sheet_name": "Sheet1",
  "sample_size": 10
}

Response: {
  "classification": {
    "module": "employee",
    "module_label": "员工管理",
    "confidence": 0.92,
    "alternative_modules": [...],
    "reasoning": "..."
  },
  "field_mappings": [
    {
      "column_index": 0,
      "original_header": "姓名",
      "mapped_field": "name",
      "field_label": "姓名",
      "confidence": 0.97
    },
    ...
  ],
  "value_samples": [...],
  "warnings": [...],
  "preview_rows": [...]
}
```

### 6.3 POST /api/v1/import — 确认导入

```
Request: {
  "upload_id": "uuid",
  "sheet_name": "Sheet1",
  "confirmed_module": "employee",
  "confirmed_mappings": [
    {"column_index": 0, "mapped_field": "name"},
    {"column_index": 1, "mapped_field": null},  // 跳过此列
    ...
  ]
}

Response: {
  "total_rows": 500,
  "imported_rows": 492,
  "skipped_rows": 5,
  "error_rows": 3,
  "errors": [
    {"row": 23, "message": "手机号格式无效", "data": {...}},
    ...
  ]
}
```

---

## 7. 项目目录结构

```
labor-dispatch-system/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口，启动事件
│   │   ├── config.py                  # 配置（DB路径、API Key）
│   │   ├── database.py                # SQLAlchemy 引擎 + 建表
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── upload.py          # POST /api/v1/upload
│   │   │       ├── analyze.py         # POST /api/v1/analyze
│   │   │       └── import_.py         # POST /api/v1/import
│   │   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── services/
│   │   │   ├── excel_reader.py        # pandas/openpyxl 封装
│   │   │   ├── agent_pipeline.py      # Agent 编排主流程
│   │   │   ├── value_converter.py     # 确定性值转换
│   │   │   └── importer.py            # 校验 + 入库
│   │   ├── agents/
│   │   │   ├── claude_client.py       # Anthropic SDK 封装
│   │   │   ├── prompts.py             # 提示词模板
│   │   │   └── tools.py               # 结构化输出 Tool 定义
│   │   └── registry/                  # Schema Registry
│   │       ├── base.py                # FieldDef, ModuleDef
│   │       ├── employee.py
│   │       ├── journal.py
│   │       ├── profit.py
│   │       ├── ...（其他模块后期补充）
│   │       └── loader.py              # 加载 + 别名倒排索引
│   ├── data/
│   │   └── uploads/                   # 临时上传文件
│   ├── tests/
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/                       # API 调用封装
│   │   │   ├── client.ts
│   │   │   └── importApi.ts
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui 基础组件
│   │   │   ├── upload/
│   │   │   │   ├── FileDropzone.tsx
│   │   │   │   └── UploadProgress.tsx
│   │   │   ├── analysis/
│   │   │   │   ├── ClassificationBadge.tsx
│   │   │   │   ├── MappingTable.tsx
│   │   │   │   ├── DataPreviewTable.tsx
│   │   │   │   └── WarningsList.tsx
│   │   │   └── result/
│   │   │       ├── ImportSummary.tsx
│   │   │       └── ErrorTable.tsx
│   │   ├── pages/
│   │   │   └── ImportWizard.tsx       # 主导入向导（4步流程）
│   │   ├── hooks/
│   │   │   ├── useFileUpload.ts
│   │   │   └── useAnalysis.ts
│   │   └── types/
│   │       └── import.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── index.html
└── .gitignore
```

---

## 8. 数据库表（MVP 核心表）

金额全部用 INTEGER（分）存储，日期用 TEXT（ISO 8601）。

```sql
CREATE TABLE employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    id_card_number TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    gender TEXT NOT NULL CHECK (gender IN ('男', '女')),
    address TEXT DEFAULT '',
    entry_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '在职' CHECK (status IN ('在职', '离职')),
    company_id INTEGER REFERENCES company(id),
    position_id INTEGER REFERENCES position(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    income_amount INTEGER NOT NULL DEFAULT 0,
    expense_amount INTEGER NOT NULL DEFAULT 0,
    description TEXT DEFAULT '',
    source_type TEXT NOT NULL CHECK (source_type IN
        ('工资发放', '返费支出', '回款到账', '财务记录', '手动录入')),
    source_id INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE profit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    total_income INTEGER NOT NULL DEFAULT 0,
    salary_expense INTEGER NOT NULL DEFAULT 0,
    recruitment_fee_expense INTEGER NOT NULL DEFAULT 0,
    other_expense INTEGER NOT NULL DEFAULT 0,
    net_profit INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE import_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    module TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    error_rows INTEGER NOT NULL DEFAULT 0,
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator TEXT NOT NULL,
    operation_time TEXT NOT NULL DEFAULT (datetime('now')),
    module TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('新增', '编辑', '删除', '导出', '导入')),
    description TEXT DEFAULT '',
    is_sensitive INTEGER NOT NULL DEFAULT 0
);
```

---

## 9. 前端页面流程

```
ImportWizard.tsx（4步向导）

Step 1: 上传文件
  └── FileDropzone（拖拽上传 + 进度条）
      → POST /api/v1/upload → 拿到 upload_id + Sheet 列表

Step 2: 选择 Sheet（多 Sheet 时）
  └── 显示 Sheet 概览（名称、行数、列数），单选

Step 3: 预览分析结果
  ├── ClassificationBadge（识别模块 + 置信度）
  ├── MappingTable（列名 → 标准字段映射表，每行显示置信度）
  │   └── 下拉框可手动调整映射（选择其他字段或"跳过此列"）
  ├── DataPreviewTable（前 5 行数据预览，值已转换）
  └── WarningsList（缺失必填字段、值异常等警告）
      → 用户确认 → POST /api/v1/import

Step 4: 导入结果
  ├── ImportSummary（卡片：总行数 / 成功 / 跳过 / 失败）
  └── ErrorTable（失败行的详细错误信息）
```

---

## 10. Agent 调用优化策略

| 策略               | 说明                                                |
| ------------------ | --------------------------------------------------- |
| **Prompt Cache**   | Schema Registry 作为 system 消息缓存在 Anthropic 侧，避免每次重复发送 |
| **结构化输出**     | 使用 Claude Tool Use（`tool_choice: "classify_and_map"`）强制返回 JSON Schema |
| **低温参数**       | temperature=0.1，确保映射结果稳定可复现              |
| **样本量控制**     | 默认发送前 10 行样本，用户可调整（更多行→更高准确度→更多 token） |
| **模块过滤**       | 后续可先做快速分类，再对 top-3 模块做精细映射，减少 prompt 体积 |

---

## 11. 实施步骤

### Phase 0：项目脚手架
- [ ] 创建 Python 3.11.9 虚拟环境
- [ ] 安装后端依赖（fastapi, uvicorn, sqlalchemy, anthropic, pandas, openpyxl 等）
- [ ] 初始化 FastAPI 项目骨架（main.py, config.py, database.py）
- [ ] 初始化 React + Vite 前端项目（shadcn/ui + Tailwind）
- [ ] 创建 .env 和 .gitignore

### Phase 1：Schema Registry
- [ ] 实现 base.py（FieldDef, ModuleDef, FieldType）
- [ ] 实现 3 个模块定义：employee, journal, profit
- [ ] 实现 loader.py（加载 + 别名倒排索引）
- [ ] 编写单元测试

### Phase 2：Excel 读取层
- [ ] 实现 excel_reader.py（Sheet 元信息、表头、样本行）
- [ ] 处理合并单元格、多行表头、空行
- [ ] 用两份现有 Excel 测试

### Phase 3：Claude Agent 接入
- [ ] 实现 claude_client.py + prompts.py + tools.py
- [ ] 实现 agent_pipeline.py（编排主流程）
- [ ] 实现 value_converter.py（枚举/日期/手机号转换）
- [ ] 端到端测试：用真实 Excel 验证

### Phase 4：API + 数据库 + 导入器
- [ ] 实现 upload / analyze / import 三个端点
- [ ] 实现 importer.py（校验 + 入库）
- [ ] 创建数据库表（employee, journal, profit, import_history, audit_log）

### Phase 5：前端
- [ ] 实现 FileDropzone + UploadProgress
- [ ] 实现 ClassificationBadge + MappingTable + DataPreview + WarningsList
- [ ] 实现 ImportSummary + ErrorTable
- [ ] 实现 ImportWizard 主页面（4 步串联）
- [ ] 前后端联调

### Phase 6：扩展
- [ ] 补完剩余 14 个模块的 Schema Registry
- [ ] 错误处理完善、文件清理、CORS 配置

---

## 12. 风险与对策

| 风险                         | 影响         | 对策                                           |
| ---------------------------- | ------------ | ---------------------------------------------- |
| Claude 误分类模块             | 数据进错表   | 显示 top-3 备选 + 置信度，用户可覆盖             |
| 非标准表头行（多行标题）       | 读错表头     | Agent 扫描前 10 行，自动检测表头所在行，用户可调整 |
| 合并单元格导致 NaN            | 数据不完整   | openpyxl 预处理填充合并单元格值                  |
| 大文件导致 token 用量过高     | 成本增加     | Prompt Cache + 样本量控制 + 模块过滤             |
| Claude API 延迟（2-5 秒）     | 用户等待     | Skeleton loading 动画 + 流式展示结果             |

---

## 13. 验证方式

1. 用仓库内两份真实 Excel（日记账、利润核算表）验证 Agent 分类 + 映射
2. 构造非标准表头 Excel（别名/空格/中英混合）验证列映射鲁棒性
3. 构造含异常值的 Excel（错误日期、无效手机号）验证值转换 + 警告
4. 前端端到端：上传 → 预览 → 调整映射 → 确认导入 → 数据库验证
