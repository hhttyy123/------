import type {
  Dataset,
  DatasetIndexItem,
  DatasetPreview,
  DatasetQueryRequest,
  DatasetQueryResult,
  DatasetRowsResult,
  UploadResponse,
} from '@/types/import'

const API_PREFIX = import.meta.env.DEV ? '' : import.meta.env.VITE_API_PREFIX || ''
const AUTH_BASE = `${API_PREFIX}/api/auth`
const BASE_URL = `${API_PREFIX}/api/v1`
const V2_BASE_URL = `${API_PREFIX}/api/v2`
const authHeaders = (): Record<string,string> => {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
export type AuthUser = { id:number;username:string;display_name:string }
export type SystemUser={id:number;username:string;display_name:string;status:string;role_code:'staff'|'finance'|'owner'|'admin';role_name:string}
export async function authStatus():Promise<{initialized:boolean}>{const r=await fetch(`${AUTH_BASE}/status`);return r.json()}
export async function authenticate(mode:'login'|'bootstrap',data:{username:string;password:string;display_name?:string}):Promise<{token:string;user:AuthUser}>{const r=await fetch(`${AUTH_BASE}/${mode}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const x=await r.json();if(!r.ok)throw new Error(x.detail||'登录失败');return x}
export async function currentUser():Promise<AuthUser>{const r=await fetch(`${AUTH_BASE}/me`,{headers:authHeaders()});if(!r.ok)throw new Error('unauthorized');return r.json()}
export async function logout():Promise<void>{await fetch(`${AUTH_BASE}/logout`,{method:'POST'});localStorage.removeItem('auth_token')}
export async function listSystemUsers():Promise<{rows:SystemUser[]}>{const r=await fetch(`${AUTH_BASE}/users`,{headers:authHeaders()});const x=await r.json();if(!r.ok)throw new Error(x.detail);return x}
export async function createSystemUser(data:{username:string;password:string;display_name:string;role_code:string}):Promise<{id:number}>{const r=await fetch(`${AUTH_BASE}/users`,{method:'POST',headers:{'Content-Type':'application/json',...authHeaders()},body:JSON.stringify(data)});const x=await r.json();if(!r.ok)throw new Error(x.detail);return x}
export async function changeSystemUserRole(id:number,role:string):Promise<void>{const r=await fetch(`${AUTH_BASE}/users/${id}/role?role_code=${role}`,{method:'PATCH',headers:authHeaders()});if(!r.ok)throw new Error((await r.json()).detail)}
function downloadFilename(header: string | null): string {
  const encoded = header?.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) return decodeURIComponent(encoded)
  return header?.match(/filename="?([^";]+)/i)?.[1] || 'export.xlsx'
}
export async function downloadAuthenticated(url:string):Promise<void>{const r=await fetch(url,{headers:authHeaders()});if(!r.ok)throw new Error('导出失败');const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=downloadFilename(r.headers.get('content-disposition'));a.click();URL.revokeObjectURL(a.href)}

export type DashboardSummary = {
  active_employees: number
  active_companies: number
  journal_count: number
  month_income: number
  month_expense: number
  month_profit: number
  approval_count: number
  warnings: DashboardWarning[]
  current_month: string
}

export type DashboardWarning = {
  type: string
  title: string
  message: string
  severity: 'info' | 'warning'
}

export type StagedImportRow = {
  id: number
  sheet_name: string
  source_row: number
  source_region: string
  normalized_data: Record<string, unknown>
  status: 'ready' | 'warning' | 'blocked' | 'committed'
  issues: Array<{ field: string; severity: string; message: string }>
}

export type StagedImportBatch = {
  batch_id: number
  module: string
  status: string
  total_rows: number
  ready_rows: number
  warning_rows: number
  blocked_rows: number
  created_at: string
  committed_at?: string | null
  rows?: StagedImportRow[]
}

export type JournalTransaction = {
  id: number
  transaction_date: string
  ledger_type: 'cash' | 'bank'
  direction: 'income' | 'expense'
  category: string
  amount: number
  payment_method?: string | null
  company_id?: number | null
  employee_id?: number | null
  summary?: string | null
  status: string
  source_import_row_id?: number | null
}

export type JournalListResult = {
  rows: JournalTransaction[]
  total: number
  page: number
  page_size: number
  income_total: number
  expense_total: number
  net_flow: number
}

export type CompanyRecord = { id: number; name: string; contact_person?: string | null; contact_phone?: string | null; address?: string | null; business_license_no?: string | null; cooperation_status: 'active' | 'paused' | 'terminated'; cooperation_start_date?: string | null; cooperation_end_date?: string | null; default_receivable_days?: number | null; remark?: string | null }
export type PositionRecord = { id: number; company_id: number; company_name: string; name: string; description?: string | null; daily_rate?: number | null; required_count?: number | null; status: 'recruiting' | 'filled' | 'closed' }
export type EmployeeRecord = { id:number;name:string;id_card_masked:string;phone:string;gender:'male'|'female';address?:string;status:string;company_id:number;company_name:string;position_id?:number|null;position_name:string;entry_date:string;contract_count:number }
export type ContractRecord={id:number;employee_id:number;contract_type:string;contract_no?:string|null;sign_date?:string|null;start_date:string;end_date:string;status:string;remark?:string|null}
export type EmployeeDetail={employee:EmployeeRecord;contracts:ContractRecord[];attendance:Array<{work_date:string;status:string;hours:number;deduction_amount:number;remark?:string|null}>;payroll:Array<{salary_month:string;pay_date?:string|null;status:string;base_salary:number;allowance:number;deduction:number;net_pay:number;remark?:string|null}>}
export type AttendanceRecord={id:number;employee_id:number;employee_name:string;work_date:string;status:'normal'|'late'|'absent'|'leave';hours:number;deduction_amount:number;remark?:string|null}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

async function requestV2<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${V2_BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Upload failed: ${res.status}`)
  }
  return res.json()
}

