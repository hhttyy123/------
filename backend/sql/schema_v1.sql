-- 劳务派遣经营管理系统 PostgreSQL 初始结构 v1
-- 评审/本地初始化用途；正式迁移后由 Alembic 接管版本。

BEGIN;

CREATE TABLE users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(80) NOT NULL,
  phone VARCHAR(30),
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(80) NOT NULL,
  level SMALLINT NOT NULL DEFAULT 0,
  description TEXT
);

CREATE TABLE permissions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code VARCHAR(100) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  module VARCHAR(50) NOT NULL,
  action VARCHAR(30) NOT NULL
);

CREATE TABLE user_roles (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_permissions (
  role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE system_settings (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_by BIGINT REFERENCES users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE files (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  original_name VARCHAR(255) NOT NULL,
  storage_key VARCHAR(500) NOT NULL UNIQUE,
  content_type VARCHAR(120),
  size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
  sha256 CHAR(64) NOT NULL,
  uploaded_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_files_sha256 ON files(sha256);

CREATE TABLE import_batches (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  file_id BIGINT NOT NULL REFERENCES files(id),
  module VARCHAR(50) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','profiling','ready','committing','committed','failed','cancelled')),
  mapping_version VARCHAR(50),
  total_rows INTEGER NOT NULL DEFAULT 0,
  ready_rows INTEGER NOT NULL DEFAULT 0,
  warning_rows INTEGER NOT NULL DEFAULT 0,
  blocked_rows INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  created_by BIGINT REFERENCES users(id),
  committed_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  committed_at TIMESTAMPTZ
);

CREATE TABLE import_mappings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  module VARCHAR(50) NOT NULL,
  fingerprint CHAR(64) NOT NULL,
  name VARCHAR(120) NOT NULL,
  mapping JSONB NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (module, fingerprint)
);

CREATE TABLE import_rows (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  batch_id BIGINT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  sheet_name VARCHAR(160) NOT NULL,
  source_row INTEGER NOT NULL CHECK (source_row > 0),
  source_region VARCHAR(80) NOT NULL DEFAULT 'main',
  raw_data JSONB NOT NULL,
  normalized_data JSONB,
  record_fingerprint CHAR(64),
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','ready','warning','blocked','committed','skipped')),
  issues JSONB NOT NULL DEFAULT '[]'::jsonb,
  target_table VARCHAR(80),
  target_record_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (batch_id, sheet_name, source_row, source_region)
);
CREATE INDEX idx_import_rows_batch_status ON import_rows(batch_id, status);
CREATE INDEX idx_import_rows_fingerprint ON import_rows(record_fingerprint) WHERE record_fingerprint IS NOT NULL;

CREATE TABLE companies (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  normalized_name VARCHAR(150) NOT NULL UNIQUE,
  contact_person VARCHAR(80),
  contact_phone VARCHAR(30),
  address VARCHAR(300),
  business_license_no VARCHAR(80),
  cooperation_status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (cooperation_status IN ('active','paused','terminated')),
  cooperation_start_date DATE,
  cooperation_end_date DATE,
  default_receivable_days INTEGER CHECK (default_receivable_days IS NULL OR default_receivable_days >= 0),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  version_no INTEGER NOT NULL DEFAULT 1,
  created_by BIGINT REFERENCES users(id),
  updated_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX uq_companies_license ON companies(business_license_no) WHERE business_license_no IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE positions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id),
  name VARCHAR(120) NOT NULL,
  description TEXT,
  daily_rate NUMERIC(18,2) CHECK (daily_rate IS NULL OR daily_rate >= 0),
  required_count INTEGER CHECK (required_count IS NULL OR required_count >= 0),
  status VARCHAR(20) NOT NULL DEFAULT 'recruiting' CHECK (status IN ('recruiting','filled','closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (company_id, name)
);

CREATE TABLE employees (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  id_card_encrypted TEXT NOT NULL,
  id_card_hash CHAR(64) NOT NULL UNIQUE,
  id_card_last4 CHAR(4) NOT NULL,
  phone VARCHAR(30),
  gender VARCHAR(10) CHECK (gender IS NULL OR gender IN ('male','female','unknown')),
  address VARCHAR(300),
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','blacklisted')),
  source_import_row_id BIGINT REFERENCES import_rows(id),
  version_no INTEGER NOT NULL DEFAULT 1,
  created_by BIGINT REFERENCES users(id),
  updated_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_employees_name ON employees(name);
CREATE INDEX idx_employees_phone ON employees(phone);

CREATE TABLE employment_records (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  employee_id BIGINT NOT NULL REFERENCES employees(id),
  company_id BIGINT NOT NULL REFERENCES companies(id),
  position_id BIGINT REFERENCES positions(id),
  entry_date DATE NOT NULL,
  leave_date DATE,
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('pending','active','left')),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (leave_date IS NULL OR leave_date >= entry_date)
);
CREATE INDEX idx_employment_company_status ON employment_records(company_id, status);

CREATE TABLE attendance_records (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  employment_id BIGINT NOT NULL REFERENCES employment_records(id),
  work_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('normal','late','absent','leave')),
  hours NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (hours >= 0),
  deduction_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (deduction_amount >= 0),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (employment_id, work_date)
);

CREATE TABLE contracts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  employee_id BIGINT REFERENCES employees(id),
  company_id BIGINT REFERENCES companies(id),
  contract_type VARCHAR(30) NOT NULL,
  contract_no VARCHAR(80),
  sign_date DATE,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','expired','terminated')),
  terminated_at DATE,
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (employee_id IS NOT NULL OR company_id IS NOT NULL),
  CHECK (end_date >= start_date)
);
CREATE INDEX idx_contracts_end_status ON contracts(end_date, status);

CREATE TABLE payroll_batches (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  salary_month DATE NOT NULL,
  pay_date DATE,
  status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','finance_review','owner_review','confirmed','rejected','voided')),
  total_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
  rule_version VARCHAR(40),
  created_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (EXTRACT(DAY FROM salary_month) = 1)
);

CREATE TABLE payroll_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  batch_id BIGINT NOT NULL REFERENCES payroll_batches(id) ON DELETE CASCADE,
  employee_id BIGINT NOT NULL REFERENCES employees(id),
  company_id BIGINT NOT NULL REFERENCES companies(id),
  employment_id BIGINT REFERENCES employment_records(id),
  base_salary NUMERIC(18,2) NOT NULL DEFAULT 0,
  allowance NUMERIC(18,2) NOT NULL DEFAULT 0,
  deduction NUMERIC(18,2) NOT NULL DEFAULT 0,
  net_pay NUMERIC(18,2) NOT NULL CHECK (net_pay >= 0),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (batch_id, employee_id)
);

CREATE TABLE recruitment_rebates (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id),
  employee_id BIGINT REFERENCES employees(id),
  rebate_date DATE NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  person_count INTEGER NOT NULL DEFAULT 1 CHECK (person_count > 0),
  status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','finance_review','owner_review','confirmed','rejected','voided')),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE invoices (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id),
  invoice_no VARCHAR(80) NOT NULL UNIQUE,
  invoice_date DATE NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  status VARCHAR(20) NOT NULL DEFAULT 'issued' CHECK (status IN ('draft','issued','partially_paid','paid','voided')),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE receivables (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id),
  invoice_id BIGINT REFERENCES invoices(id),
  expected_date DATE NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  received_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (received_amount >= 0),
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','partial','paid','overdue','voided')),
  remark TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (received_amount <= amount)
);
CREATE INDEX idx_receivables_due_status ON receivables(expected_date, status);

