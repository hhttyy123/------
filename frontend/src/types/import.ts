// API 响应类型定义 —— 对应后端 Pydantic schemas

export interface SheetInfo {
  name: string
  row_count: number
  column_count: number
  headers: string[]
}

export interface UploadResponse {
  upload_id: string
  filename: string
  sheets: SheetInfo[]
  sheet_count: number
}

export interface Classification {
  module: string
  module_label: string
  confidence: number
  reasoning?: string
  alternative_modules?: { module: string; module_label: string; confidence: number }[]
}

export interface FieldMapping {
  column_index: number
  original_header: string
  mapped_field: string | null
  field_label: string | null
  confidence: number
  reasoning?: string
  suggested_alternatives?: string[]
}

export interface ValueSampleItem {
  original: string
  converted: string | number | null
  needs_review: boolean
}

export interface ValueSample {
  column_index: number
  field_key: string
  field_label: string
  samples: ValueSampleItem[]
}

export interface WarningItem {
  type: string
  message: string
  severity: 'info' | 'warning' | 'error'
  details?: string
}

export interface AnalysisResponse {
  upload_id: string
  sheet_name: string
  classification: Classification
  header_row_index: number
  field_mappings: FieldMapping[]
  value_samples: ValueSample[]
  warnings: WarningItem[]
  preview_rows: Record<string, string | number>[]
  total_rows?: number
}

export interface ConfirmedMapping {
  column_index: number
  mapped_field: string | null
}

export interface ImportRequest {
  upload_id: string
  sheet_name: string
  confirmed_module: string
  confirmed_mappings: ConfirmedMapping[]
  header_row_index: number
}

export interface ImportError {
  row: number
  message: string
  data?: Record<string, string>
}

export interface ImportResponse {
  import_id: string
  module: string
  total_rows: number
  imported_rows: number
  skipped_rows: number
  error_rows: number
  errors: ImportError[]
  summary: Record<string, unknown>
}

export interface PreviewResponse {
  upload_id: string
  sheet_name: string
  headers: string[]
  rows: string[][]
  total_rows: number
  preview_rows: number
  header_row: number
}

export interface AnalyzeAllSheetResult {
  sheet_name: string
  classification: Classification
  header_row_index?: number
  field_mappings: FieldMapping[]
  preview_rows: Record<string, unknown>[]
  total_rows?: number
  _debug?: Record<string, unknown>
  error?: string
}

export interface AnalyzeAllResponse {
  upload_id: string
  results: AnalyzeAllSheetResult[]
}

export type WizardStep = 'idle' | 'preview' | 'analyzing' | 'done'

export interface ModuleField {
  field_key: string
  field_label: string
  field_type: string
  required: boolean
  unique: boolean
  aliases: string[]
  description: string
  enum_values?: string[]
}

export interface ModuleMeta {
  module: string
  module_label: string
  description: string
  fields: ModuleField[]
  record_count: number
}

export interface ImportIssue {
  row_index: number
  field: string
  field_label: string
  severity: 'blocker' | 'warning'
  message: string
  original_value: unknown
  suggested_value: unknown
}

export interface ImportBatch {
  batch_id: string
  filename: string
  upload_id: string
  module: string
  module_label: string
  sheet_name: string
  status: 'prepared' | 'committed' | 'failed'
  rows_total: number
  rows_ready: number
  rows_blocked: number
  records: Record<string, unknown>[]
  display_records?: Record<string, unknown>[]
  targets?: ImportTarget[]
  sheet_reports?: SheetReport[]
  issues: ImportIssue[]
  fingerprint: string
  cache_hit: boolean
  header_row_index: number
  committed_rows?: number
  commit_errors?: Array<{ module?: string; row_index?: number; message: string }>
  created_at: string
  committed_at?: string
  _debug?: Record<string, unknown>
}

export interface ImportChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ImportChatResponse {
  answer: string
  context_scope: string
  batch_id: string
}

export interface ImportTarget {
  module: string
  module_label: string
  sheet_name: string
  selected: boolean
  rows_total: number
  rows_ready: number
  rows_blocked: number
  records: Record<string, unknown>[]
  display_records: Record<string, unknown>[]
  issues: ImportIssue[]
}

export interface SheetReport {
  sheet_name: string
  status: 'ready' | 'skipped'
  message: string
  rows_total: number
  targets: Array<{ module: string; module_label: string; rows_ready: number; rows_blocked: number }>
}

export interface DashboardSummary {
  active_employees: number
  month_receivable: number
  month_salary: number
  month_profit: number
  warning_count: number
  approval_count: number
  current_month: string
}

export interface WarningRecord {
  type: string
  module: string
  record_id?: number
  title: string
  message: string
  severity: 'info' | 'warning' | 'error'
}

export interface DatasetColumn {
  key: string
  label: string
  type: string
  visible: boolean
}

export interface DatasetIndexItem {
  dataset_id: string
  name: string
  category?: string
  source_file: string
  sheet_name: string
  row_count: number
  column_count: number
  created_at: string
  updated_at: string
}

export interface Dataset {
  dataset_id: string
  name: string
  category?: string
  source_file: string
  upload_id: string
  sheet_name: string
  header_row: number
  columns: DatasetColumn[]
  rows: Record<string, unknown>[]
  created_at: string
  updated_at: string
}

export interface DatasetPreview {
  upload_id: string
  sheet_name: string
  header_row: number
  columns: DatasetColumn[]
  rows: Record<string, unknown>[]
  total_rows: number
}

export interface DatasetRowsResult {
  dataset_id: string
  columns: DatasetColumn[]
  total: number
  rows: Record<string, unknown>[]
}

export interface DatasetFilter {
  field: string
  operator: string
  value?: unknown
}

export interface DatasetAggregation {
  field: string
  type: 'sum'
}

export interface DatasetQueryRequest {
  filters: DatasetFilter[]
  group_by: string[]
  aggregations: DatasetAggregation[]
  limit: number
}

export interface DatasetQueryResult {
  total: number
  rows: Record<string, unknown>[]
  summary: Record<string, { sum: number; avg: number; count: number }>
  groups: Record<string, unknown>[]
}