export async function previewDatasetSheet(uploadId: string, sheetName: string, headerRow?: number): Promise<DatasetPreview> {
  const params = new URLSearchParams({ limit: '100' })
  if (headerRow !== undefined) params.set('header_row', String(headerRow))
  return request<DatasetPreview>(`/simple-import/${uploadId}/sheets/${encodeURIComponent(sheetName)}/preview?${params}`)
}

export async function createDatasetFromSheet(payload: {
  upload_id: string
  sheet_name: string
  name?: string
  header_row?: number
  category?: string
}): Promise<Dataset> {
  return request<Dataset>('/datasets', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createWorkbookDataset(payload: {
  upload_id: string
  name: string
  category: string
}): Promise<Dataset> {
  return request<Dataset>('/datasets/from-workbook', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listDatasets(): Promise<{ datasets: DatasetIndexItem[] }> {
  return request<{ datasets: DatasetIndexItem[] }>('/datasets')
}

export async function getDataset(datasetId: string): Promise<Dataset> {
  return request<Dataset>(`/datasets/${datasetId}`)
}

export async function updateDataset(datasetId: string, name: string, category?: string): Promise<Dataset> {
  return request<Dataset>(`/datasets/${datasetId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name, category }),
  })
}

export async function deleteDataset(datasetId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/datasets/${datasetId}`, { method: 'DELETE' })
}

export async function listDatasetRows(datasetId: string, search = '', limit = 500, offset = 0): Promise<DatasetRowsResult> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (search) params.set('search', search)
  return request<DatasetRowsResult>(`/datasets/${datasetId}/rows?${params}`)
}

export async function createDatasetRow(datasetId: string, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/datasets/${datasetId}/rows`, {
    method: 'POST',
    body: JSON.stringify({ data }),
  })
}

export async function updateDatasetRow(datasetId: string, rowId: number, data: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/datasets/${datasetId}/rows/${rowId}`, {
    method: 'PATCH',
    body: JSON.stringify({ data }),
  })
}

export async function deleteDatasetRow(datasetId: string, rowId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/datasets/${datasetId}/rows/${rowId}`, { method: 'DELETE' })
}

export async function queryDataset(datasetId: string, payload: DatasetQueryRequest): Promise<DatasetQueryResult> {
  return request<DatasetQueryResult>(`/datasets/${datasetId}/query`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function exportDatasetUrl(datasetId: string): string {
  return `${BASE_URL}/datasets/${datasetId}/export`
}

export async function clearRecords(): Promise<{ ok: boolean; cleared_modules: string[]; cleared_batches: number }> {
  return request<{ ok: boolean; cleared_modules: string[]; cleared_batches: number }>('/maintenance/clear-records', {
    method: 'POST',
  })
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return requestV2<DashboardSummary>('/dashboard/summary')
}

export async function stageJournalImport(payload: {
  upload_id: string
  sheet_name: string
  header_row?: number
}): Promise<StagedImportBatch> {
  return requestV2<StagedImportBatch>('/imports/journal/stage', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getStagedImportBatch(batchId: number): Promise<StagedImportBatch> {
  return requestV2<StagedImportBatch>(`/imports/batches/${batchId}`)
}

export async function commitStagedImport(batchId: number): Promise<{ batch_id: number; status: string; imported_rows: number }> {
  return requestV2(`/imports/batches/${batchId}/commit`, { method: 'POST' })
}

export async function listJournalTransactions(filters: {
  direction?: 'income' | 'expense'
  ledger_type?: 'cash' | 'bank'
  date_from?: string
  date_to?: string
  search?: string
  page?: number
  page_size?: number
} = {}): Promise<JournalListResult> {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value))
  })
  return requestV2(`/journal?${params}`)
}

export async function createJournalTransaction(data: Omit<JournalTransaction, 'id' | 'status' | 'source_import_row_id'>): Promise<JournalTransaction> {
  return requestV2('/journal', { method: 'POST', body: JSON.stringify(data) })
}

export async function updateJournalTransaction(id: number, data: Partial<JournalTransaction>): Promise<JournalTransaction> {
  return requestV2(`/journal/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function voidJournalTransaction(id: number): Promise<{ ok: boolean }> {
  return requestV2(`/journal/${id}`, { method: 'DELETE' })
}

export function journalExportUrl(filters: { direction?: string; date_from?: string; date_to?: string; search?: string } = {}): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value)
  })
  return `${V2_BASE_URL}/journal/export/file.xlsx?${params}`
}