CREATE TABLE payments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES companies(id),
  payment_date DATE NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  payment_method VARCHAR(30) NOT NULL CHECK (payment_method IN ('direct','bank_acceptance')),
  acceptance_due_date DATE,
  bank_reference VARCHAR(120),
  status VARCHAR(20) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('draft','confirmed','voided')),
  remark TEXT,
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (payment_method <> 'bank_acceptance' OR acceptance_due_date IS NOT NULL)
);

CREATE TABLE payment_allocations (
  payment_id BIGINT NOT NULL REFERENCES payments(id),
  receivable_id BIGINT NOT NULL REFERENCES receivables(id),
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (payment_id, receivable_id)
);

CREATE TABLE cash_transactions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  transaction_date DATE NOT NULL,
  ledger_type VARCHAR(20) NOT NULL CHECK (ledger_type IN ('cash','bank')),
  direction VARCHAR(10) NOT NULL CHECK (direction IN ('income','expense')),
  category VARCHAR(40) NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  payment_method VARCHAR(50),
  company_id BIGINT REFERENCES companies(id),
  employee_id BIGINT REFERENCES employees(id),
  summary VARCHAR(500),
  status VARCHAR(20) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('draft','confirmed','voided','reversed')),
  reversal_of_id BIGINT REFERENCES cash_transactions(id),
  source_import_row_id BIGINT REFERENCES import_rows(id),
  created_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_cash_transactions_date_direction ON cash_transactions(transaction_date, direction);
CREATE INDEX idx_cash_transactions_company_date ON cash_transactions(company_id, transaction_date);