export async function listCompanies(search = '', status = '', page = 1, page_size = 30): Promise<{ rows: CompanyRecord[]; total: number; page: number; page_size: number }> { const p = new URLSearchParams({ page: String(page), page_size: String(page_size) }); if (search) p.set('search', search); if (status) p.set('status', status); return requestV2(`/companies?${p}`) }
export async function createCompany(data: Partial<CompanyRecord>): Promise<CompanyRecord> { return requestV2('/companies', { method: 'POST', body: JSON.stringify(data) }) }
export async function updateCompany(id: number, data: Partial<CompanyRecord>): Promise<CompanyRecord> { return requestV2(`/companies/${id}`, { method: 'PATCH', body: JSON.stringify(data) }) }
export async function deleteCompanyRecord(id: number): Promise<{ ok: boolean }> { return requestV2(`/companies/${id}`, { method: 'DELETE' }) }
export function companiesExportUrl(): string { return `${V2_BASE_URL}/companies/export/file.xlsx` }
export async function listPositions(companyId?: number, page = 1, page_size = 100): Promise<{ rows: PositionRecord[]; total: number; page: number; page_size: number }> { return requestV2(`/companies/positions/list?${new URLSearchParams({ page: String(page), page_size: String(page_size), ...(companyId ? { company_id: String(companyId) } : {}) })}`) }
export async function createPosition(data: Partial<PositionRecord>): Promise<PositionRecord> { return requestV2('/companies/positions', { method: 'POST', body: JSON.stringify(data) }) }
export async function updatePosition(id: number, data: Partial<PositionRecord>): Promise<PositionRecord> { return requestV2(`/companies/positions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }) }
export async function deletePositionRecord(id: number): Promise<{ ok: boolean }> { return requestV2(`/companies/positions/${id}`, { method: 'DELETE' }) }
export function positionsExportUrl(): string { return `${V2_BASE_URL}/companies/positions/export/file.xlsx` }
export async function stageCompanyImport(payload: { upload_id: string; sheet_name: string; header_row?: number }): Promise<StagedImportBatch> { return requestV2('/imports/company/stage', { method: 'POST', body: JSON.stringify(payload) }) }
export async function commitStagedCompanies(batchId: number): Promise<{ batch_id: number; status: string; imported_rows: number }> { return requestV2(`/imports/batches/${batchId}/commit-companies`, { method: 'POST' }) }
export async function stageEmployeeImport(payload:{upload_id:string;sheet_name:string;header_row?:number}):Promise<StagedImportBatch>{return requestV2('/imports/employee/stage',{method:'POST',body:JSON.stringify(payload)})}
export async function commitStagedEmployees(batchId:number):Promise<{batch_id:number;status:string;imported_rows:number}>{return requestV2(`/imports/batches/${batchId}/commit-employees`,{method:'POST'})}
export async function stagePositionImport(payload:{upload_id:string;sheet_name:string;header_row?:number}):Promise<StagedImportBatch>{return requestV2('/imports/position/stage',{method:'POST',body:JSON.stringify(payload)})}
export async function commitStagedPositions(batchId:number):Promise<{batch_id:number;status:string;imported_rows:number}>{return requestV2(`/imports/batches/${batchId}/commit-positions`,{method:'POST'})}
export async function stageContractImport(payload:{upload_id:string;sheet_name:string;header_row?:number}):Promise<StagedImportBatch>{return requestV2('/imports/contract/stage',{method:'POST',body:JSON.stringify(payload)})}
export async function commitStagedContracts(batchId:number):Promise<{batch_id:number;status:string;imported_rows:number}>{return requestV2(`/imports/batches/${batchId}/commit-contracts`,{method:'POST'})}
export async function stageAttendanceImport(payload:{upload_id:string;sheet_name:string;header_row?:number}):Promise<StagedImportBatch>{return requestV2('/imports/attendance/stage',{method:'POST',body:JSON.stringify(payload)})}
export async function commitStagedAttendance(batchId:number):Promise<{batch_id:number;status:string;imported_rows:number}>{return requestV2(`/imports/batches/${batchId}/commit-attendance`,{method:'POST'})}
export async function stageJournalWorkbook(upload_id:string):Promise<StagedImportBatch>{return requestV2('/imports/journal/stage-workbook',{method:'POST',body:JSON.stringify({upload_id})})}
export function contractsExportUrl():string{return `${V2_BASE_URL}/employees/contracts/export/file.xlsx`}
export async function listEmployees(search='',page=1,page_size=30):Promise<{rows:EmployeeRecord[];total:number;page:number;page_size:number}>{return requestV2(`/employees?${new URLSearchParams({search,page:String(page),page_size:String(page_size)})}`)}
export async function createEmployee(data:Record<string,unknown>):Promise<EmployeeRecord>{return requestV2('/employees',{method:'POST',body:JSON.stringify(data)})}
export async function updateEmployee(id:number,data:Record<string,unknown>):Promise<EmployeeRecord>{return requestV2(`/employees/${id}`,{method:'PATCH',body:JSON.stringify(data)})}
export async function leaveEmployee(id:number,date:string):Promise<{ok:boolean}>{return requestV2(`/employees/${id}/leave?leave_date=${date}`,{method:'POST'})}
export async function getEmployeeDetail(id:number):Promise<EmployeeDetail>{return requestV2(`/employees/${id}/detail`)}
export async function listUnsignedContractWarnings():Promise<{rows:Array<{employee_id:number;employee_name:string;entry_date:string;days_worked:number}>}>{return requestV2('/employees/warnings/unsigned-contract')}
export async function listContracts(employeeId?:number,page=1,page_size=30):Promise<{rows:ContractRecord[];total:number;page:number;page_size:number}>{return requestV2(`/employees/contracts/list?${new URLSearchParams({page:String(page),page_size:String(page_size),...(employeeId?{employee_id:String(employeeId)}:{})})}`)}
export async function createContract(data:Partial<ContractRecord>&{company_id?:number|null}):Promise<{id:number}>{return requestV2('/employees/contracts',{method:'POST',body:JSON.stringify(data)})}
export async function updateContract(id:number,data:Partial<ContractRecord>):Promise<{id:number}>{return requestV2(`/employees/contracts/${id}`,{method:'PATCH',body:JSON.stringify(data)})}
export async function terminateContract(id:number):Promise<{ok:boolean}>{return requestV2(`/employees/contracts/${id}`,{method:'DELETE'})}
export async function listContractExpiryWarnings():Promise<{rows:Array<{contract_id:number;employee_name:string;end_date:string;days_left:number}>}>{return requestV2('/employees/warnings/contract-expiry')}
export async function listAttendance(page=1,page_size=30):Promise<{rows:AttendanceRecord[];total:number;page:number;page_size:number}>{return requestV2(`/attendance?page=${page}&page_size=${page_size}`)}
export async function createAttendance(data:Omit<AttendanceRecord,'id'|'employee_name'>):Promise<{id:number}>{return requestV2('/attendance',{method:'POST',body:JSON.stringify(data)})}
export async function updateAttendance(id:number,data:Omit<AttendanceRecord,'id'|'employee_name'>):Promise<{ok:boolean}>{return requestV2(`/attendance/${id}`,{method:'PATCH',body:JSON.stringify(data)})}
export async function deleteAttendance(id:number):Promise<{ok:boolean}>{return requestV2(`/attendance/${id}`,{method:'DELETE'})}
export function attendanceExportUrl():string{return `${V2_BASE_URL}/attendance/export/file.xlsx`}
export function employeesExportUrl():string{return `${V2_BASE_URL}/employees/export/file.xlsx`}
export async function listFinanceModule(module:string,page=1,page_size=30):Promise<{rows:Array<Record<string,unknown>>;total:number;page:number;page_size:number}>{return requestV2(`/finance/${module}?page=${page}&page_size=${page_size}`)}
export async function createFinanceRecord(module:string,data:Record<string,unknown>):Promise<{id:number}>{return requestV2(`/finance/${module}`,{method:'POST',body:JSON.stringify(data)})}
export async function approveFinanceRecord(module:string,id:number):Promise<{status:string}>{return requestV2(`/finance/${module}/${id}/approve`,{method:'POST'})}
export async function updateFinanceRecord(module:string,id:number,data:Record<string,unknown>):Promise<{ok:boolean}>{return requestV2(`/finance/${module}/${id}`,{method:'PATCH',body:JSON.stringify(data)})}
export async function deleteFinanceRecord(module:string,id:number):Promise<{ok:boolean}>{return requestV2(`/finance/${module}/${id}`,{method:'DELETE'})}
export function financeExportUrl(module:string):string{return `${V2_BASE_URL}/finance/${module}/export`}
export async function importFinance(module:string,upload_id:string,sheet_name:string):Promise<{imported_rows:number;errors:Array<{row:number;error:string}>}>{return requestV2(`/finance/${module}/import`,{method:'POST',body:JSON.stringify({upload_id,sheet_name})})}
export async function profitSummary(dateFrom:string,dateTo:string):Promise<Record<string,number>>{return requestV2(`/finance/profit/summary?date_from=${dateFrom}&date_to=${dateTo}`)}

export async function askAdvisor(question: string, history: Array<{role: string; content: string}> = []): Promise<{answer: string; tools_used?: string[]}> {
  return requestV2('/advisor/ask', { method: 'POST', body: JSON.stringify({ question, history }) })
}

export type ProfitMonthlyRow = { month: string; income: number; expense: number; net_profit: number }
export type ProfitMonthlyResult = { rows: ProfitMonthlyRow[]; summary: { total_income: number; total_expense: number; net_profit: number } }
export async function profitMonthly(dateFrom: string, dateTo: string): Promise<ProfitMonthlyResult> {
  return requestV2<ProfitMonthlyResult>(`/finance/profit/monthly?date_from=${dateFrom}&date_to=${dateTo}`)
}

export type ReconciliationItem = { source_type: string; source_id: number; source_label: string; ref_date: string; expected_amount: number; journal_amount: number; difference: number; issue: string }
export type ReconciliationResult = { items: ReconciliationItem[]; total: number; ok: boolean }
export async function getReconciliation(dateFrom?: string, dateTo?: string): Promise<ReconciliationResult> {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return requestV2<ReconciliationResult>(`/reconciliation/check?${params}`)
}

export type OverdueItem = { id: number; company_name: string; expected_date: string; amount: number; received_amount: number; remaining: number; overdue_days: number; status: string; remark: string }
export type OverdueResult = { items: OverdueItem[]; total: number; total_remaining: number }
export async function getOverdueReceivables(): Promise<OverdueResult> {
  return requestV2<OverdueResult>('/overdue/receivables')
}

export type ApprovalItem = { id: number; module: string; label: string; ref_date: string; amount: number; status: string }
export type ApprovalListResult = { items: ApprovalItem[]; total: number }
export async function listPendingApprovals(): Promise<ApprovalListResult> {
  return requestV2<ApprovalListResult>('/approvals/pending')
}

export type ClearByDateRequest = { module: string; date_from: string; date_to: string }
export type ClearByDateResponse = { ok: boolean; affected: number; module: string; date_from: string; date_to: string }
export async function clearByDateRange(payload: ClearByDateRequest): Promise<ClearByDateResponse> {
  return requestV2<ClearByDateResponse>('/maintenance/clear', { method: 'POST', body: JSON.stringify(payload) })
}