CREATE TABLE transaction_links (
  transaction_id BIGINT NOT NULL REFERENCES cash_transactions(id) ON DELETE CASCADE,
  source_type VARCHAR(40) NOT NULL,
  source_id BIGINT NOT NULL,
  link_role VARCHAR(30) NOT NULL DEFAULT 'origin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (transaction_id, source_type, source_id)
);
CREATE INDEX idx_transaction_links_source ON transaction_links(source_type, source_id);

CREATE TABLE approval_requests (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  subject_type VARCHAR(40) NOT NULL,
  subject_id BIGINT NOT NULL,
  current_status VARCHAR(30) NOT NULL DEFAULT 'finance_review' CHECK (current_status IN ('draft','finance_review','owner_review','approved','rejected','cancelled')),
  submitted_by BIGINT NOT NULL REFERENCES users(id),
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  UNIQUE (subject_type, subject_id)
);

CREATE TABLE approval_steps (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  request_id BIGINT NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
  step_level SMALLINT NOT NULL CHECK (step_level BETWEEN 1 AND 3),
  action VARCHAR(20) NOT NULL CHECK (action IN ('submit','approve','reject','cancel')),
  actor_id BIGINT NOT NULL REFERENCES users(id),
  comment TEXT,
  acted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alerts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rule_code VARCHAR(80) NOT NULL,
  subject_type VARCHAR(40) NOT NULL,
  subject_id BIGINT NOT NULL,
  severity VARCHAR(20) NOT NULL CHECK (severity IN ('info','warning','critical')),
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open','processing','resolved','ignored')),
  due_date DATE,
  first_triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX uq_alerts_open_subject ON alerts(rule_code, subject_type, subject_id) WHERE status IN ('open','processing');

CREATE TABLE alert_actions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  alert_id BIGINT NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
  action VARCHAR(30) NOT NULL,
  comment TEXT,
  actor_id BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE profit_periods (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  basis VARCHAR(20) NOT NULL CHECK (basis IN ('cash','accrual')),
  rule_version VARCHAR(40) NOT NULL,
  total_income NUMERIC(18,2) NOT NULL DEFAULT 0,
  total_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
  net_profit NUMERIC(18,2) NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'calculated' CHECK (status IN ('calculated','confirmed','superseded')),
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  confirmed_by BIGINT REFERENCES users(id),
  confirmed_at TIMESTAMPTZ,
  CHECK (period_end >= period_start),
  UNIQUE (period_start, period_end, basis, rule_version)
);

CREATE TABLE profit_lines (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  profit_period_id BIGINT NOT NULL REFERENCES profit_periods(id) ON DELETE CASCADE,
  line_type VARCHAR(20) NOT NULL CHECK (line_type IN ('income','cost')),
  category VARCHAR(50) NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
  source_type VARCHAR(40),
  source_id BIGINT,
  description TEXT
);

CREATE TABLE reconciliation_items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  reconciliation_type VARCHAR(50) NOT NULL,
  period_start DATE,
  period_end DATE,
  left_type VARCHAR(40) NOT NULL,
  left_id BIGINT,
  right_type VARCHAR(40),
  right_id BIGINT,
  difference_type VARCHAR(40) NOT NULL,
  expected_amount NUMERIC(18,2),
  actual_amount NUMERIC(18,2),
  status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open','processing','resolved','ignored')),
  resolution TEXT,
  resolved_by BIGINT REFERENCES users(id),
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE attachments (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  file_id BIGINT NOT NULL REFERENCES files(id),
  owner_type VARCHAR(40) NOT NULL,
  owner_id BIGINT NOT NULL,
  attachment_type VARCHAR(40) NOT NULL,
  expires_on DATE,
  created_by BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_attachments_owner ON attachments(owner_type, owner_id);

CREATE TABLE audit_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id BIGINT REFERENCES users(id),
  action VARCHAR(40) NOT NULL,
  object_type VARCHAR(50) NOT NULL,
  object_id BIGINT,
  before_data JSONB,
  after_data JSONB,
  request_id VARCHAR(80),
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_logs_object ON audit_logs(object_type, object_id, created_at DESC);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id, created_at DESC);

INSERT INTO roles (code, name, level, description) VALUES
  ('staff', '一级员工', 1, '录入工资和返费等原始业务数据'),
  ('finance', '二级财务', 2, '审核财务数据'),
  ('owner', '三级老板', 3, '最终确认并查看经营利润'),
  ('admin', '系统管理员', 9, '维护账号、权限和系统配置');

INSERT INTO system_settings (key, value, description) VALUES
  ('contract.unsigned_warning_days', '20', '入职后未签合同预警天数'),
  ('contract.expiry_warning_days', '15', '合同到期前预警天数'),
  ('receivable.default_overdue_days', '30', '默认回款逾期阈值');

COMMIT;
