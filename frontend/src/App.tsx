import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  AlertCircle,
  LogOut,
  CheckCircle2,
  ArrowDownLeft,
  ArrowUpRight,
  Bell,
  Bot,
  Building2,
  CalendarRange,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  ClipboardCheck,
  Database,
  Download,
  Edit3,
  FileSpreadsheet,
  Home,
  Loader2,
  Plus,
  Search,
  Settings,
  Trash2,
  TriangleAlert,
  Upload,
  Users,
  WalletCards,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  changeSystemUserRole,
  authenticate,
  authStatus,
  commitStagedCompanies,
  commitStagedEmployees,
  commitStagedImport,
  commitStagedPositions,
  stageContractImport,
  commitStagedContracts,
  stageAttendanceImport,
  commitStagedAttendance,
  stageJournalWorkbook,
  contractsExportUrl,
  attendanceExportUrl,
  employeesExportUrl,
  companiesExportUrl,
  createCompany,
  createAttendance,
  createFinanceRecord,
  deleteFinanceRecord,
  createSystemUser,
  createContract,
  createEmployee,
  createJournalTransaction,
  createPosition,
  createDatasetFromSheet,
  createWorkbookDataset,
  createDatasetRow,
  deleteDataset,
  deleteDatasetRow,
  deleteCompanyRecord,
  deleteAttendance,
  deletePositionRecord,
  positionsExportUrl,
  downloadAuthenticated,
  getDataset,
  getDashboardSummary,
  currentUser,
  getEmployeeDetail,
  getStagedImportBatch,
  journalExportUrl,
  leaveEmployee,
  listDatasetRows,
  listDatasets,
  listAttendance,
  listFinanceModule,
  importFinance,
  listCompanies,
  listContractExpiryWarnings,
  listContracts,
  listEmployees,
  listJournalTransactions,
  listPositions,
  listUnsignedContractWarnings,
  listSystemUsers,
  logout,
  previewDatasetSheet,
  queryDataset,
  stageJournalImport,
  stageCompanyImport,
  stageEmployeeImport,
  stagePositionImport,
  updateDataset,
  updateDatasetRow,
  updateCompany,
  updateAttendance,
  approveFinanceRecord,
  updateFinanceRecord,
  financeExportUrl,
  updateContract,
  updateEmployee,
  updateJournalTransaction,
  updatePosition,
  uploadFile,
  terminateContract,
  voidJournalTransaction,
  getReconciliation,
  getOverdueReceivables,
  listPendingApprovals,
  askAdvisor,
  profitMonthly,
  clearByDateRange,
} from "@/api/importApi";
import type {
  ProfitMonthlyResult,
  AttendanceRecord,
  AuthUser,
  CompanyRecord,
  ContractRecord,
  DashboardSummary,
  EmployeeDetail,
  EmployeeRecord,
  JournalTransaction,
  PositionRecord,
  StagedImportBatch,
  SystemUser,
} from "@/api/importApi";
import type {
  Dataset,
  DatasetColumn,
  DatasetFilter,
  DatasetIndexItem,
  DatasetPreview,
  DatasetQueryResult,
  UploadResponse,
} from "@/types/import";

const MODULES = [
  { key: "employee", label: "人员管理" },
  { key: "company", label: "企业管理" },
  { key: "position", label: "岗位管理" },
  { key: "contract", label: "合同管理" },
  { key: "attendance", label: "考勤管理" },
  { key: "salary", label: "工资发放" },
  { key: "rebate", label: "代招返费" },
  { key: "payment", label: "回款管理" },
  { key: "receivable", label: "应收管理" },
  { key: "overdue", label: "回款跟进" },
  { key: "invoice", label: "开票管理" },
  { key: "journal", label: "日记账" },
  { key: "approvals", label: "审批中心" },
  { key: "reconciliation", label: "核对中心" },
  { key: "profit", label: "利润核算" },
  { key: "other", label: "其他表格" },
];

const NAV_GROUPS = [
  {
    key: "people",
    label: "人员与用工",
    icon: Users,
    modules: ["employee", "attendance", "contract"],
  },
  {
    key: "business",
    label: "企业与合作",
    icon: Building2,
    modules: ["company", "position", "payment", "receivable", "overdue", "invoice"],
  },
  {
    key: "finance",
    label: "财务与薪资",
    icon: WalletCards,
    modules: ["salary", "rebate", "approvals", "journal", "reconciliation", "profit", "other"],
  },
] as const;

const OPERATORS = [
  { value: "contains", label: "包含" },
  { value: "not_contains", label: "不包含" },
  { value: "eq", label: "等于" },
  { value: "ne", label: "不等于" },
  { value: "gt", label: "大于" },
  { value: "gte", label: "大于等于" },
  { value: "lt", label: "小于" },
  { value: "lte", label: "小于等于" },
  { value: "empty", label: "为空" },
  { value: "not_empty", label: "不为空" },
  { value: "between", label: "区间" },
];

type Mode = "table" | "query";
type Page = "home" | "data" | "advisor" | "settings";

function LoginPage({
  onAuthenticated,
}: {
  onAuthenticated: (user: AuthUser) => void;
}) {
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    authStatus()
      .then((x) => setInitialized(x.initialized))
      .catch(() => setError("无法连接服务器"));
  }, []);
  const submit = async () => {
    if (initialized === null) return;
    setBusy(true);
    setError("");
    try {
      const result = await authenticate(initialized ? "login" : "bootstrap", {
        username,
        password,
        display_name: displayName,
      });
      localStorage.setItem("auth_token", result.token);
      onAuthenticated(result.user);
    } catch (e) {
      setError(readError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#e9efe9] p-6">
      <div className="absolute inset-0 opacity-40 [background-image:radial-gradient(#829b87_0.7px,transparent_0.7px)] [background-size:18px_18px]" />
      <div className="relative grid w-full max-w-4xl overflow-hidden rounded-3xl border border-white/70 bg-white shadow-[0_30px_90px_rgba(29,55,37,.18)] md:grid-cols-[1.05fr_.95fr]">
        <div className="hidden bg-[#173f2a] p-12 text-white md:flex md:flex-col md:justify-center">
          <h1 className="text-5xl font-bold tracking-tight">曼克斯</h1>
          <p className="mt-2 text-xl font-light text-white/80">劳务派遣经营管理</p>
          <div className="mt-8 space-y-3 text-sm text-white/60">
            <p>· 人员档案 · 合同管理 · 考勤记录</p>
            <p>· 工资发放 · 代招返费 · 回款跟进</p>
            <p>· 现金及银行日记账</p>
            <p>· 利润核算 · 审批 · 数据核对</p>
          </div>
        </div>
        <div className="p-8 md:p-12">
          <h2 className="text-xl font-semibold text-[#1f3326]">
            {initialized === false ? "创建管理员账号" : "登录"}
          </h2>
          <div className="mt-8 space-y-4">
            {initialized === false && (
              <JournalField label="管理员姓名">
                <input
                  className="journal-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </JournalField>
            )}
            <JournalField label="账号">
              <input
                autoComplete="username"
                className="journal-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </JournalField>
            <JournalField label="密码（至少10位）">
              <input
                type="password"
                autoComplete={initialized ? "current-password" : "new-password"}
                className="journal-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submit();
                }}
              />
            </JournalField>
            {error && (
              <div className="rounded-lg bg-[#fff0ed] px-3 py-2 text-xs text-[#b74734]">
                {error}
              </div>
            )}
            <Button
              className="h-11 w-full bg-[#173f2a] hover:bg-[#245c3c]"
              disabled={
                busy ||
                initialized === null ||
                username.length < 3 ||
                password.length < 10 ||
                (initialized === false && !displayName)
              }
              onClick={submit}
            >
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {initialized === false ? "创建并进入系统" : "登录"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null | undefined>(
    undefined,
  );
  const [datasets, setDatasets] = useState<DatasetIndexItem[]>([]);
  const [activeId, setActiveId] = useState("");
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [activeModule, setActiveModule] = useState("employee");
  const [activePage, setPage] = useState<Page>(() => {
    const hash = window.location.hash?.replace("#", "");
    if (hash.startsWith("data-")) {
      setActiveModule(hash.replace("data-", "")); // deferred, works because this is init
      return "data";
    }
    if (["home","data","advisor","settings"].includes(hash)) return hash as Page;
    return "home";
  });
  const goPage = (page: Page) => { window.location.hash = page; setPage(page); };
  const goModule = (module: string) => { window.location.hash = `data-${module}`; setActiveModule(module); setPage("data"); };
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    people: true,
    business: true,
    finance: true,
  });
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("table");
  const [importOpen, setImportOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<Record<string, unknown> | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clearModule, setClearModule] = useState<string | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState(0);

  useEffect(() => {
    currentUser()
      .then(setAuthUser)
      .catch(() => setAuthUser(null));
  }, []);

  const grouped = useMemo(() => groupDatasets(datasets), [datasets]);

  const refreshDatasets = useCallback(async (preferredId?: string | null) => {
    const result = await listDatasets();
    setDatasets(result.datasets);
    setActiveId((currentId) => {
      if (preferredId === null) return currentId;
      if (preferredId === "__first__")
        return result.datasets[0]?.dataset_id || "";
      if (preferredId !== undefined) {
        return result.datasets.some((item) => item.dataset_id === preferredId)
          ? preferredId
          : "";
      }
      return currentId &&
        result.datasets.some((item) => item.dataset_id === currentId)
        ? currentId
        : "";
    });
  }, []);

  const loadDataset = useCallback(
    async (id: string, keyword = search) => {
      if (!id) {
        setDataset(null);
        setRows([]);
        setTotalRows(0);
        return;
      }
      const [detail, rowResult] = await Promise.all([
        getDataset(id),
        listDatasetRows(id, keyword, 1000),
      ]);
      setDataset(detail);
      setActiveModule(detail.category || "other");
      setRows(rowResult.rows);
      setTotalRows(rowResult.total);
    },
    [search],
  );

  useEffect(() => {
    if (!authUser) return;
    refreshDatasets().catch((err) => setError(readError(err)));
  }, [authUser, refreshDatasets]);

  useEffect(() => {
    if (!authUser || !activeId) return;
    loadDataset(activeId).catch((err) => setError(readError(err)));
  }, [authUser, activeId, loadDataset]);

  const saveRow = async (data: Record<string, unknown>) => {
    if (!dataset) return;
    if (editingRow?.id) {
      await updateDatasetRow(dataset.dataset_id, Number(editingRow.id), data);
    } else {
      await createDatasetRow(dataset.dataset_id, data);
    }
    setEditorOpen(false);
    setEditingRow(null);
    await loadDataset(dataset.dataset_id, search);
    await refreshDatasets(dataset.dataset_id);
  };

  if (authUser === undefined)
    return (
      <div className="grid min-h-screen place-items-center bg-[#eef2ed]">
        <Loader2 className="h-6 w-6 animate-spin text-[#173f2a]" />
      </div>
    );
  if (!authUser) return <LoginPage onAuthenticated={setAuthUser} />;
  return (
    <div className="h-screen overflow-hidden bg-[#f5f7fa] text-[#1f2329]">
      <header className="flex h-14 items-center justify-between border-b border-[#e5e6eb] bg-white px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-[#165dff] text-white">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold leading-4">曼克斯劳务管理</div>
            <div className="mt-0.5 text-xs text-[#86909c]">
              导入、维护、查询、导出
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="mr-1 hidden text-xs text-[#657169] sm:inline">
            {authUser.display_name}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await logout();
              setAuthUser(null);
            }}
            title="退出登录"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="grid h-[calc(100vh-56px)] grid-cols-[248px_1fr]">
        <aside className="flex min-h-0 flex-col border-r border-[#dfe4e8] bg-[#f8faf9]">
          <div className="px-3 pb-2 pt-3">
            <SidebarMainButton
              icon={Home}
              label="经营首页"
              active={activePage === "home"}
              onClick={() => goPage("home")}
            />
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-3 py-1">
            {NAV_GROUPS.map((group) => {
              const GroupIcon = group.icon;
              const isOpen = openGroups[group.key];
              const groupCount = group.modules.reduce(
                (total, key) => total + (grouped[key]?.length || 0),
                0,
              );
              return (
                <section key={group.key} className="mb-2">
                  <button
                    type="button"
                    onClick={() =>
                      setOpenGroups((current) => ({
                        ...current,
                        [group.key]: !isOpen,
                      }))
                    }
                    className="flex min-h-10 w-full items-center gap-2 rounded-lg px-2 text-left text-sm font-semibold text-[#293238] transition hover:bg-white"
                    aria-expanded={isOpen}
                  >
                    <GroupIcon className="h-4 w-4 text-[#5f6b72]" />
                    <span className="flex-1">{group.label}</span>
                    {groupCount > 0 && (
                      <span className="text-[11px] font-normal text-[#8b969d]">
                        {groupCount}
                      </span>
                    )}
                    {isOpen ? (
                      <ChevronDown className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" />
                    )}
                  </button>
                  {isOpen && (
                    <div className="ml-3 border-l border-[#dfe4e8] pl-2">
                      {group.modules.map((moduleKey) => {
                        const module = MODULES.find(
                          (item) => item.key === moduleKey,
                        );
                        if (!module) return null;
                        const items = grouped[module.key] || [];
                        const moduleActive =
                          activePage === "data" &&
                          activeModule === module.key &&
                          !dataset;
                        return (
                          <div key={module.key} className="py-0.5">
                            <button
                              type="button"
                              onClick={() => {
                                goModule(module.key);
                                setActiveId("");
                                setDataset(null);
                                setRows([]);
                                setTotalRows(0);
                                setMode("table");
                              }}
                              className={`flex min-h-8 w-full items-center justify-between rounded-md px-2 text-sm transition ${
                                moduleActive
                                  ? "bg-[#e8f2ec] font-medium text-[#17633b]"
                                  : "text-[#59656c] hover:bg-white hover:text-[#1f2b31]"
                              }`}
                            >
                              <span>{module.label}</span>
                              {items.length > 0 && (
                                <span className="text-[11px] text-[#98a1a7]">
                                  {items.length}
                                </span>
                              )}
                            </button>
                            {items.map((item) => (
                              <button
                                key={item.dataset_id}
                                type="button"
                                onClick={() => {
                                  goPage("data");
                                  setActiveModule(module.key);
                                  setActiveId(item.dataset_id);
                                  setMode("table");
                                }}
                                className={`mt-0.5 w-full rounded-md py-1.5 pl-4 pr-2 text-left text-xs transition ${
                                  activePage === "data" &&
                                  activeId === item.dataset_id
                                    ? "bg-white font-medium text-[#17633b] shadow-sm ring-1 ring-[#dce8e0]"
                                    : "text-[#7a858c] hover:bg-white hover:text-[#344047]"
                                }`}
                              >
                                <div className="truncate">{item.name}</div>
                                <div className="mt-0.5 text-[10px] text-[#a1a9ae]">
                                  {item.row_count} 条记录
                                </div>
                              </button>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
          <div className="border-t border-[#dfe4e8] p-3">
            <SidebarMainButton
              icon={Bot}
              label="AI 顾问"
              active={activePage === "advisor"}
              onClick={() => goPage("advisor")}
            />
            <div className="mt-1">
              <SidebarMainButton
                icon={Settings}
                label="设置"
                active={activePage === "settings"}
                onClick={() => goPage("settings")}
              />
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col">
          {activePage === "home" ? (
            <DashboardPage
              onGoModule={(m) => { goModule(m); }}
            />
          ) : activePage === "advisor" ? (
            <AdvisorPage setError={setError} />
          ) : activePage === "settings" ? (
            <UserSettingsPage setError={setError} />
          ) : (
            <>
              {dataset && (
              <section className="border-b border-[#e5e6eb] bg-white px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h1 className="truncate text-lg font-semibold">
                        {dataset.name}
                      </h1>
                      <Badge variant="secondary">
                        {moduleLabel(dataset.category)}
                      </Badge>
                    </div>
                    <div className="mt-1 truncate text-xs text-[#86909c]">
                      {dataset.source_file} / {dataset.sheet_name} / {dataset.columns.length} 列 / {totalRows} 行
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={async () => {
                      const name = window.prompt("新的数据集名称", dataset.name);
                      if (!name || name === dataset.name) return;
                      await updateDataset(dataset.dataset_id, name, dataset.category);
                      await refreshDatasets(dataset.dataset_id);
                      await loadDataset(dataset.dataset_id, search);
                    }}><Edit3 className="mr-2 h-4 w-4" />改名</Button>
                    <Button variant="ghost" size="sm" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={async () => {
                      if (!window.confirm(`确定删除「${dataset.name}」吗？`)) return;
                      await deleteDataset(dataset.dataset_id);
                      setActiveId(""); setDataset(null); setRows([]); setTotalRows(0);
                      await refreshDatasets(null);
                    }}><Trash2 className="mr-2 h-4 w-4" />删除</Button>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <div className="flex h-9 w-full max-w-xl items-center gap-2 rounded border border-[#dcdfe6] bg-white px-3 focus-within:border-[#165dff]">
                      <Search className="h-4 w-4 text-[#86909c]" />
                      <input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") loadDataset(activeId, search).catch((err) => setError(readError(err))); }} placeholder="搜索当前数据集的任意字段" className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
                      {search && <button onClick={() => setSearch("")}><X className="h-4 w-4 text-[#86909c]" /></button>}
                    </div>
                    <Button variant="outline" size="sm" disabled={!dataset} onClick={() => loadDataset(activeId, search).catch((err) => setError(readError(err)))}>查询</Button>
                  </div>
                  <div className="flex rounded border border-[#dcdfe6] bg-white p-0.5">
                    <button onClick={() => setMode("table")} className={`h-8 rounded px-3 text-sm ${mode === "table" ? "bg-[#165dff] text-white" : "text-[#4e5969]"}`}>表格</button>
                    <button onClick={() => setMode("query")} className={`h-8 rounded px-3 text-sm ${mode === "query" ? "bg-[#165dff] text-white" : "text-[#4e5969]"}`}>查询分析</button>
                  </div>
                </div>
              </section>
              )}

              {error && (
                <div className="border-b border-[#ffd8d8] bg-[#fff7f7] px-5 py-3">
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                </div>
              )}

              <section className="min-h-0 flex-1 p-4">
                {!dataset ? (
                  activeModule === "journal" ? (
                    <DatabaseJournalPage
                      onImport={() => setImportOpen(true)}
                      setError={setError}
                      legacyCount={(grouped.journal || []).length}
                      reloadTrigger={reloadTrigger}
                      onClear={setClearModule}
                      onOpenLegacy={() => {
                        const first = (grouped.journal || [])[0];
                        if (first) {
                          setActiveId(first.dataset_id);
                          loadDataset(first.dataset_id).catch((err) => setError(readError(err)));
                        }
                      }}
                    />
                  ) : activeModule === "company" ? (
                    <DatabaseCompanyPage
                      onImport={() => setImportOpen(true)}
                      setError={setError}
                      reloadTrigger={reloadTrigger}
                      onClear={setClearModule}
                    />
                  ) : activeModule === "position" ? (
                    <DatabasePositionPage setError={setError} reloadTrigger={reloadTrigger} onClear={setClearModule} onImport={() => setImportOpen(true)} />
                  ) : activeModule === "employee" ? (
                    <DatabaseEmployeePage
                      onImport={() => setImportOpen(true)}
                      setError={setError}
                      reloadTrigger={reloadTrigger}
                      onClear={setClearModule}
                    />
                  ) : activeModule === "attendance" ? (
                    <AttendancePage setError={setError} reloadTrigger={reloadTrigger} onClear={setClearModule} onImport={() => setImportOpen(true)} />
                  ) : activeModule === "contract" ? (
                    <DatabaseContractPage setError={setError} reloadTrigger={reloadTrigger} onClear={setClearModule} onImport={() => setImportOpen(true)} />
                  ) : ["salary", "rebate", "invoice", "payment", "receivable"].includes(
                      activeModule,
                    ) ? (
                    <FinanceDataPageV2
                      module={activeModule}
                      setError={setError}
                      reloadTrigger={reloadTrigger}
                      onClear={setClearModule}
                    />
                  ) : activeModule === "reconciliation" ? (
                    <ReconciliationPage setError={setError} reloadTrigger={reloadTrigger} />
                  ) : activeModule === "overdue" ? (
                    <OverduePage setError={setError} reloadTrigger={reloadTrigger} />
                  ) : activeModule === "approvals" ? (
                    <ApprovalsPage setError={setError} reloadTrigger={reloadTrigger} />
                  ) : activeModule === "profit" ? (
                    <DatabaseProfitPage
                      onImport={() => setImportOpen(true)}
                      setError={setError}
                      reloadTrigger={reloadTrigger}
                    />
                  ) : (
                    <WelcomePanel
                      moduleKey={activeModule}
                      onImport={() => setImportOpen(true)}
                    />
                  )
                ) : mode === "query" ? (
                  <QueryPanel dataset={dataset} setError={setError} />
                ) : (
                  <div className="h-full overflow-hidden rounded border border-[#e5e6eb] bg-white">
                    {dataset.category === "journal" &&
                    getJournalSections(dataset.columns, rows) ? (
                      <JournalDatasetTable
                        columns={dataset.columns}
                        rows={rows}
                        onEditRow={(row) => {
                          setEditingRow(row);
                          setEditorOpen(true);
                        }}
                        onDeleteRow={async (row) => {
                          if (
                            !row.id ||
                            !window.confirm("确定删除这条记录吗？")
                          )
                            return;
                          await deleteDatasetRow(
                            dataset.dataset_id,
                            Number(row.id),
                          );
                          await loadDataset(dataset.dataset_id, search);
                          await refreshDatasets(dataset.dataset_id);
                        }}
                      />
                    ) : (
                      <DataTable
                        columns={dataset.columns}
                        rows={rows}
                        onEditRow={(row) => {
                          setEditingRow(row);
                          setEditorOpen(true);
                        }}
                        onDeleteRow={async (row) => {
                          if (
                            !row.id ||
                            !window.confirm("确定删除这条记录吗？")
                          )
                            return;
                          await deleteDatasetRow(
                            dataset.dataset_id,
                            Number(row.id),
                          );
                          await loadDataset(dataset.dataset_id, search);
                          await refreshDatasets(dataset.dataset_id);
                        }}
                      />
                    )}
                  </div>
                )}
              </section>
            </>
          )}
        </main>
      </div>

      {importOpen && (
        <ImportDrawer
          initialCategory={activeModule}
          busy={busy}
          setBusy={setBusy}
          setError={setError}
          onClose={() => setImportOpen(false)}
          onJournalCommitted={() => {
            setImportOpen(false);
            goModule("journal");
            setActiveId("");setDataset(null);setRows([]);setTotalRows(0);setReloadTrigger(n=>n+1);
          }}
          onCompanyCommitted={() => {
            setImportOpen(false);
            goModule("company");setActiveId("");setDataset(null);setRows([]);setTotalRows(0);setReloadTrigger(n=>n+1);
          }}
          onEmployeeCommitted={() => {
            setImportOpen(false);
            goModule("employee");setActiveId("");setDataset(null);setRows([]);setTotalRows(0);setReloadTrigger(n=>n+1);
          }}
          onPositionCommitted={() => {
            setImportOpen(false);
            goModule("position");setActiveId("");setDataset(null);setRows([]);setTotalRows(0);setReloadTrigger(n=>n+1);
          }}
          onContractCommitted={() => {
            setImportOpen(false);
            goModule("contract");setActiveId("");setDataset(null);setRows([]);setTotalRows(0);setReloadTrigger(n=>n+1);
          }}
          onAttendanceCommitted={() => {
            setImportOpen(false);
            goModule("attendance");
            setActiveId("");
            setDataset(null);
            setRows([]);
            setTotalRows(0);
            setReloadTrigger(n => n + 1);
          }}
          onCreated={async (created) => {
            setImportOpen(false);
            goPage("data");
            setMode("table");
            setSearch("");
            setActiveModule(created.category || "other");
            await refreshDatasets(created.dataset_id);
            setActiveId(created.dataset_id);
            await loadDataset(created.dataset_id, "");
          }}
        />
      )}

      {editorOpen && dataset && (
        <RowEditor
          dataset={dataset}
          row={editingRow}
          onClose={() => {
            setEditorOpen(false);
            setEditingRow(null);
          }}
          onSave={saveRow}
        />
      )}

      {clearModule && (
        <ClearDialog
          module={clearModule}
          onClose={() => setClearModule(null)}
          onCleared={() => {
            setClearModule(null);
            setReloadTrigger((n) => n + 1);
            setError("");
          }}
        />
      )}
    </div>
  );
}

function SidebarMainButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-h-10 w-full items-center gap-2.5 rounded-lg px-3 text-sm font-medium transition ${
        active
          ? "bg-[#173f2a] text-white shadow-sm"
          : "text-[#4e5b62] hover:bg-white hover:text-[#1f2b31]"
      }`}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </button>
  );
}

function DashboardPage({
  onGoModule,
}: {
  onGoModule: (m: string) => void;
}) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }, []);

  const warnings = summary?.warnings || [];
  const metrics = [
    { label: "在职人员", value: summary?.active_employees ?? "—", unit: "人", icon: Users },
    { label: "合作企业", value: summary?.active_companies ?? "—", unit: "家", icon: Building2 },
    { label: "本月收入", value: formatMoney(summary?.month_income), unit: "", icon: ArrowDownLeft },
    { label: "本月支出", value: formatMoney(summary?.month_expense), unit: "", icon: ArrowUpRight },
    { label: "本月利润", value: formatMoney(summary?.month_profit), unit: "", icon: CircleDollarSign },
    { label: "日记账流水", value: summary?.journal_count ?? "—", unit: "笔", icon: WalletCards },
  ] as const;

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-[#f3f6f4]">
      <div className="mx-auto max-w-[1480px] px-6 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#678070]">
              经营工作台 · {summary?.current_month || "—"}
            </div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#17251d]">
              曼克斯劳务派遣
            </h1>
            <p className="mt-1 text-sm text-[#738078]">
              实时数据来自正式数据库，预警实时更新。
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <div key={metric.label} className="rounded-xl border border-[#dfe6e1] bg-white p-4 shadow-[0_1px_2px_rgba(22,44,31,0.04)]">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#69766f]">{metric.label}</span>
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#edf4ef] text-[#286040]"><Icon className="h-4 w-4" /></span>
                </div>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-2xl font-semibold tabular-nums text-[#18251e]">{metric.value}</span>
                  {metric.unit && <span className="text-xs text-[#8a958f]">{metric.unit}</span>}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.85fr]">
          <section className="overflow-hidden rounded-xl border border-[#dfe6e1] bg-white">
            <div className="flex items-center justify-between border-b border-[#edf0ee] px-5 py-4">
              <div>
                <h2 className="font-semibold text-[#223028]">风险预警</h2>
                <p className="mt-0.5 text-xs text-[#849089]">合同到期、入职未签、回款逾期</p>
              </div>
              <Badge variant="secondary">{warnings.length} 项</Badge>
            </div>
            <div className="divide-y divide-[#edf0ee]">
              {warnings.length > 0 ? (
                warnings.slice(0, 8).map((w, i) => (
                  <div key={`${w.type}-${i}`} className="flex items-start gap-3 px-5 py-4">
                    <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${w.severity === "info" ? "bg-[#eef4ff] text-[#356bb4]" : "bg-[#fff3e8] text-[#b76320]"}`}>
                      <TriangleAlert className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-[#27342d]">{w.title}</div>
                      <div className="mt-1 text-xs text-[#7b8780]">{w.message}</div>
                    </div>
                    <span className="rounded-full bg-[#f3f5f4] px-2 py-1 text-[11px] text-[#758078]">{w.type}</span>
                  </div>
                ))
              ) : (
                <DashboardEmpty icon={Bell} title="当前没有预警" description="合同到期、入职未签、回款逾期等风险会显示在这里。" />
              )}
            </div>
          </section>

          <div className="grid gap-5">
            <section className="rounded-xl border border-[#dfe6e1] bg-[#173f2a] p-5 text-white shadow-[0_12px_30px_rgba(23,63,42,0.12)]">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-white/75">待审批</div>
                <ClipboardCheck className="h-5 w-5 text-[#9ed0ad]" />
              </div>
              <div className="mt-5 text-3xl font-semibold tabular-nums">{summary?.approval_count ?? 0}</div>
              <div className="mt-1 text-sm text-white/70">条工资/返费待审核确认</div>
              <div className="mt-5 border-t border-white/15 pt-4 text-xs leading-5 text-white/60">
                工资和返费需经财务审核、老板确认后生效。
              </div>
            </section>

            <section className="rounded-xl border border-[#dfe6e1] bg-white p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-[#223028]">快捷入口</h2>
                <ArrowUpRight className="h-4 w-4 text-[#708078]" />
              </div>
              <div className="mt-4 space-y-2">
                {[
                  { key: "journal", label: "日记账", desc: "查看流水与收支" },
                  { key: "employee", label: "人员档案", desc: "管理派遣员工" },
                  { key: "company", label: "企业管理", desc: "合作企业信息" },
                  { key: "approvals", label: "审批中心", desc: "待审核事项" },
                ].map(item => (
                  <button key={item.key} onClick={() => onGoModule(item.key)}
                    className="w-full rounded-lg border border-[#e5eae7] bg-[#fafcfb] p-3 text-left hover:bg-[#edf4ef] transition">
                    <div className="text-sm font-medium text-[#2a382f]">{item.label}</div>
                    <div className="text-xs text-[#859088]">{item.desc}</div>
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardEmpty({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3 px-5 py-6">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#f0f4f1] text-[#718078]">
        <Icon className="h-4 w-4" />
      </span>
      <div>
        <div className="text-sm font-medium text-[#344138]">{title}</div>
        <div className="mt-0.5 text-xs text-[#89938d]">{description}</div>
      </div>
    </div>
  );
}

function UserSettingsPage({ setError }: { setError: (v: string) => void }) {
  const [rows, setRows] = useState<SystemUser[]>([]);
  const [allowed, setAllowed] = useState(true);
  const [open, setOpen] = useState(false);
  const load = useCallback(async () => {
    try {
      setRows((await listSystemUsers()).rows);
      setAllowed(true);
    } catch (e) {
      setAllowed(false);
      setError(readError(e));
    }
  }, [setError]);
  useEffect(() => {
    load();
  }, [load]);
  return (
    <div className="h-full overflow-auto rounded-xl border bg-white">
      <div className="flex items-center justify-between border-b bg-[#f8faf9] p-5">
        <div>
          <h2 className="font-semibold">账号与三级权限</h2>
          <p className="mt-1 text-xs text-[#718078]">
            一级员工录入，二级财务审核，三级老板确认；管理员维护系统。
          </p>
        </div>
        {allowed && (
          <Button onClick={() => setOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            新增账号
          </Button>
        )}
      </div>
      {!allowed ? (
        <EmptyState
          title="仅管理员可查看"
          description="当前账号没有用户与权限管理权限。"
        />
      ) : (
        <table className="min-w-full text-sm">
          <thead className="bg-[#f4f7f5]">
            <tr>
              {["姓名", "账号", "状态", "角色"].map((x) => (
                <th key={x} className="px-5 py-3 text-left text-xs">
                  {x}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="px-5 py-3">{u.display_name}</td>
                <td className="px-5 py-3 text-xs">{u.username}</td>
                <td className="px-5 py-3 text-xs">
                  {u.status === "active" ? "启用" : "停用"}
                </td>
                <td className="px-5 py-3">
                  <select
                    className="journal-input max-w-40"
                    value={u.role_code}
                    onChange={async (e) => {
                      await changeSystemUserRole(u.id, e.target.value);
                      await load();
                    }}
                  >
                    <option value="staff">一级员工</option>
                    <option value="finance">二级财务</option>
                    <option value="owner">三级老板</option>
                    <option value="admin">系统管理员</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open && (
        <NewUserDialog
          onClose={() => setOpen(false)}
          onSave={async (d) => {
            await createSystemUser(d);
            setOpen(false);
            await load();
          }}
        />
      )}
    </div>
  );
}
function NewUserDialog({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (d: {
    username: string;
    password: string;
    display_name: string;
    role_code: string;
  }) => Promise<void>;
}) {
  const [f, setF] = useState({
    username: "",
    password: "",
    display_name: "",
    role_code: "staff",
  });
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4">
      <div className="w-full max-w-md rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>新增系统账号</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="space-y-3 p-5">
          <JournalField label="姓名">
            <input
              className="journal-input"
              value={f.display_name}
              onChange={(e) => setF({ ...f, display_name: e.target.value })}
            />
          </JournalField>
          <JournalField label="登录账号">
            <input
              className="journal-input"
              value={f.username}
              onChange={(e) => setF({ ...f, username: e.target.value })}
            />
          </JournalField>
          <JournalField label="初始密码（至少10位）">
            <input
              type="password"
              className="journal-input"
              value={f.password}
              onChange={(e) => setF({ ...f, password: e.target.value })}
            />
          </JournalField>
          <JournalField label="角色">
            <select
              className="journal-input"
              value={f.role_code}
              onChange={(e) => setF({ ...f, role_code: e.target.value })}
            >
              <option value="staff">一级员工</option>
              <option value="finance">二级财务</option>
              <option value="owner">三级老板</option>
              <option value="admin">系统管理员</option>
            </select>
          </JournalField>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={
              !f.display_name || f.username.length < 3 || f.password.length < 10
            }
            onClick={() => onSave(f)}
          >
            创建
          </Button>
        </div>
      </div>
    </div>
  );
}

function ComingSoonPage({
  icon: Icon,
  eyebrow,
  title,
  description,
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-[#f3f6f4] p-8">
      <div className="max-w-xl rounded-2xl border border-[#dfe6e1] bg-white p-8 text-center shadow-[0_16px_50px_rgba(26,50,35,0.08)]">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-[#eaf3ed] text-[#245c3a]">
          <Icon className="h-6 w-6" />
        </div>
        <div className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-[#6d8174]">
          {eyebrow}
        </div>
        <h1 className="mt-2 text-xl font-semibold text-[#1e2c23]">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-[#728078]">{description}</p>
      </div>
    </div>
  );
}

function formatMoney(value: number | undefined): string {
  if (value === undefined) return "—";
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(value);
}

type JournalDirectionFilter = "all" | "income" | "expense";

function AttendancePage({ setError, reloadTrigger, onClear, onImport }: { setError: (v: string) => void; reloadTrigger: number; onClear: (m: string) => void; onImport: () => void }) {
  const [rows, setRows] = useState<AttendanceRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [editId, setEditId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const [a, e] = await Promise.all([listAttendance(targetPage, pageSize), listEmployees('', 1, 1000)]);
      setRows(a.rows);
      setTotal(a.total);
      setPage(targetPage);
      setEmployees(e.rows);
    } catch (x) {
      setError(readError(x));
    }
  }, [pageSize, setError]);
  useEffect(() => {
    load(1);
  }, [load, reloadTrigger]);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex justify-between border-b bg-[#f8faf9] p-4">
        <div>
          <b>考勤管理</b>
          <div className="text-xs text-[#7d8881]">
            工时、异常与扣款直接关联人员
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("attendance")}>
            <Trash2 className="mr-2 h-4 w-4" />
            清空
          </Button>
          <Button variant="outline" asChild><a href={attendanceExportUrl()}><Download className="mr-2 h-4 w-4" />导出</a></Button>
          <Button variant="outline" onClick={onImport}><Upload className="mr-2 h-4 w-4" />导入</Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>
              {["日期","人员","状态","工时","扣款","备注",""].map(x => <th key={x} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{x}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]">
              <td colSpan={7} className="px-2 py-1">
                {editId === -1 ? (
                  <AttendNewRow employees={employees} onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />
                ) : (
                  <button onClick={() => employees.length ? setEditId(-1) : setError("请先在人员管理中新增人员，再录入考勤")} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium">
                    <Plus className="h-3.5 w-3.5" /> 新增
                  </button>
                )}
              </td>
            </tr>
            {rows.map(r => (
              <AttendRow key={r.id} row={r} employees={employees} onSaved={() => { load(); setEditId(null); }} isEditing={editId === r.id} onEdit={() => setEditId(r.id)} />
            ))}
            {!rows.length && <tr><td colSpan={7}><EmptyState title="暂无考勤" description="点击上方「+ 新增」录入第一条" /></td></tr>}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
    </div>
  );
}

function AttendRow({ row, employees, onSaved, isEditing, onEdit }: {
  row: AttendanceRecord; employees: EmployeeRecord[]; onSaved: () => void; isEditing: boolean; onEdit: () => void;
}) {
  const [f, setF] = useState({ employee_id: String(row.employee_id), work_date: row.work_date, status: row.status, hours: String(row.hours), deduction_amount: String(row.deduction_amount), remark: row.remark || "" });
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const labels: Record<string,string> = { normal:"正常", late:"迟到", absent:"旷工", leave:"请假" };
  const save = async () => { setSaving(true); try { await updateAttendance(row.id, { employee_id: Number(f.employee_id), work_date: f.work_date, status: f.status as AttendanceRecord["status"], hours: Number(f.hours), deduction_amount: Number(f.deduction_amount), remark: f.remark } as Omit<AttendanceRecord,"id"|"employee_name">); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const del = async () => { await deleteAttendance(row.id); onSaved(); };
  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]";
  const cell = "px-1 py-1";
  if (!isEditing) return (
    <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
      <td className={`${cell} text-xs`}>{row.work_date}</td>
      <td className={`${cell} text-xs font-medium`}>{row.employee_name}</td>
      <td className={`${cell} text-xs`}>{labels[row.status]}</td>
      <td className={`${cell} text-xs`}>{row.hours}</td>
      <td className={`${cell} text-xs`}>¥{row.deduction_amount}</td>
      <td className={`${cell} text-xs`}>{row.remark || "-"}</td>
      <td className={cell} onClick={e => e.stopPropagation()}>
        {confirming ? (
          <span className="inline-flex items-center gap-1"><span className="text-xs text-[#ba4935]">确认？</span><button onClick={del} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button><button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button></span>
        ) : <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">✕</button>}
      </td>
    </tr>
  );
  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><DatePicker value={f.work_date} onChange={v => setF({...f, work_date: v})} /></td>
      <td className={cell}><select value={f.employee_id} onChange={e => setF({...f, employee_id: e.target.value})} className={inputCls}>{employees.map(e => <option key={e.id} value={String(e.id)}>{e.name}</option>)}</select></td>
      <td className={cell}><select value={f.status} onChange={e => setF({...f, status: e.target.value as AttendanceRecord["status"]})} className={inputCls}><option value="normal">正常</option><option value="late">迟到</option><option value="absent">旷工</option><option value="leave">请假</option></select></td>
      <td className={cell}><input type="number" value={f.hours} onChange={e => setF({...f, hours: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input type="number" value={f.deduction_amount} onChange={e => setF({...f, deduction_amount: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.remark} onChange={e => setF({...f, remark: e.target.value})} className={inputCls} onKeyDown={e => { if (e.key==="Enter") save(); if (e.key==="Escape") onSaved(); }} /></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button><button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}
function AttendNewRow({ employees, onSaved, onCancel }: { employees: EmployeeRecord[]; onSaved: () => void; onCancel: () => void }) {
  const [f, setF] = useState({ employee_id: String(employees[0]?.id || ""), work_date: new Date().toISOString().slice(0,10), status: "normal" as AttendanceRecord["status"], hours: "8", deduction_amount: "0", remark: "" });
  const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await createAttendance({ employee_id: Number(f.employee_id), work_date: f.work_date, status: f.status, hours: Number(f.hours), deduction_amount: Number(f.deduction_amount), remark: f.remark } as Omit<AttendanceRecord,"id"|"employee_name">); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none";
  const cell = "px-1 py-1";
  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><DatePicker value={f.work_date} onChange={v => setF({...f, work_date: v})} /></td>
      <td className={cell}><select value={f.employee_id} onChange={e => setF({...f, employee_id: e.target.value})} className={inputCls}>{employees.map(e => <option key={e.id} value={String(e.id)}>{e.name}</option>)}</select></td>
      <td className={cell}><select value={f.status} onChange={e => setF({...f, status: e.target.value as AttendanceRecord["status"]})} className={inputCls}><option value="normal">正常</option><option value="late">迟到</option><option value="absent">旷工</option><option value="leave">请假</option></select></td>
      <td className={cell}><input type="number" value={f.hours} onChange={e => setF({...f, hours: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input type="number" value={f.deduction_amount} onChange={e => setF({...f, deduction_amount: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.remark} onChange={e => setF({...f, remark: e.target.value})} className={inputCls} placeholder="备注" onKeyDown={e => { if (e.key==="Enter") save(); }} /></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button><button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}

function EmpRow({ row, warn, companies, positions, onSaved, isEditing, onEdit, onDetail }: {
  row: EmployeeRecord; warn: boolean; companies: CompanyRecord[]; positions: PositionRecord[];
  onSaved: () => void; isEditing: boolean; onEdit: () => void; onDetail: () => void;
}) {
  const [f, setF] = useState({ name: row.name, phone: row.phone, gender: row.gender, company_id: String(row.company_id), position_id: String(row.position_id || ""), entry_date: row.entry_date, address: row.address || "" });
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const filteredPos = positions.filter(p => p.company_id === Number(f.company_id));
  const save = async () => { setSaving(true); try { await updateEmployee(row.id, { ...f, company_id: Number(f.company_id), position_id: f.position_id ? Number(f.position_id) : null }); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const leave = async () => { setConfirming(false); await leaveEmployee(row.id, new Date().toISOString().slice(0,10)); onSaved(); };
  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]";
  const cell = "px-1 py-1";
  if (!isEditing) return (
    <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
      <td className={cell}><button onClick={e => { e.stopPropagation(); onDetail(); }} className="text-xs text-[#165d46] hover:underline font-medium">{row.name}</button>{warn && <span className="ml-1 rounded bg-[#fff0ed] px-1 py-0.5 text-[10px] text-[#b74734]">未签</span>}</td>
      <td className={`${cell} text-xs`}>{row.id_card_masked}</td>
      <td className={`${cell} text-xs`}>{row.phone}</td>
      <td className={`${cell} text-xs`}>{row.company_name}{row.position_name ? ` / ${row.position_name}` : ""}</td>
      <td className={`${cell} text-xs`}>{row.entry_date}</td>
      <td className={`${cell} text-xs`}>{row.contract_count}份</td>
      <td className={`${cell} text-xs`}>{row.status === "active" ? "在职" : "离职"}</td>
      <td className={cell} onClick={e => e.stopPropagation()}>
        {confirming ? (
          <span className="inline-flex items-center gap-1"><span className="text-xs text-[#ba4935]">确认离职？</span><button onClick={leave} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button><button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button></span>
        ) : <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">离职</button>}
      </td>
    </tr>
  );
  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} /></td>
      <td className={`${cell} text-xs text-[#86909c]`}>{row.id_card_masked}</td>
      <td className={cell}><input value={f.phone} onChange={e => setF({...f, phone: e.target.value})} className={inputCls} /></td>
      <td className={cell}>
        <select value={f.company_id} onChange={e => setF({...f, company_id: e.target.value, position_id: ""})} className={inputCls + " w-24"}>{companies.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}</select>
        <select value={f.position_id} onChange={e => setF({...f, position_id: e.target.value})} className={inputCls + " w-20 ml-1"}><option value="">-</option>{filteredPos.map(p => <option key={p.id} value={String(p.id)}>{p.name}</option>)}</select>
      </td>
      <td className={cell}><DatePicker value={f.entry_date} onChange={v => setF({...f, entry_date: v})} /></td>
      <td className={`${cell} text-xs`}>{row.contract_count}份</td>
      <td className={`${cell} text-xs`}>{row.status === "active" ? "在职" : "离职"}</td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button><button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}
function EmpNewRow({ companies, positions, onSaved, onCancel }: {
  companies: CompanyRecord[]; positions: PositionRecord[]; onSaved: () => void; onCancel: () => void;
}) {
  const [f, setF] = useState({ name: "", id_card_number: "", phone: "", gender: "male", company_id: String(companies[0]?.id || ""), position_id: "", entry_date: new Date().toISOString().slice(0,10), address: "" });
  const [saving, setSaving] = useState(false);
  const filteredPos = positions.filter(p => p.company_id === Number(f.company_id));
  const save = async () => { setSaving(true); try { await createEmployee({ ...f, company_id: Number(f.company_id), position_id: f.position_id ? Number(f.position_id) : null }); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none";
  const cell = "px-1 py-1";
  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} placeholder="姓名" /></td>
      <td className={cell}><input value={f.id_card_number} onChange={e => setF({...f, id_card_number: e.target.value})} className={inputCls} placeholder="身份证" /></td>
      <td className={cell}><input value={f.phone} onChange={e => setF({...f, phone: e.target.value})} className={inputCls} placeholder="手机号" /></td>
      <td className={cell}>
        <select value={f.company_id} onChange={e => setF({...f, company_id: e.target.value, position_id: ""})} className={inputCls + " w-24"}>{companies.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}</select>
        <select value={f.position_id} onChange={e => setF({...f, position_id: e.target.value})} className={inputCls + " w-20 ml-1"}><option value="">-</option>{filteredPos.map(p => <option key={p.id} value={String(p.id)}>{p.name}</option>)}</select>
      </td>
      <td className={cell}><DatePicker value={f.entry_date} onChange={v => setF({...f, entry_date: v})} /></td>
      <td className={`${cell} text-xs`}>-</td>
      <td className={`${cell} text-xs text-[#173f2a] font-medium`}>新增</td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button><button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}

function PosRow({ row, companies, onSaved, isEditing, onEdit }: { row: PositionRecord; companies: CompanyRecord[]; onSaved: () => void; isEditing: boolean; onEdit: () => void }) {
  const [f, setF] = useState({ company_id: String(row.company_id), name: row.name, daily_rate: String(row.daily_rate ?? ""), required_count: String(row.required_count ?? ""), status: row.status, description: row.description || "" });
  const [confirming, setConfirming] = useState(false); const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await updatePosition(row.id, { ...f, company_id: Number(f.company_id), daily_rate: f.daily_rate ? Number(f.daily_rate) : null, required_count: f.required_count ? Number(f.required_count) : null } as Partial<PositionRecord>); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const del = async () => { setConfirming(false); await deletePositionRecord(row.id); onSaved(); };
  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]"; const cell = "px-1 py-1";
  if (!isEditing) return (
    <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
      <td className={`${cell} text-xs`}>{row.company_name}</td><td className={`${cell} text-xs font-medium`}>{row.name}</td>
      <td className={`${cell} text-xs`}>{row.daily_rate ?? "-"}</td><td className={`${cell} text-xs`}>{row.required_count ?? "-"}</td>
      <td className={`${cell} text-xs`}>{row.status}</td>
      <td className={cell} onClick={e => e.stopPropagation()}>
        {confirming ? (<span className="inline-flex items-center gap-1"><span className="text-xs text-[#ba4935]">确认？</span><button onClick={del} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button><button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button></span>) : <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">关闭</button>}
      </td>
    </tr>
  );
  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><select value={f.company_id} onChange={e => setF({...f, company_id: e.target.value})} className={inputCls}>{companies.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}</select></td>
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input type="number" value={f.daily_rate} onChange={e => setF({...f, daily_rate: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input type="number" value={f.required_count} onChange={e => setF({...f, required_count: e.target.value})} className={inputCls} /></td>
      <td className={cell}><select value={f.status} onChange={e => setF({...f, status: e.target.value as PositionRecord["status"]})} className={inputCls}><option value="recruiting">招聘中</option><option value="filled">已满</option><option value="closed">已关闭</option></select></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button><button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}
function PosNewRow({ companies, onSaved, onCancel }: { companies: CompanyRecord[]; onSaved: () => void; onCancel: () => void }) {
  const [f, setF] = useState({ company_id: String(companies[0]?.id || ""), name: "", daily_rate: "", required_count: "", status: "recruiting", description: "" });
  const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await createPosition({ ...f, company_id: Number(f.company_id), daily_rate: f.daily_rate ? Number(f.daily_rate) : null, required_count: f.required_count ? Number(f.required_count) : null } as Partial<PositionRecord>); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none"; const cell = "px-1 py-1";
  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><select value={f.company_id} onChange={e => setF({...f, company_id: e.target.value})} className={inputCls}>{companies.map(c => <option key={c.id} value={String(c.id)}>{c.name}</option>)}</select></td>
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} placeholder="岗位名" /></td>
      <td className={cell}><input type="number" value={f.daily_rate} onChange={e => setF({...f, daily_rate: e.target.value})} className={inputCls} placeholder="0" /></td>
      <td className={cell}><input type="number" value={f.required_count} onChange={e => setF({...f, required_count: e.target.value})} className={inputCls} placeholder="0" /></td>
      <td className={cell}><select value={f.status} onChange={e => setF({...f, status: e.target.value})} className={inputCls}><option value="recruiting">招聘中</option><option value="filled">已满</option><option value="closed">已关闭</option></select></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button><button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}

function CompanyRow({ row, onSaved, isEditing, onEdit }: { row: CompanyRecord; onSaved: () => void; isEditing: boolean; onEdit: () => void }) {
  const statusText: Record<string,string> = { active:"正常合作", paused:"暂停合作", terminated:"终止合作" };
  const [f, setF] = useState({ name: row.name, contact_person: row.contact_person || "", contact_phone: row.contact_phone || "", address: row.address || "", business_license_no: row.business_license_no || "", cooperation_status: row.cooperation_status, cooperation_start_date: row.cooperation_start_date || "", cooperation_end_date: row.cooperation_end_date || "", default_receivable_days: String(row.default_receivable_days ?? ""), remark: row.remark || "" });
  const [confirming, setConfirming] = useState(false);
  const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await updateCompany(row.id, { ...f, default_receivable_days: f.default_receivable_days ? Number(f.default_receivable_days) : null, cooperation_start_date: f.cooperation_start_date || null, cooperation_end_date: f.cooperation_end_date || null } as Partial<CompanyRecord>); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const del = async () => { setConfirming(false); await deleteCompanyRecord(row.id); onSaved(); };
  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]"; const cell = "px-1 py-1";
  if (!isEditing) return (
    <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
      <td className={`${cell} text-xs font-medium`}>{row.name}</td><td className={`${cell} text-xs`}>{row.contact_person||"-"}</td><td className={`${cell} text-xs`}>{row.contact_phone||"-"}</td>
      <td className={`${cell} text-xs`}>{statusText[row.cooperation_status]}</td><td className={`${cell} text-xs`}>{row.cooperation_start_date||"-"}~{row.cooperation_end_date||"-"}</td>
      <td className={`${cell} text-xs`}>{row.default_receivable_days != null ? `${row.default_receivable_days}天` : "-"}</td>
      <td className={cell} onClick={e => e.stopPropagation()}>
        {confirming ? (<span className="inline-flex items-center gap-1"><span className="text-xs text-[#ba4935]">确认？</span><button onClick={del} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button><button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button></span>) : <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">停用</button>}
      </td>
    </tr>
  );
  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.contact_person} onChange={e => setF({...f, contact_person: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.contact_phone} onChange={e => setF({...f, contact_phone: e.target.value})} className={inputCls} /></td>
      <td className={cell}><select value={f.cooperation_status} onChange={e => setF({...f, cooperation_status: e.target.value as CompanyRecord["cooperation_status"]})} className={inputCls}><option value="active">正常</option><option value="paused">暂停</option><option value="terminated">终止</option></select></td>
      <td className={cell}><DatePicker value={f.cooperation_start_date} onChange={v => setF({...f, cooperation_start_date: v})} /><DatePicker value={f.cooperation_end_date} onChange={v => setF({...f, cooperation_end_date: v})} /></td>
      <td className={cell}><input type="number" value={f.default_receivable_days} onChange={e => setF({...f, default_receivable_days: e.target.value})} className={inputCls} /></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button><button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}
function CompanyNewRow({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const [f, setF] = useState({ name: "", contact_person: "", contact_phone: "", address: "", business_license_no: "", cooperation_status: "active", cooperation_start_date: "", cooperation_end_date: "", default_receivable_days: "", remark: "" });
  const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await createCompany({ ...f, default_receivable_days: f.default_receivable_days ? Number(f.default_receivable_days) : null, cooperation_start_date: f.cooperation_start_date || null, cooperation_end_date: f.cooperation_end_date || null } as Partial<CompanyRecord>); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none"; const cell = "px-1 py-1";
  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><input value={f.name} onChange={e => setF({...f, name: e.target.value})} className={inputCls} placeholder="企业名称" /></td>
      <td className={cell}><input value={f.contact_person} onChange={e => setF({...f, contact_person: e.target.value})} className={inputCls} placeholder="联系人" /></td>
      <td className={cell}><input value={f.contact_phone} onChange={e => setF({...f, contact_phone: e.target.value})} className={inputCls} placeholder="电话" /></td>
      <td className={cell}><select value={f.cooperation_status} onChange={e => setF({...f, cooperation_status: e.target.value as CompanyRecord["cooperation_status"]})} className={inputCls}><option value="active">正常</option><option value="paused">暂停</option><option value="terminated">终止</option></select></td>
      <td className={cell}><DatePicker value={f.cooperation_start_date} onChange={v => setF({...f, cooperation_start_date: v})} /><DatePicker value={f.cooperation_end_date} onChange={v => setF({...f, cooperation_end_date: v})} /></td>
      <td className={cell}><input type="number" value={f.default_receivable_days} onChange={e => setF({...f, default_receivable_days: e.target.value})} className={inputCls} placeholder="天" /></td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button><button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}

function ContractRow({ row, empName, warn, employees, onSaved, isEditing, onEdit }: {
  row: ContractRecord; empName?: string; warn?: { days_left: number }; employees: EmployeeRecord[];
  onSaved: () => void; isEditing: boolean; onEdit: () => void;
}) {
  const [f, setF] = useState({ employee_id: String(row.employee_id), contract_type: row.contract_type, contract_no: row.contract_no || "", sign_date: row.sign_date || "", start_date: row.start_date, end_date: row.end_date, remark: row.remark || "" });
  const [confirming, setConfirming] = useState(false); const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await updateContract(row.id, { ...f, employee_id: Number(f.employee_id), sign_date: f.sign_date || null } as Partial<ContractRecord>); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const term = async () => { setConfirming(false); await terminateContract(row.id); onSaved(); };
  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]"; const cell = "px-1 py-1";
  if (!isEditing) return (
    <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
      <td className={`${cell} text-xs`}>{empName || row.employee_id}</td><td className={`${cell} text-xs`}>{row.contract_no || "-"}</td>
      <td className={`${cell} text-xs`}>{row.sign_date || "-"}</td><td className={`${cell} text-xs`}>{row.start_date}~{row.end_date}</td>
      <td className={`${cell} text-xs`}>{row.status}</td>
      <td className={`${cell} text-xs`}>{warn ? <span className="text-[#b74734]">{warn.days_left}天后到期</span> : "-"}</td>
      <td className={cell} onClick={e => e.stopPropagation()}>
        {confirming ? (<span className="inline-flex items-center gap-1"><span className="text-xs text-[#ba4935]">确认终止？</span><button onClick={term} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button><button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button></span>) : <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">终止</button>}
      </td>
    </tr>
  );
  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><select value={f.employee_id} onChange={e => setF({...f, employee_id: e.target.value})} disabled={!!row.id} className={inputCls}>{employees.map(e => <option key={e.id} value={String(e.id)}>{e.name}</option>)}</select></td>
      <td className={cell}><input value={f.contract_no} onChange={e => setF({...f, contract_no: e.target.value})} className={inputCls} /></td>
      <td className={cell}><DatePicker value={f.sign_date} onChange={v => setF({...f, sign_date: v})} /></td>
      <td className={cell}><DatePicker value={f.start_date} onChange={v => setF({...f, start_date: v})} /><span className="text-xs">~</span><DatePicker value={f.end_date} onChange={v => setF({...f, end_date: v})} /></td>
      <td className={`${cell} text-xs`}>{row.status}</td>
      <td className={`${cell} text-xs`}>{warn ? <span className="text-[#b74734]">{warn.days_left}天后到期</span> : "-"}</td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button><button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}
function ContractNewRow({ employees, onSaved, onCancel }: { employees: EmployeeRecord[]; onSaved: () => void; onCancel: () => void }) {
  const today = new Date().toISOString().slice(0,10);
  const [f, setF] = useState({ employee_id: String(employees[0]?.id || ""), contract_type: "employee", contract_no: "", sign_date: "", start_date: today, end_date: "", remark: "" });
  const [saving, setSaving] = useState(false);
  const emp = employees.find(e => e.id === Number(f.employee_id));
  const save = async () => { setSaving(true); try { await createContract({ ...f, employee_id: Number(f.employee_id), company_id: emp?.company_id, sign_date: f.sign_date || null } as Partial<ContractRecord> & { company_id?: number | null }); onSaved(); } catch(e) { alert(readError(e)); } finally { setSaving(false); } };
  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none"; const cell = "px-1 py-1";
  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><select value={f.employee_id} onChange={e => setF({...f, employee_id: e.target.value})} className={inputCls}>{employees.map(e => <option key={e.id} value={String(e.id)}>{e.name}</option>)}</select></td>
      <td className={cell}><input value={f.contract_no} onChange={e => setF({...f, contract_no: e.target.value})} className={inputCls} placeholder="编号" /></td>
      <td className={cell}><DatePicker value={f.sign_date} onChange={v => setF({...f, sign_date: v})} /></td>
      <td className={cell}><DatePicker value={f.start_date} onChange={v => setF({...f, start_date: v})} /><span className="text-xs">~</span><DatePicker value={f.end_date} onChange={v => setF({...f, end_date: v})} /></td>
      <td className={`${cell} text-xs text-[#173f2a] font-medium`}>新增</td>
      <td className={`${cell} text-xs`}>-</td>
      <td className={`${cell} whitespace-nowrap`}><button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button><button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button></td>
    </tr>
  );
}

const FINANCE_META: Record<
  string,
  { title: string; fields: Array<[string, string, string]> }
> = {
  salary: {
    title: "工资发放",
    fields: [
      ["employee_id", "员工", "employee"],
      ["salary_month", "工资月份", "date"],
      ["pay_date", "发薪日期", "date"],
      ["base_salary", "基本工资", "number"],
      ["allowance", "津贴", "number"],
      ["deduction", "扣款", "number"],
      ["remark", "备注", "text"],
    ],
  },
  rebate: {
    title: "代招返费",
    fields: [
      ["company_id", "企业", "company"],
      ["employee_id", "关联员工", "employee"],
      ["rebate_date", "返费日期", "date"],
      ["amount", "金额", "number"],
      ["person_count", "人数", "number"],
      ["remark", "备注", "text"],
    ],
  },
  invoice: {
    title: "开票管理",
    fields: [
      ["company_id", "企业", "company"],
      ["invoice_no", "发票编号", "text"],
      ["invoice_date", "开票日期", "date"],
      ["amount", "金额", "number"],
      ["remark", "备注", "text"],
    ],
  },
  payment: {
    title: "回款管理",
    fields: [
      ["company_id", "企业", "company"],
      ["payment_date", "回款日期", "date"],
      ["amount", "金额", "number"],
      ["payment_method", "付款方式", "method"],
      ["acceptance_due_date", "承兑到期日", "date"],
      ["bank_reference", "银行流水", "text"],
      ["receivable_id", "分配应收ID", "number"],
      ["allocated_amount", "分配金额", "number"],
      ["remark", "备注", "text"],
    ],
  },
  receivable: {
    title: "应收管理",
    fields: [
      ["company_id", "企业", "company"],
      ["expected_date", "预计回款日", "date"],
      ["amount", "应收金额", "number"],
      ["received_amount", "已收金额", "number"],
      ["status", "状态", "text"],
      ["remark", "备注", "text"],
    ],
  },
};
function FinanceDataPageV2({
  module,
  setError,
  reloadTrigger,
  onClear,
}: {
  module: string;
  setError: (v: string) => void;
  reloadTrigger: number;
  onClear: (m: string) => void;
}) {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [total, setTotal] = useState(0);
  const [editId, setEditId] = useState<number | null>(null);
  const [companies, setCompanies] = useState<CompanyRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const meta = FINANCE_META[module];
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const [r, c, e] = await Promise.all([
        listFinanceModule(module, targetPage, pageSize),
        listCompanies('', '', 1, 1000),
        listEmployees('', 1, 1000),
      ]);
      setRows(r.rows);
      setTotal(r.total);
      setPage(targetPage);
      setCompanies(c.rows);
      setEmployees(e.rows);
    } catch (x) {
      setError(readError(x));
    }
  }, [module, pageSize, setError]);
  useEffect(() => {
    load(1);
  }, [load, reloadTrigger]);
  const doImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".xlsx";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const up = await uploadFile(file);
        const result = await importFinance(
          module,
          up.upload_id,
          up.sheets[0].name,
        );
        if (result.errors.length)
          setError(
            `已导入 ${result.imported_rows} 行，${result.errors.length} 行失败`,
          );
        await load();
      } catch (x) {
        setError(readError(x));
      }
    };
    input.click();
  };
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex justify-between border-b bg-[#f8faf9] p-4">
        <div>
          <b>{meta.title}</b>
          <div className="text-xs text-[#7d8881]">
            正式数据库 · {rows.length} 条
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear(module)}>
            <Trash2 className="mr-2 h-4 w-4" />
            清空
          </Button>
          <Button variant="outline" onClick={doImport}>
            <Upload className="mr-2 h-4 w-4" />
            导入
          </Button>
          <Button
            variant="outline"
            onClick={() => downloadAuthenticated(financeExportUrl(module))}
          >
            <Download className="mr-2 h-4 w-4" />
            导出
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>
              {meta.fields.map(([k, l]) => <th key={k} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{l}</th>)}
              <th className="px-2 py-2 text-left text-xs font-medium text-[#526058]"></th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]">
              <td colSpan={meta.fields.length + 1} className="px-2 py-1">
                {editId === -1 ? (
                  <FinanceNewRowInline module={module} companies={companies} employees={employees} onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />
                ) : (
                  <button onClick={() => setEditId(-1)} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium">
                    <Plus className="h-3.5 w-3.5" /> 新增
                  </button>
                )}
              </td>
            </tr>
            {rows.map((r) => (
              <FinanceRow key={String(r.id)} module={module} row={r} companies={companies} employees={employees} onSaved={() => { load(); setEditId(null); }} isEditing={editId === Number(r.id)} onEdit={() => setEditId(Number(r.id))} />
            ))}
            {!rows.length && (
              <tr><td colSpan={meta.fields.length + 1}><EmptyState title={`暂无${meta.title}数据`} description="点击上方「+ 新增」录入第一条记录" /></td></tr>
            )}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
    </div>
  );
}
function FinanceRow({ module, row, companies, employees, onSaved, isEditing, onEdit }: {
  module: string; row: Record<string, unknown>; companies: CompanyRecord[]; employees: EmployeeRecord[];
  onSaved: () => void; isEditing: boolean; onEdit: () => void;
}) {
  const meta = FINANCE_META[module];
  const [f, setF] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const [k] of meta.fields) init[k] = String(row[k] ?? "");
    return init;
  });
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const d: Record<string, unknown> = {};
      for (const [k, , t] of meta.fields)
        d[k] = t === "number" ? Number(f[k] || 0) : ["company", "employee"].includes(t) ? (f[k] ? Number(f[k]) : null) : f[k] || null;
      await updateFinanceRecord(module, Number(row.id), d);
      onSaved();
    } catch (e) { alert(readError(e)); }
    finally { setSaving(false); }
  };

  const del = async () => { await deleteFinanceRecord(module, Number(row.id)); onSaved(); };

  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c]";
  const cell = "px-1 py-1";

  if (!isEditing) {
    const status = String(row.status ?? "");
    const displayVals: Record<string, string> = {};
    for (const [k] of meta.fields) {
      const v = row[k];
      if (k === "company_id") displayVals[k] = companies.find(c => c.id === Number(v))?.name || String(v ?? "-");
      else if (k === "employee_id") displayVals[k] = employees.find(e => e.id === Number(v))?.name || String(v ?? "-");
      else if (k === "payment_method") displayVals[k] = v === "bank_acceptance" ? "银行承兑" : v === "direct" ? "直接给付" : String(v ?? "-");
      else displayVals[k] = String(v ?? "-");
    }
    return (
      <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
        {meta.fields.map(([k]) => <td key={k} className={`${cell} text-xs`}>{displayVals[k]}</td>)}
        <td className={`${cell} whitespace-nowrap`} onClick={e => e.stopPropagation()}>
          {["salary","rebate"].includes(module) && status !== "confirmed" && (
            <button onClick={async () => { await approveFinanceRecord(module, Number(row.id)); onSaved(); }} className="mr-1 text-xs text-[#165dff] hover:underline">审批</button>
          )}
          {confirming ? (
            <span className="inline-flex items-center gap-1">
              <span className="text-xs text-[#ba4935]">确认？</span>
              <button onClick={del} className="text-xs bg-[#f53f3f] text-white rounded px-1 py-0.5">确认</button>
              <button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button>
            </span>
          ) : (
            <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">✕</button>
          )}
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      {meta.fields.map(([k, , t]) => (
        <td key={k} className={cell}>
          {t === "company" ? (
            <select value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}>
              <option value="">-</option>
              {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          ) : t === "employee" ? (
            <select value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}>
              <option value="">-</option>
              {employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          ) : t === "method" ? (
            <select value={f[k] || "direct"} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}>
              <option value="direct">直接给付</option>
              <option value="bank_acceptance">银行承兑</option>
            </select>
          ) : t === "date" ? (
            <DatePicker value={f[k] || ""} onChange={v => setF({...f, [k]: v})} />
          ) : (
            <input type={t === "number" ? "number" : "text"} step="0.01" value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls} onKeyDown={e => { if (e.key === "Enter") save(); if (e.key === "Escape") onSaved(); }} />
          )}
        </td>
      ))}
      <td className={`${cell} whitespace-nowrap`}>
        <button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button>
        <button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button>
      </td>
    </tr>
  );
}

function FinanceNewRowInline({ module, companies, employees, onSaved, onCancel }: {
  module: string; companies: CompanyRecord[]; employees: EmployeeRecord[];
  onSaved: () => void; onCancel: () => void;
}) {
  const meta = FINANCE_META[module];
  const seed: Record<string, string> = { payment_method: "direct", person_count: "1", base_salary: "0", allowance: "0", deduction: "0" };
  const [f, setF] = useState<Record<string, string>>(seed);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const d: Record<string, unknown> = {};
      for (const [k, , t] of meta.fields)
        d[k] = t === "number" ? Number(f[k] || 0) : ["company", "employee"].includes(t) ? (f[k] ? Number(f[k]) : null) : f[k] || null;
      await createFinanceRecord(module, d);
      onSaved();
    } catch (e) { alert(readError(e)); }
    finally { setSaving(false); }
  };

  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none";
  const cell = "px-1 py-1";

  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      {meta.fields.map(([k, , t]) => (
        <td key={k} className={cell}>
          {t === "company" ? (
            <select value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}><option value="">-</option>{companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
          ) : t === "employee" ? (
            <select value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}><option value="">-</option>{employees.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select>
          ) : t === "method" ? (
            <select value={f[k] || "direct"} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls}><option value="direct">直接给付</option><option value="bank_acceptance">银行承兑</option></select>
          ) : t === "date" ? (
            <DatePicker value={f[k] || new Date().toISOString().slice(0,10)} onChange={v => setF({...f, [k]: v})} />
          ) : (
            <input type={t === "number" ? "number" : "text"} step="0.01" value={f[k] || ""} onChange={e => setF({...f, [k]: e.target.value})} className={inputCls} placeholder={t === "number" ? "0" : ""} onKeyDown={e => { if (e.key === "Enter") save(); }} />
          )}
        </td>
      ))}
      <td className={`${cell} whitespace-nowrap`}>
        <button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button>
        <button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button>
      </td>
    </tr>
  );
}

function FinanceEditorV2({
  module,
  initial,
  companies,
  employees,
  onClose,
  onSave,
}: {
  module: string;
  initial: Record<string, unknown> | null;
  companies: CompanyRecord[];
  employees: EmployeeRecord[];
  onClose: () => void;
  onSave: (d: Record<string, unknown>) => Promise<void>;
}) {
  const meta = FINANCE_META[module];
  const seed: Record<string, string> = {
    payment_method: "direct",
    person_count: "1",
    base_salary: "0",
    allowance: "0",
    deduction: "0",
  };
  for (const [k] of meta.fields)
    if (initial?.[k] != null) seed[k] = String(initial[k]).slice(0, 10);
  const [f, setF] = useState(seed);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4">
      <div className="max-h-[90vh] w-full max-w-xl overflow-auto rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>
            {initial ? "编辑" : "新增"}
            {meta.title}
          </b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3 p-5">
          {meta.fields.map(([k, l, t]) => (
            <JournalField key={k} label={l}>
              {t === "company" ? (
                <select
                  className="journal-input"
                  value={f[k] || ""}
                  onChange={(e) => setF({ ...f, [k]: e.target.value })}
                >
                  <option value="">请选择</option>
                  {companies.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name}
                    </option>
                  ))}
                </select>
              ) : t === "employee" ? (
                <select
                  className="journal-input"
                  value={f[k] || ""}
                  onChange={(e) => setF({ ...f, [k]: e.target.value })}
                >
                  <option value="">请选择</option>
                  {employees.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name}
                    </option>
                  ))}
                </select>
              ) : t === "method" ? (
                <select
                  className="journal-input"
                  value={f[k] || "direct"}
                  onChange={(e) => setF({ ...f, [k]: e.target.value })}
                >
                  <option value="direct">直接给付</option>
                  <option value="bank_acceptance">银行承兑</option>
                </select>
              ) : (
                <input
                  type={t}
                  className="journal-input"
                  value={f[k] || ""}
                  onChange={(e) => setF({ ...f, [k]: e.target.value })}
                />
              )}
            </JournalField>
          ))}
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            onClick={() => {
              const d: Record<string, unknown> = {};
              for (const [k, , t] of meta.fields)
                d[k] =
                  t === "number"
                    ? Number(f[k] || 0)
                    : ["company", "employee"].includes(t)
                      ? f[k]
                        ? Number(f[k])
                        : null
                      : f[k] || null;
              onSave(d);
            }}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}
function FinanceDataPage({
  module,
  setError,
}: {
  module: string;
  setError: (v: string) => void;
}) {
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [open, setOpen] = useState(false);
  const [companies, setCompanies] = useState<CompanyRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const meta = FINANCE_META[module];
  const load = useCallback(async () => {
    try {
      const [r, c, e] = await Promise.all([
        listFinanceModule(module),
        listCompanies(),
        listEmployees(),
      ]);
      setRows(r.rows);
      setCompanies(c.rows);
      setEmployees(e.rows);
    } catch (x) {
      setError(readError(x));
    }
  }, [module, setError]);
  useEffect(() => {
    load();
  }, [load]);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex justify-between border-b bg-[#f8faf9] p-4">
        <div>
          <b>{meta.title}</b>
          <div className="text-xs text-[#7d8881]">
            正式数据库记录 · 共 {rows.length} 条
          </div>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          新增
        </Button>
      </div>
      <div className="flex-1 overflow-auto">
        {!rows.length ? (
          <EmptyState
            title={`暂无${meta.title}数据`}
            description="无需导入，可以直接新增。"
          />
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-[#f5f7f6]">
              <tr>
                {Object.keys(rows[0])
                  .slice(1, 9)
                  .map((x) => (
                    <th key={x} className="px-3 py-2 text-left text-xs">
                      {x}
                    </th>
                  ))}
                <th className="px-3 py-2 text-left text-xs">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={String(r.id || i)} className="border-t">
                  {Object.keys(rows[0])
                    .slice(1, 9)
                    .map((k) => (
                      <td key={k} className="px-3 py-2 text-xs">
                        {String(r[k] ?? "-")}
                      </td>
                    ))}
                  <td className="px-3 py-2 text-xs">
                    {["salary", "rebate"].includes(module) &&
                    r.status !== "confirmed" ? (
                      <button
                        className="text-[#216c40]"
                        onClick={async () => {
                          await approveFinanceRecord(module, Number(r.id));
                          await load();
                        }}
                      >
                        审批
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open && (
        <FinanceEditor
          module={module}
          companies={companies}
          employees={employees}
          onClose={() => setOpen(false)}
          onSave={async (d) => {
            await createFinanceRecord(module, d);
            setOpen(false);
            await load();
          }}
        />
      )}
    </div>
  );
}
function FinanceEditor({
  module,
  companies,
  employees,
  onClose,
  onSave,
}: {
  module: string;
  companies: CompanyRecord[];
  employees: EmployeeRecord[];
  onClose: () => void;
  onSave: (d: Record<string, unknown>) => Promise<void>;
}) {
  const meta = FINANCE_META[module];
  const [f, setF] = useState<Record<string, string>>({
    payment_method: "direct",
    person_count: "1",
    base_salary: "0",
    allowance: "0",
    deduction: "0",
  });
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4">
      <div className="w-full max-w-xl rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>新增{meta.title}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3 p-5">
          {meta.fields.map(([key, label, type]) => (
            <JournalField key={key} label={label}>
              {type === "company" ? (
                <select
                  className="journal-input"
                  value={f[key] || ""}
                  onChange={(e) => setF({ ...f, [key]: e.target.value })}
                >
                  <option value="">请选择</option>
                  {companies.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name}
                    </option>
                  ))}
                </select>
              ) : type === "employee" ? (
                <select
                  className="journal-input"
                  value={f[key] || ""}
                  onChange={(e) => setF({ ...f, [key]: e.target.value })}
                >
                  <option value="">请选择</option>
                  {employees.map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.name}
                    </option>
                  ))}
                </select>
              ) : type === "method" ? (
                <select
                  className="journal-input"
                  value={f[key] || "direct"}
                  onChange={(e) => setF({ ...f, [key]: e.target.value })}
                >
                  <option value="direct">直接给付</option>
                  <option value="bank_acceptance">银行承兑</option>
                </select>
              ) : (
                <input
                  type={type}
                  className="journal-input"
                  value={f[key] || ""}
                  onChange={(e) => setF({ ...f, [key]: e.target.value })}
                />
              )}
            </JournalField>
          ))}
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            onClick={() => {
              const d: Record<string, unknown> = {};
              for (const [k, , t] of meta.fields)
                d[k] =
                  t === "number"
                    ? Number(f[k] || 0)
                    : ["company", "employee"].includes(t)
                      ? f[k]
                        ? Number(f[k])
                        : null
                      : f[k] || null;
              onSave(d);
            }}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}
function AttendanceEditor({
  row,
  employees,
  onClose,
  onSave,
}: {
  row: AttendanceRecord | null;
  employees: EmployeeRecord[];
  onClose: () => void;
  onSave: (d: Omit<AttendanceRecord, "id" | "employee_name">) => Promise<void>;
}) {
  const [f, setF] = useState({
    employee_id: row?.employee_id || employees[0]?.id || 0,
    work_date: row?.work_date || new Date().toISOString().slice(0, 10),
    status: row?.status || "normal",
    hours: row?.hours ?? 8,
    deduction_amount: row?.deduction_amount ?? 0,
    remark: row?.remark || "",
  });
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35">
      <div className="w-full max-w-lg rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>{row ? "编辑考勤" : "新增考勤"}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3 p-5">
          <JournalField label="人员">
            <select
              className="journal-input"
              value={f.employee_id}
              onChange={(e) =>
                setF({ ...f, employee_id: Number(e.target.value) })
              }
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </JournalField>
          <JournalField label="日期">
            <DatePicker value={f.work_date} onChange={(v) => setF({ ...f, work_date: v })} />
          </JournalField>
          <JournalField label="状态">
            <select
              className="journal-input"
              value={f.status}
              onChange={(e) =>
                setF({
                  ...f,
                  status: e.target.value as AttendanceRecord["status"],
                })
              }
            >
              <option value="normal">正常</option>
              <option value="late">迟到</option>
              <option value="absent">旷工</option>
              <option value="leave">请假</option>
            </select>
          </JournalField>
          <JournalField label="工时">
            <input
              type="number"
              className="journal-input"
              value={f.hours}
              onChange={(e) => setF({ ...f, hours: Number(e.target.value) })}
            />
          </JournalField>
          <JournalField label="扣款">
            <input
              type="number"
              className="journal-input"
              value={f.deduction_amount}
              onChange={(e) =>
                setF({ ...f, deduction_amount: Number(e.target.value) })
              }
            />
          </JournalField>
          <JournalField label="备注">
            <input
              className="journal-input"
              value={f.remark}
              onChange={(e) => setF({ ...f, remark: e.target.value })}
            />
          </JournalField>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={() => onSave(f)}>保存</Button>
        </div>
      </div>
    </div>
  );
}

void FinanceDataPage;
function DatabaseContractPage({ setError, reloadTrigger, onClear, onImport }: { setError: (v: string) => void; reloadTrigger: number; onClear: (m: string) => void; onImport: () => void }) {
  const [rows, setRows] = useState<ContractRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [expiry, setExpiry] = useState<
    Array<{ contract_id: number; days_left: number }>
  >([]);
  const [editId, setEditId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const [c, e, w] = await Promise.all([
        listContracts(undefined, targetPage, pageSize),
        listEmployees('', 1, 1000),
        listContractExpiryWarnings(),
      ]);
      setRows(c.rows);
      setTotal(c.total);
      setPage(targetPage);
      setEmployees(e.rows);
      setExpiry(w.rows);
    } catch (x) {
      setError(readError(x));
    }
  }, [pageSize, setError]);
  useEffect(() => {
    load(1);
  }, [load, reloadTrigger]);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex justify-between border-b bg-[#f8faf9] p-4">
        <div>
          <b>合同管理</b>
          <div className="text-xs text-[#7d8881]">
            {expiry.length} 份合同将在15天内到期
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("contract")}>
            <Trash2 className="mr-2 h-4 w-4" />
            清空
          </Button>
          <Button variant="outline" asChild><a href={contractsExportUrl()}><Download className="mr-2 h-4 w-4" />导出</a></Button>
          <Button variant="outline" onClick={onImport}><Upload className="mr-2 h-4 w-4" />导入</Button>
        <Button
          className="bg-[#173f2a]"
          onClick={() => employees.length ? setEditId(-1) : setError("请先新增人员")}
        >
          <Plus className="mr-2 h-4 w-4" />
          新增合同
        </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>{["员工","合同编号","签订日期","起止日期","状态","预警",""].map(x => <th key={x} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{x}</th>)}</tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]"><td colSpan={7} className="px-2 py-1">
              {editId === -1 ? null : <button onClick={() => employees.length ? setEditId(-1) : setError("请先新增人员")} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium"><Plus className="h-3.5 w-3.5" /> 新增</button>}
            </td></tr>
            {editId === -1 && <ContractNewRow employees={employees} onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />}
            {rows.map(r => {
              const emp = employees.find(e => e.id === r.employee_id);
              const warn = expiry.find(x => x.contract_id === r.id);
              return <ContractRow key={r.id} row={r} empName={emp?.name} warn={warn} employees={employees} onSaved={() => { load(); setEditId(null); }} isEditing={editId === r.id} onEdit={() => setEditId(r.id)} />;
            })}
            {!rows.length && <tr><td colSpan={7}><EmptyState title="暂无合同" description="点击上方「+ 新增」录入" /></td></tr>}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
    </div>
  );
}
function ContractEditor({
  row,
  employees,
  onClose,
  onSave,
}: {
  row: ContractRecord | null;
  employees: EmployeeRecord[];
  onClose: () => void;
  onSave: (
    d: Partial<ContractRecord> & { company_id?: number | null },
  ) => Promise<void>;
}) {
  const [f, setF] = useState({
    employee_id: String(row?.employee_id || employees[0]?.id || ""),
    contract_type: row?.contract_type || "employee",
    contract_no: row?.contract_no || "",
    sign_date: row?.sign_date || "",
    start_date: row?.start_date || new Date().toISOString().slice(0, 10),
    end_date: row?.end_date || "",
    remark: row?.remark || "",
  });
  const emp = employees.find((e) => e.id === Number(f.employee_id));
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35">
      <div className="w-full max-w-lg rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>{row ? "编辑合同" : "新增合同"}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-3 p-5">
          <JournalField label="员工">
            <select
              disabled={!!row}
              className="journal-input"
              value={f.employee_id}
              onChange={(e) => setF({ ...f, employee_id: e.target.value })}
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </JournalField>
          <JournalField label="合同编号">
            <input
              className="journal-input"
              value={f.contract_no}
              onChange={(e) => setF({ ...f, contract_no: e.target.value })}
            />
          </JournalField>
          <div className="grid grid-cols-3 gap-2">
            <JournalField label="签订日">
              <DatePicker value={f.sign_date} onChange={(v) => setF({ ...f, sign_date: v })} />
            </JournalField>
            <JournalField label="开始日">
              <DatePicker value={f.start_date} onChange={(v) => setF({ ...f, start_date: v })} />
            </JournalField>
            <JournalField label="结束日">
              <DatePicker value={f.end_date} onChange={(v) => setF({ ...f, end_date: v })} />
            </JournalField>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={!f.end_date}
            onClick={() =>
              onSave({
                ...f,
                employee_id: Number(f.employee_id),
                company_id: emp?.company_id,
                sign_date: f.sign_date || null,
              })
            }
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}

function DatabaseEmployeePage({
  onImport,
  setError,
  reloadTrigger,
  onClear,
}: {
  onImport: () => void;
  setError: (v: string) => void;
  reloadTrigger: number;
  onClear: (m: string) => void;
}) {
  const [rows, setRows] = useState<EmployeeRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [warnings, setWarnings] = useState<
    Array<{ employee_id: number; employee_name: string; days_worked: number }>
  >([]);
  const [search, setSearch] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [detail, setDetail] = useState<EmployeeDetail | null>(null);
  const [companies, setCompanies] = useState<CompanyRecord[]>([]);
  const [positions, setPositions] = useState<PositionRecord[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const [e, w, c, pos] = await Promise.all([
        listEmployees(search, targetPage, pageSize),
        listUnsignedContractWarnings(),
        listCompanies('', '', 1, 1000),
        listPositions(undefined, 1, 1000),
      ]);
      setRows(e.rows);
      setTotal(e.total);
      setPage(targetPage);
      setWarnings(w.rows);
      setCompanies(c.rows);
      setPositions(pos.rows);
    } catch (x) {
      setError(readError(x));
    }
  }, [search, pageSize, setError]);
  useEffect(() => {
    load(1);
  }, [load, reloadTrigger]);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex flex-wrap justify-between gap-3 border-b bg-[#f8faf9] p-4">
        <div>
          <b>人员档案</b>
          <div className="mt-1 text-xs text-[#7d8881]">
            {warnings.length} 人入职超过20天仍未签合同
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("employee")}>
            <Trash2 className="mr-2 h-4 w-4" />
            清空
          </Button>
          <Button variant="outline" asChild><a href={employeesExportUrl()}><Download className="mr-2 h-4 w-4" />导出</a></Button>
          <input
            className="journal-input max-w-64"
            placeholder="搜索姓名或手机号"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button variant="outline" onClick={onImport}>
            <Upload className="mr-2 h-4 w-4" />
            导入
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>
              {["姓名","身份证","手机号","企业/岗位","入职日期","合同","状态",""].map(x => <th key={x} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{x}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]">
              <td colSpan={8} className="px-2 py-1">
                {editId === -1 ? (
                  <EmpNewRow companies={companies} positions={positions} onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />
                ) : (
                  <button onClick={() => companies.length ? setEditId(-1) : setError("请先在企业管理中新增企业，再新增人员")} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium">
                    <Plus className="h-3.5 w-3.5" /> 新增
                  </button>
                )}
              </td>
            </tr>
            {rows.map(r => {
              const warn = warnings.some(w => w.employee_id === r.id);
              return (
                <EmpRow key={r.id} row={r} warn={warn} companies={companies} positions={positions} onSaved={() => { load(); setEditId(null); }} isEditing={editId === r.id} onEdit={() => setEditId(r.id)}
                  onDetail={async () => { try { setDetail(await getEmployeeDetail(r.id)); } catch(x) { setError(readError(x)); } }}
                />
              );
            })}
            {!rows.length && <tr><td colSpan={8}><EmptyState title="暂无人员" description="点击上方「+ 新增」录入" /></td></tr>}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
      {detail && (
        <EmployeeDetailDrawer detail={detail} onClose={() => setDetail(null)} />
      )}
    </div>
  );
}

function EmployeeDetailDrawer({
  detail,
  onClose,
}: {
  detail: EmployeeDetail;
  onClose: () => void;
}) {
  const e = detail.employee;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <aside className="flex h-full w-full max-w-2xl flex-col bg-[#fbfcfa] shadow-2xl">
        <div className="flex items-center justify-between border-b bg-[#173f2a] px-6 py-5 text-white">
          <div>
            <div className="text-xl font-semibold">{e.name}</div>
            <div className="mt-1 text-xs text-white/65">
              {e.company_name} · {e.position_name || "未指定岗位"}
            </div>
          </div>
          <Button
            size="icon"
            variant="ghost"
            className="text-white hover:bg-white/10 hover:text-white"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 space-y-4 overflow-auto p-5">
          <section className="grid grid-cols-2 gap-3 rounded-xl border bg-white p-4 text-sm">
            <DetailItem label="身份证" value={e.id_card_masked} />
            <DetailItem label="手机号" value={e.phone} />
            <DetailItem
              label="性别"
              value={e.gender === "male" ? "男" : "女"}
            />
            <DetailItem label="入职日期" value={e.entry_date} />
            <DetailItem label="地址" value={e.address || "-"} />
            <DetailItem
              label="状态"
              value={e.status === "active" ? "在职" : "离职"}
            />
          </section>
          <DetailSection
            title={`合同（${detail.contracts.length}）`}
            empty="暂无关联合同"
          >
            {detail.contracts.map((x) => (
              <div
                key={x.id}
                className="grid grid-cols-3 gap-2 border-t py-3 text-xs"
              >
                <span>{x.contract_no || "未编号"}</span>
                <span>
                  {x.start_date} ~ {x.end_date}
                </span>
                <span>{x.status}</span>
              </div>
            ))}
          </DetailSection>
          <DetailSection
            title={`最近考勤（${detail.attendance.length}）`}
            empty="暂无考勤记录"
          >
            {detail.attendance.map((x, i) => (
              <div
                key={i}
                className="grid grid-cols-4 gap-2 border-t py-3 text-xs"
              >
                <span>{x.work_date}</span>
                <span>{x.status}</span>
                <span>{x.hours} 小时</span>
                <span>扣款 ¥{x.deduction_amount}</span>
              </div>
            ))}
          </DetailSection>
          <DetailSection
            title={`工资记录（${detail.payroll.length}）`}
            empty="暂无工资记录"
          >
            {detail.payroll.map((x, i) => (
              <div
                key={i}
                className="grid grid-cols-4 gap-2 border-t py-3 text-xs"
              >
                <span>{x.salary_month}</span>
                <span>基本 ¥{x.base_salary}</span>
                <span>扣款 ¥{x.deduction}</span>
                <span className="font-semibold text-[#216c40]">
                  实发 ¥{x.net_pay}
                </span>
              </div>
            ))}
          </DetailSection>
        </div>
      </aside>
    </div>
  );
}
function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-[#7d8881]">{label}</div>
      <div className="mt-1 font-medium text-[#26372d]">{value}</div>
    </div>
  );
}
function DetailSection({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: ReactNode;
}) {
  const has = Array.isArray(children) && children.length > 0;
  return (
    <section className="rounded-xl border bg-white p-4">
      <h3 className="mb-2 text-sm font-semibold text-[#26372d]">{title}</h3>
      {has ? (
        children
      ) : (
        <div className="border-t py-5 text-center text-xs text-[#8a958e]">
          {empty}
        </div>
      )}
    </section>
  );
}
function EmployeeEditor({
  row,
  companies,
  positions,
  onClose,
  onSave,
}: {
  row: EmployeeRecord | null;
  companies: CompanyRecord[];
  positions: PositionRecord[];
  onClose: () => void;
  onSave: (d: Record<string, unknown>) => Promise<void>;
}) {
  const [f, setF] = useState({
    name: row?.name || "",
    id_card_number: "",
    phone: row?.phone || "",
    gender: row?.gender || "male",
    address: row?.address || "",
    company_id: String(row?.company_id || companies[0]?.id || ""),
    position_id: String(row?.position_id || ""),
    entry_date: row?.entry_date || new Date().toISOString().slice(0, 10),
  });
  const pos = positions.filter((p) => p.company_id === Number(f.company_id));
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35">
      <div className="w-full max-w-xl rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>{row ? "编辑人员" : "新增人员"}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-3 p-5 md:grid-cols-2">
          <JournalField label="姓名">
            <input
              className="journal-input"
              value={f.name}
              onChange={(e) => setF({ ...f, name: e.target.value })}
            />
          </JournalField>
          {!row && (
            <JournalField label="身份证号">
              <input
                className="journal-input"
                value={f.id_card_number}
                onChange={(e) => setF({ ...f, id_card_number: e.target.value })}
              />
            </JournalField>
          )}
          <JournalField label="手机号">
            <input
              className="journal-input"
              value={f.phone}
              onChange={(e) => setF({ ...f, phone: e.target.value })}
            />
          </JournalField>
          <JournalField label="性别">
            <select
              className="journal-input"
              value={f.gender}
              onChange={(e) =>
                setF({ ...f, gender: e.target.value as "male" | "female" })
              }
            >
              <option value="male">男</option>
              <option value="female">女</option>
            </select>
          </JournalField>
          <JournalField label="企业">
            <select
              className="journal-input"
              value={f.company_id}
              onChange={(e) =>
                setF({ ...f, company_id: e.target.value, position_id: "" })
              }
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </JournalField>
          <JournalField label="岗位">
            <select
              className="journal-input"
              value={f.position_id}
              onChange={(e) => setF({ ...f, position_id: e.target.value })}
            >
              <option value="">未指定</option>
              {pos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </JournalField>
          <JournalField label="入职日期">
            <DatePicker value={f.entry_date} onChange={(v) => setF({ ...f, entry_date: v })} />
          </JournalField>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            onClick={() =>
              onSave({
                ...f,
                company_id: Number(f.company_id),
                position_id: f.position_id ? Number(f.position_id) : null,
              })
            }
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}

function DatabaseCompanyPage({
  onImport,
  setError,
  reloadTrigger,
  onClear,
}: {
  onImport: () => void;
  setError: (value: string) => void;
  reloadTrigger: number;
  onClear: (m: string) => void;
}) {
  const [rows, setRows] = useState<CompanyRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const result = await listCompanies(search, '', targetPage, pageSize);
      setRows(result.rows);
      setTotal(result.total);
      setPage(targetPage);
    } catch (e) {
      setError(readError(e));
    }
  }, [search, pageSize, setError]);
  useEffect(() => {
    load(1);
  }, [load, reloadTrigger]);
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b bg-[#f8faf9] p-4">
        <div className="flex h-9 min-w-72 items-center gap-2 rounded-md border bg-white px-3">
          <Search className="h-4 w-4 text-[#849087]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") load(1);
            }}
            placeholder="搜索企业、联系人或电话"
            className="flex-1 bg-transparent text-sm outline-none"
          />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("company")}>
            <Trash2 className="mr-2 h-4 w-4" />
            清空
          </Button>
          <Button variant="outline" asChild>
            <a href={companiesExportUrl()}>
              <Download className="mr-2 h-4 w-4" />
              导出 Excel
            </a>
          </Button>
          <Button variant="outline" onClick={onImport}>
            <Upload className="mr-2 h-4 w-4" />
            导入
          </Button>
          <Button className="bg-[#173f2a]" onClick={() => setEditId(-1)}>
            <Plus className="mr-2 h-4 w-4" />
            新增企业
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>
              {["企业名称","联系人","电话","合作状态","合作期限","回款期限",""].map(x => <th key={x} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{x}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]">
              <td colSpan={7} className="px-2 py-1">
                {editId === -1 ? (
                  <CompanyNewRow onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />
                ) : (
                  <button onClick={() => setEditId(-1)} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium">
                    <Plus className="h-3.5 w-3.5" /> 新增
                  </button>
                )}
              </td>
            </tr>
            {rows.map(r => (
              <CompanyRow key={r.id} row={r} onSaved={() => { load(); setEditId(null); }} isEditing={editId === r.id} onEdit={() => setEditId(r.id)} />
            ))}
            {!rows.length && <tr><td colSpan={7}><EmptyState title="暂无企业" description="点击上方「+ 新增」录入" /></td></tr>}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
    </div>
  );
}

function CompanyEditor({
  row,
  onClose,
  onSave,
}: {
  row: CompanyRecord | null;
  onClose: () => void;
  onSave: (data: Partial<CompanyRecord>) => Promise<void>;
}) {
  const [form, setForm] = useState({
    name: row?.name || "",
    contact_person: row?.contact_person || "",
    contact_phone: row?.contact_phone || "",
    address: row?.address || "",
    business_license_no: row?.business_license_no || "",
    cooperation_status: row?.cooperation_status || "active",
    cooperation_start_date: row?.cooperation_start_date || "",
    cooperation_end_date: row?.cooperation_end_date || "",
    default_receivable_days: String(row?.default_receivable_days ?? ""),
    remark: row?.remark || "",
  });
  const [saving, setSaving] = useState(false);
  const u = (k: string, v: string) => setForm((x) => ({ ...x, [k]: v }));
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>{row ? "编辑企业" : "新增企业"}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-3 p-5 md:grid-cols-2">
          <JournalField label="企业名称">
            <input
              className="journal-input"
              value={form.name}
              onChange={(e) => u("name", e.target.value)}
            />
          </JournalField>
          <JournalField label="联系人">
            <input
              className="journal-input"
              value={form.contact_person}
              onChange={(e) => u("contact_person", e.target.value)}
            />
          </JournalField>
          <JournalField label="联系电话">
            <input
              className="journal-input"
              value={form.contact_phone}
              onChange={(e) => u("contact_phone", e.target.value)}
            />
          </JournalField>
          <JournalField label="合作状态">
            <select
              className="journal-input"
              value={form.cooperation_status}
              onChange={(e) => u("cooperation_status", e.target.value)}
            >
              <option value="active">正常合作</option>
              <option value="paused">暂停合作</option>
              <option value="terminated">终止合作</option>
            </select>
          </JournalField>
          <JournalField label="合作开始">
            <DatePicker value={form.cooperation_start_date} onChange={(v) => u("cooperation_start_date", v)} />
          </JournalField>
          <JournalField label="合作结束">
            <DatePicker value={form.cooperation_end_date} onChange={(v) => u("cooperation_end_date", v)} />
          </JournalField>
          <JournalField label="默认回款天数">
            <input
              type="number"
              className="journal-input"
              value={form.default_receivable_days}
              onChange={(e) => u("default_receivable_days", e.target.value)}
            />
          </JournalField>
          <JournalField label="营业执照号">
            <input
              className="journal-input"
              value={form.business_license_no}
              onChange={(e) => u("business_license_no", e.target.value)}
            />
          </JournalField>
          <div className="md:col-span-2">
            <JournalField label="地址">
              <input
                className="journal-input"
                value={form.address}
                onChange={(e) => u("address", e.target.value)}
              />
            </JournalField>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={!form.name || saving}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave({
                  ...form,
                  default_receivable_days: form.default_receivable_days
                    ? Number(form.default_receivable_days)
                    : null,
                  cooperation_start_date: form.cooperation_start_date || null,
                  cooperation_end_date: form.cooperation_end_date || null,
                } as Partial<CompanyRecord>);
              } finally {
                setSaving(false);
              }
            }}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}

function DatabasePositionPage({
  setError,
  reloadTrigger,
  onClear,
  onImport,
}: {
  setError: (value: string) => void;
  reloadTrigger: number;
  onClear: (m: string) => void;
  onImport: () => void;
}) {
  const [companies, setCompanies] = useState<CompanyRecord[]>([]);
  const [rows, setRows] = useState<PositionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [editId, setEditId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    try {
      const [c, pos] = await Promise.all([listCompanies('', '', 1, 1000), listPositions(undefined, targetPage, pageSize)]);
      setCompanies(c.rows);
      setRows(pos.rows);
      setTotal(pos.total);
      setPage(targetPage);
    } catch (e) { setError(readError(e)); }
  }, [pageSize, setError]);
  useEffect(() => { load(1); }, [load, reloadTrigger]);
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border bg-white">
      <div className="flex justify-between border-b bg-[#f8faf9] p-4">
        <div><b>岗位管理</b><div className="text-xs text-[#7d8881]">岗位必须关联一家企业</div></div>
        <div className="flex gap-2">
          <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("position")}><Trash2 className="mr-2 h-4 w-4" />清空</Button>
          <Button variant="outline" asChild><a href={positionsExportUrl()}><Download className="mr-2 h-4 w-4" />导出</a></Button>
          <Button variant="outline" onClick={onImport}><Upload className="mr-2 h-4 w-4" />导入</Button>
          <Button className="bg-[#173f2a]" onClick={() => companies.length ? setEditId(-1) : setError("请先新增企业")}><Plus className="mr-2 h-4 w-4" />新增岗位</Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full table-fixed text-sm">
          <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>{["企业","岗位","日单价","需求人数","状态",""].map(x => <th key={x} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{x}</th>)}</tr>
          </thead>
          <tbody>
            <tr className="border-b bg-[#fafcfb]"><td colSpan={6} className="px-2 py-1">
              {editId === -1 ? null : <button onClick={() => companies.length ? setEditId(-1) : setError("请先新增企业")} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium"><Plus className="h-3.5 w-3.5" /> 新增</button>}
            </td></tr>
            {editId === -1 && <PosNewRow companies={companies} onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />}
            {rows.map(r => <PosRow key={r.id} row={r} companies={companies} onSaved={() => { load(); setEditId(null); }} isEditing={editId === r.id} onEdit={() => setEditId(r.id)} />)}
            {!rows.length && <tr><td colSpan={6}><EmptyState title="暂无岗位" description="点击上方「+ 新增」录入" /></td></tr>}
          </tbody>
        </table>
      </div>
      <PaginationBar total={total} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
    </div>
  );
}

function PositionEditor({
  row,
  companies,
  onClose,
  onSave,
}: {
  row: PositionRecord | null;
  companies: CompanyRecord[];
  onClose: () => void;
  onSave: (d: Partial<PositionRecord>) => Promise<void>;
}) {
  const [form, setForm] = useState({
    company_id: String(row?.company_id || companies[0]?.id || ""),
    name: row?.name || "",
    daily_rate: String(row?.daily_rate ?? ""),
    required_count: String(row?.required_count ?? ""),
    status: row?.status || "recruiting",
    description: row?.description || "",
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35">
      <div className="w-full max-w-lg rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <b>{row ? "编辑岗位" : "新增岗位"}</b>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-3 p-5">
          <JournalField label="所属企业">
            <select
              className="journal-input"
              value={form.company_id}
              onChange={(e) => setForm({ ...form, company_id: e.target.value })}
            >
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </JournalField>
          <JournalField label="岗位名称">
            <input
              className="journal-input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </JournalField>
          <div className="grid grid-cols-2 gap-3">
            <JournalField label="日单价">
              <input
                type="number"
                className="journal-input"
                value={form.daily_rate}
                onChange={(e) =>
                  setForm({ ...form, daily_rate: e.target.value })
                }
              />
            </JournalField>
            <JournalField label="需求人数">
              <input
                type="number"
                className="journal-input"
                value={form.required_count}
                onChange={(e) =>
                  setForm({ ...form, required_count: e.target.value })
                }
              />
            </JournalField>
          </div>
          <JournalField label="描述">
            <input
              className="journal-input"
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
          </JournalField>
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={!form.name}
            onClick={() =>
              onSave({
                company_id: Number(form.company_id),
                name: form.name,
                daily_rate: form.daily_rate ? Number(form.daily_rate) : null,
                required_count: form.required_count
                  ? Number(form.required_count)
                  : null,
                status: form.status,
                description: form.description,
              })
            }
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}

function DatabaseJournalPage({
  onImport,
  setError,
  legacyCount,
  onOpenLegacy,
  reloadTrigger,
  onClear,
}: {
  onImport: () => void;
  setError: (value: string) => void;
  legacyCount: number;
  onOpenLegacy: () => void;
  reloadTrigger: number;
  onClear: (m: string) => void;
}) {
  const [result, setResult] = useState<Awaited<
    ReturnType<typeof listJournalTransactions>
  > | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const yearStart = `${new Date().getFullYear()}-01-01`;
  const [direction, setDirection] = useState<JournalDirectionFilter>("all");
  const [ledger, setLedger] = useState<"all" | "cash" | "bank">("all");
  const [dateFrom, setDateFrom] = useState(yearStart);
  const [dateTo, setDateTo] = useState(today);
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(30);
  const [loading, setLoading] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  const load = useCallback(async (p?: number) => {
    const targetPage = p || page;
    setLoading(true);
    setError("");
    try {
      setResult(
        await listJournalTransactions({
          direction: direction === "all" ? undefined : direction,
          ledger_type: ledger === "all" ? undefined : ledger,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          search: keyword || undefined,
          page: targetPage,
          page_size: pageSize,
        }),
      );
      setPage(targetPage);
    } catch (err) {
      setError(readError(err));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, direction, ledger, keyword, pageSize, setError]);

  useEffect(() => { load(1); setPage(1); }, [load, reloadTrigger]);

  const exportUrl = journalExportUrl({
    direction: direction === "all" ? undefined : direction,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: keyword || undefined,
  });

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-[#dfe6e1] bg-white">
      {legacyCount > 0 && (!result || result.rows.length === 0) && (
        <div className="flex items-center justify-between border-b border-[#ecdcae] bg-[#fff9e8] px-4 py-3 text-sm text-[#765b18]">
          <span>检测到 {legacyCount} 张旧版日记账表；它们尚未确认写入正式数据库。</span>
          <Button size="sm" variant="outline" onClick={onOpenLegacy}>查看原表</Button>
        </div>
      )}
      <div className="shrink-0 border-b border-[#e8ede9] bg-[#f8faf9] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-2">
            <div className="flex rounded-lg border border-[#dbe4de] bg-white p-1">
              {(["all","income","expense"] as const).map(key => (
                <button key={key} type="button" onClick={() => setDirection(key)}
                  className={`min-h-9 rounded-md px-3 text-sm font-medium transition ${direction === key ? "bg-[#173f2a] text-white" : "text-[#5d6962] hover:bg-[#f0f4f1]"}`}>
                  {{all:"全部收支",income:"收入",expense:"支出"}[key]}
                </button>
              ))}
            </div>
            <div className="flex rounded-lg border border-[#dbe4de] bg-white p-1">
              {(["all","cash","bank"] as const).map(key => (
                <button key={key} type="button" onClick={() => setLedger(key)}
                  className={`min-h-9 rounded-md px-3 text-sm font-medium transition ${ledger === key ? "bg-[#173f2a] text-white" : "text-[#5d6962] hover:bg-[#f0f4f1]"}`}>
                  {{all:"全部账簿",cash:"现金",bank:"银行"}[key]}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="text-[#f53f3f] hover:bg-[#fff1f0] hover:text-[#f53f3f]" onClick={() => onClear("journal")}>
              <Trash2 className="mr-2 h-4 w-4" />
              清空
            </Button>
            <Button
              variant="outline"
              onClick={() => downloadAuthenticated(exportUrl)}
            >
              <Download className="mr-2 h-4 w-4" />
              导出 Excel
            </Button>
            <Button variant="outline" onClick={onImport}>
              <Upload className="mr-2 h-4 w-4" />
              导入 Excel
            </Button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <DatePicker value={dateFrom} onChange={setDateFrom} />
          <span className="text-sm text-[#86909c]">至</span>
          <DatePicker value={dateTo} onChange={setDateTo} />
          <div className="flex h-9 items-center gap-2 rounded-md border border-[#dbe2dd] bg-white px-3">
            <Search className="h-4 w-4 text-[#849087]" />
            <input
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") load();
              }}
              placeholder="搜索摘要、方式"
              className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            />
          </div>
          <Button variant="outline" onClick={() => load(1)} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "查询"}
          </Button>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3">
          <ImportCountCard
            label="收入合计"
            value={result?.income_total || 0}
            tone="success"
          />
          <ImportCountCard
            label="支出合计"
            value={result?.expense_total || 0}
            tone="danger"
          />
          <ImportCountCard
            label="净流入"
            value={result?.net_flow || 0}
            tone="neutral"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full table-fixed border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
            <tr>
              {["日期","账簿","收支","金额","方式","摘要","来源",""].map((label) => (
                <th key={label} className="px-2 py-2 text-left text-xs font-medium text-[#526058]">{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-[#e2e7e4] bg-[#fafcfb]">
              <td colSpan={8} className="px-2 py-1">
                {editId === -1 ? (
                  <JournalNewRowInline onSaved={() => { load(); setEditId(null); }} onCancel={() => setEditId(null)} />
                ) : (
                  <button onClick={() => setEditId(-1)} className="flex items-center gap-1 text-xs text-[#216c40] hover:text-[#173f2a] font-medium">
                    <Plus className="h-3.5 w-3.5" /> 新增
                  </button>
                )}
              </td>
            </tr>
            {result?.rows.map((row) => (
              <JournalRow key={row.id} row={row} onSaved={() => { load(); setEditId(null); }} isEditing={editId === row.id} onEdit={() => setEditId(row.id)} />
            ))}
            {(!result || result.rows.length === 0) && (
              <tr><td colSpan={8}><EmptyState title="暂无日记账流水" description="点击上方「+ 新增」录入第一条记录" /></td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="shrink-0 border-t border-[#e7ece9] bg-[#fafcfb] px-4 py-2.5 flex items-center justify-between text-xs text-[#7d8881]">
        <span>共 {result?.total || 0} 条 · 点击行编辑 | Tab 跳格 | Enter 保存</span>
        <PaginationBar total={result?.total || 0} page={page} pageSize={pageSize} onPageChange={(p) => load(p)} onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); }} />
      </div>
    </div>
  );
}

function JournalRow({ row, onSaved, isEditing, onEdit }: { row: JournalTransaction; onSaved: () => void; isEditing: boolean; onEdit: () => void }) {
  const [f, setF] = useState({
    transaction_date: row.transaction_date,
    ledger_type: row.ledger_type,
    direction: row.direction,
    category: row.category,
    amount: String(row.amount),
    payment_method: row.payment_method || "",
    summary: row.summary || "",
  });
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await updateJournalTransaction(row.id, {
        ...f,
        amount: Number(f.amount),
      } as Partial<JournalTransaction>);
      onSaved();
    } catch (e) {
      alert(readError(e));
    } finally {
      setSaving(false);
    }
  };

  const del = async () => {
    await voidJournalTransaction(row.id);
    onSaved();
  };

  const inputCls = "w-full h-7 rounded border border-[#d8e0db] bg-white px-1.5 text-xs outline-none focus:border-[#35704c] focus:ring-1 focus:ring-[#dcebe1]";
  const cell = "px-1 py-1";

  if (!isEditing) {
    return (
      <tr className="border-b border-[#edf1ee] hover:bg-[#f8fbf9] cursor-pointer" onClick={() => { onEdit(); setConfirming(false); }}>
        <td className={cell}><span className="text-xs tabular-nums">{row.transaction_date}</span></td>
        <td className={cell}><span className="text-xs">{row.ledger_type === "cash" ? "现金" : "银行"}</span></td>
        <td className={cell}>
          <span className={`rounded-full px-1.5 py-0.5 text-xs ${row.direction === "income" ? "bg-[#eaf7ee] text-[#24703e]" : "bg-[#fff1ee] text-[#ae412e]"}`}>
            {row.direction === "income" ? "收入" : "支出"}
          </span>
        </td>
        <td className={cell}><span className="text-xs font-semibold tabular-nums">¥{row.amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</span></td>
        <td className={cell}><span className="text-xs">{row.payment_method || "-"}</span></td>
        <td className={`${cell} max-w-48 truncate`}><span className="text-xs">{row.summary || "-"}</span></td>
        <td className={cell}><span className="text-xs text-[#77837b]">{row.source_import_row_id ? "导入" : "手工"}</span></td>
        <td className={cell} onClick={(e) => e.stopPropagation()}>
          {confirming ? (
            <span className="inline-flex items-center gap-1">
              <span className="text-xs text-[#ba4935]">确认作废？</span>
              <button onClick={del} className="text-xs bg-[#f53f3f] text-white rounded px-1.5 py-0.5">确认</button>
              <button onClick={() => setConfirming(false)} className="text-xs text-[#86909c]">取消</button>
            </span>
          ) : (
            <button onClick={() => setConfirming(true)} className="text-xs text-[#ba4935] hover:underline">✕</button>
          )}
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-[#35704c] bg-[#f0faf3]">
      <td className={cell}><DatePicker value={f.transaction_date} onChange={(v) => setF({...f, transaction_date: v})} /></td>
      <td className={cell}>
        <select value={f.ledger_type} onChange={(e) => setF({...f, ledger_type: e.target.value as "cash"|"bank"})} className={inputCls}>
          <option value="cash">现金</option><option value="bank">银行</option>
        </select>
      </td>
      <td className={cell}>
        <select value={f.direction} onChange={(e) => setF({...f, direction: e.target.value as "income"|"expense"})} className={inputCls}>
          <option value="income">收入</option><option value="expense">支出</option>
        </select>
      </td>
      <td className={cell}><input type="number" step="0.01" value={f.amount} onChange={(e) => setF({...f, amount: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.payment_method} onChange={(e) => setF({...f, payment_method: e.target.value})} className={inputCls} /></td>
      <td className={cell}><input value={f.summary} onChange={(e) => setF({...f, summary: e.target.value})} className={inputCls} onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") onSaved(); }} /></td>
      <td className={cell}><span className="text-xs text-[#77837b]">{row.source_import_row_id ? "导入" : "手工"}</span></td>
      <td className={`${cell} whitespace-nowrap`}>
        <button onClick={save} disabled={saving} className="mr-1 text-xs text-[#216c40] hover:underline font-medium">保存</button>
        <button onClick={() => onSaved()} className="text-xs text-[#86909c] hover:underline">取消</button>
      </td>
    </tr>
  );
}

function JournalNewRowInline({ onSaved, onCancel }: { onSaved: () => void; onCancel: () => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const [f, setF] = useState({
    transaction_date: today, ledger_type: "cash" as "cash"|"bank",
    direction: "expense" as "income"|"expense",
    amount: "", payment_method: "", summary: "",
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const amt = Number(f.amount);
    if (!amt || amt <= 0) { alert("请输入有效金额"); return; }
    setSaving(true);
    try {
      await createJournalTransaction({
        transaction_date: f.transaction_date, ledger_type: f.ledger_type,
        direction: f.direction, category: "other", amount: amt,
        payment_method: f.payment_method || null, summary: f.summary || null,
      } as Omit<JournalTransaction, "id" | "status" | "source_import_row_id">);
      onSaved();
    } catch (e) { alert(readError(e)); }
    finally { setSaving(false); }
  };

  const inputCls = "w-full h-7 rounded border border-[#35704c] bg-white px-1.5 text-xs outline-none";
  const cell = "px-1 py-1";

  return (
    <tr className="border-b-2 border-[#173f2a] bg-[#f6fdf8]">
      <td className={cell}><DatePicker value={f.transaction_date} onChange={(v) => setF({...f, transaction_date: v})} /></td>
      <td className={cell}>
        <select value={f.ledger_type} onChange={(e) => setF({...f, ledger_type: e.target.value as "cash"|"bank"})} className={inputCls}>
          <option value="cash">现金</option><option value="bank">银行</option></select></td>
      <td className={cell}>
        <select value={f.direction} onChange={(e) => setF({...f, direction: e.target.value as "income"|"expense"})} className={inputCls}>
          <option value="income">收入</option><option value="expense">支出</option></select></td>
      <td className={cell}><input type="number" step="0.01" value={f.amount} onChange={(e) => setF({...f, amount: e.target.value})} className={inputCls} placeholder="金额" onKeyDown={(e) => { if (e.key === "Enter") save(); }} /></td>
      <td className={cell}><input value={f.payment_method} onChange={(e) => setF({...f, payment_method: e.target.value})} className={inputCls} placeholder="方式" /></td>
      <td className={cell}><input value={f.summary} onChange={(e) => setF({...f, summary: e.target.value})} className={inputCls} placeholder="摘要" onKeyDown={(e) => { if (e.key === "Enter") save(); }} /></td>
      <td className={cell}><span className="text-xs text-[#77837b]">新增</span></td>
      <td className={`${cell} whitespace-nowrap`}>
        <button onClick={save} disabled={saving} className="mr-1 text-xs text-white bg-[#216c40] rounded px-1.5 py-0.5">保存</button>
        <button onClick={onCancel} className="text-xs text-[#86909c] hover:underline">取消</button>
      </td>
    </tr>
  );
}

// @ts-ignore - kept for reference, replaced by JournalRow inline editing
function _JournalEditor({
  row,
  onClose,
  onSave,
}: {
  row: JournalTransaction | null;
  onClose: () => void;
  onSave: (data: Partial<JournalTransaction>) => Promise<void>;
}) {
  const [form, setForm] = useState({
    transaction_date:
      row?.transaction_date || new Date().toISOString().slice(0, 10),
    ledger_type: row?.ledger_type || "cash",
    direction: row?.direction || "expense",
    category: row?.category || "other",
    amount: String(row?.amount || ""),
    payment_method: row?.payment_method || "",
    summary: row?.summary || "",
  });
  const [saving, setSaving] = useState(false);
  const update = (key: string, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4">
      <div className="w-full max-w-xl rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#e5eae7] px-5 py-4">
          <div>
            <div className="font-semibold">{row ? "编辑流水" : "新增流水"}</div>
            <div className="mt-0.5 text-xs text-[#7f8a83]">
              保存后直接进入正式日记账
            </div>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2">
          <JournalField label="日期">
            <DatePicker
              value={form.transaction_date}
              onChange={(v) => update("transaction_date", v)}
            />
          </JournalField>
          <JournalField label="金额">
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.amount}
              onChange={(event) => update("amount", event.target.value)}
              className="journal-input"
            />
          </JournalField>
          <JournalField label="账簿">
            <select
              value={form.ledger_type}
              onChange={(event) => update("ledger_type", event.target.value)}
              className="journal-input"
            >
              <option value="cash">现金日记账</option>
              <option value="bank">银行日记账</option>
            </select>
          </JournalField>
          <JournalField label="收支">
            <select
              value={form.direction}
              onChange={(event) => update("direction", event.target.value)}
              className="journal-input"
            >
              <option value="income">收入</option>
              <option value="expense">支出</option>
            </select>
          </JournalField>
          <JournalField label="类别">
            <input
              value={form.category}
              onChange={(event) => update("category", event.target.value)}
              className="journal-input"
            />
          </JournalField>
          <JournalField label="方式">
            <input
              value={form.payment_method}
              onChange={(event) => update("payment_method", event.target.value)}
              className="journal-input"
            />
          </JournalField>
          <div className="md:col-span-2">
            <JournalField label="摘要">
              <input
                value={form.summary}
                onChange={(event) => update("summary", event.target.value)}
                className="journal-input"
              />
            </JournalField>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-[#e5eae7] px-5 py-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={
              saving || !form.transaction_date || Number(form.amount) <= 0
            }
            className="bg-[#173f2a] hover:bg-[#0f3320]"
            onClick={async () => {
              setSaving(true);
              try {
                await onSave({
                  ...form,
                  amount: Number(form.amount),
                } as Partial<JournalTransaction>);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "保存中..." : "保存"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ApprovalsPage({ setError, reloadTrigger }: { setError: (v: string) => void; reloadTrigger: number }) {
  const [items, setItems] = useState<Array<{ id: number; module: string; label: string; ref_date: string; amount: number; status: string }>>([]);
  const load = useCallback(async () => {
    try { setItems((await listPendingApprovals()).items); } catch (e) { setError(readError(e)); }
  }, [setError]);
  useEffect(() => { load(); }, [load, reloadTrigger]);
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border bg-white">
      <div className="shrink-0 border-b bg-[#f8faf9] p-4 flex justify-between items-center">
        <div><b className="text-lg">审批中心</b><div className="mt-0.5 text-xs text-[#7d8881]">工资和返费需要财务审核 → 老板确认</div></div>
        <Badge variant="secondary">{items.length} 项待处理</Badge>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {!items.length ? (
          <EmptyState title="暂无待审批" description="所有工资和返费已确认完毕" />
        ) : (
          <table className="min-w-full table-fixed text-sm">
            <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
              <tr>{["事项","日期","金额","当前状态","操作"].map(x => <th key={x} className="px-3 py-2.5 text-left text-xs font-medium text-[#526058]">{x}</th>)}</tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={`${item.module}-${item.id}`} className="border-b border-[#edf1ee]">
                  <td className="px-3 py-2.5 text-xs font-medium">{item.label}</td>
                  <td className="px-3 py-2.5 text-xs">{item.ref_date}</td>
                  <td className="px-3 py-2.5 text-xs font-semibold">¥{item.amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-3 py-2.5 text-xs">{item.status === "finance_review" ? "待财务审核" : "待老板确认"}</td>
                  <td className="px-3 py-2.5 text-xs">
                    <button onClick={async () => { await approveFinanceRecord(item.module, item.id); await load(); }} className="text-[#216c40] hover:underline font-medium">
                      {item.status === "finance_review" ? "审核通过" : "确认"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="shrink-0 border-t bg-[#fafcfb] px-4 py-2.5 text-xs text-[#7d8881]">
        审批流程：员工录入 → 财务审核 → 老板确认 · 确认后自动生成日记账
      </div>
    </div>
  );
}

function AdvisorPage({ setError }: { setError: (v: string) => void }) {
  const [messages, setMessages] = useState<Array<{role: string; content: string}>>(() => {
    try { const s = localStorage.getItem("advisor_msgs"); return s ? JSON.parse(s) : []; } catch { return []; }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    localStorage.setItem("advisor_msgs", JSON.stringify(messages.slice(-20)));
  }, [messages]);

  const send = async (question?: string) => {
    const q = question || input;
    if (!q.trim() || loading) return;
    const updated = [...messages, {role: "user", content: q}];
    setMessages(updated);
    setInput("");
    setLoading(true);
    try {
      const resp = await askAdvisor(q, messages);
      setMessages([...updated, {role: "assistant", content: resp.answer}]);
    } catch (e) { setError(readError(e)); }
    finally { setLoading(false); }
  };

  const quickQs = ["本月经营概况","回款逾期情况","利润变化原因","核对差异说明","哪家企业回款最多"];

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#f3f6f4]">
      <div className="shrink-0 border-b bg-white px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#173f2a] text-white"><Bot className="h-5 w-5" /></div>
          <div>
            <b className="text-lg">AI 顾问</b>
            <div className="text-xs text-[#7d8881]">已连接全部业务数据 · 可直接提问</div>
          </div>
          {messages.length > 0 && (
            <Button variant="ghost" size="sm" onClick={() => { setMessages([]); localStorage.removeItem("advisor_msgs"); }}>
              <Trash2 className="mr-1 h-3.5 w-3.5" /> 清空对话
            </Button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {/* Chat messages */}
        {messages.length > 0 && (
          <div className="px-6 py-4 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                  msg.role === "user" ? "bg-[#173f2a] text-white" : "bg-white border border-[#dfe6e1] text-[#1f2b31] shadow-sm"
                }`}>
                  {msg.content.split('\n').map((line, j) => <p key={j} className={j > 0 ? "mt-2" : ""}>{line}</p>)}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-white border border-[#dfe6e1] px-4 py-3 text-sm text-[#86909c] shadow-sm flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> 小曼正在查看数据...
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="shrink-0 border-t bg-white px-6 py-2 flex gap-2 overflow-x-auto">
        {quickQs.map(q => (
          <button key={q} onClick={() => send(q)} disabled={loading}
            className="shrink-0 rounded-full border border-[#dce4df] px-3 py-1 text-xs text-[#526058] hover:bg-[#f0f4f1] hover:border-[#173f2a] transition">{q}</button>
        ))}
      </div>

      <div className="shrink-0 border-t bg-white px-6 py-3">
        <div className="flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") send(); }}
            placeholder="问任何经营相关问题..." disabled={loading}
            className="flex-1 h-10 rounded-lg border border-[#dce4df] px-4 text-sm outline-none focus:border-[#173f2a] disabled:bg-[#f5f5f5]" />
          <Button onClick={() => send()} disabled={loading || !input.trim()} className="bg-[#173f2a] hover:bg-[#0f3320] h-10">发送</Button>
        </div>
      </div>
    </div>
  );
}

function OverduePage({ setError, reloadTrigger }: { setError: (v: string) => void; reloadTrigger: number }) {
  const [result, setResult] = useState<Awaited<ReturnType<typeof getOverdueReceivables>> | null>(null);
  const load = useCallback(async () => {
    try { setResult(await getOverdueReceivables()); } catch (e) { setError(readError(e)); }
  }, [setError]);
  useEffect(() => { load(); }, [load, reloadTrigger]);
  const items = result?.items || [];
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border bg-white">
      <div className="shrink-0 border-b bg-[#f8faf9] p-4">
        <div className="flex justify-between items-center">
          <div><b className="text-lg">回款逾期跟进</b><div className="mt-0.5 text-xs text-[#7d8881]">按逾期天数排列，优先处理最紧急的</div></div>
          {result && <div className="flex gap-4"><div className="text-center"><div className="text-2xl font-bold text-[#b74734]">{result.total}</div><div className="text-xs text-[#7d8881]">逾期笔数</div></div><div className="text-center"><div className="text-2xl font-bold text-[#b74734]">¥{(result.total_remaining||0).toLocaleString("zh-CN",{maximumFractionDigits:0})}</div><div className="text-xs text-[#7d8881]">待回款金额</div></div></div>}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {!items.length ? (
          <EmptyState title="暂无逾期" description="所有回款均在期限内" />
        ) : (
          <table className="min-w-full table-fixed text-sm">
            <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
              <tr>{["企业","预计回款日","逾期天数","应收","已收","待回款","状态","备注"].map(x => <th key={x} className="px-2 py-2.5 text-left text-xs font-medium text-[#526058]">{x}</th>)}</tr>
            </thead>
            <tbody>
              {items.map(r => (
                <tr key={r.id} className="border-b border-[#edf1ee] hover:bg-[#f8fbf9]">
                  <td className="px-2 py-2 text-xs font-medium">{r.company_name}</td>
                  <td className="px-2 py-2 text-xs">{r.expected_date}</td>
                  <td className="px-2 py-2 text-xs"><span className={`rounded-full px-2 py-0.5 font-medium ${r.overdue_days > 30 ? "bg-[#fff0ed] text-[#b74734]" : "bg-[#fff8e6] text-[#b78320]"}`}>{r.overdue_days}天</span></td>
                  <td className="px-2 py-2 text-xs tabular-nums">¥{r.amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-2 py-2 text-xs tabular-nums text-[#216c40]">¥{r.received_amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-2 py-2 text-xs font-semibold tabular-nums text-[#b74734]">¥{r.remaining.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-2 py-2 text-xs">{r.status}</td>
                  <td className="px-2 py-2 text-xs text-[#86909c] max-w-40 truncate">{r.remark || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="shrink-0 border-t bg-[#fafcfb] px-4 py-2.5 text-xs text-[#7d8881]">逾期超30天标红，30天内标黄 · 数据实时更新</div>
    </div>
  );
}

function ReconciliationPage({ setError, reloadTrigger }: { setError: (v: string) => void; reloadTrigger: number }) {
  const today = new Date().toISOString().slice(0, 10);
  const yearStart = `${new Date().getFullYear()}-01-01`;
  const [result, setResult] = useState<Awaited<ReturnType<typeof getReconciliation>> | null>(null);
  const [dateFrom, setDateFrom] = useState(yearStart);
  const [dateTo, setDateTo] = useState(today);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setResult(await getReconciliation(dateFrom, dateTo)); } catch (e) { setError(readError(e)); }
    finally { setLoading(false); }
  }, [dateFrom, dateTo, setError]);

  useEffect(() => { load(); }, [load, reloadTrigger]);

  const items = result?.items || [];

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-[#dfe6e1] bg-white">
      <div className="shrink-0 border-b border-[#e8ede9] bg-[#f8faf9] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <b className="text-lg">核对中心</b>
            <div className="mt-0.5 text-xs text-[#7d8881]">日记账金额 vs 工资/返费/回款业务记录</div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <DatePicker value={dateFrom} onChange={setDateFrom} />
          <span className="text-sm text-[#86909c]">至</span>
          <DatePicker value={dateTo} onChange={setDateTo} />
          <Button variant="outline" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "核对"}
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {!result ? (
          <EmptyState title="点击核对" description="选择日期范围后点击「核对」按钮" />
        ) : result.ok ? (
          <EmptyState title="核对通过 ✓" description="所选范围内日记账与业务记录完全一致，没有差异" />
        ) : (
          <table className="min-w-full table-fixed border-collapse text-sm">
            <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
              <tr>
                {["类型","关联记录","日期","业务金额","日记账金额","差异","问题"].map(x => (
                  <th key={x} className="px-3 py-2.5 text-left text-xs font-medium text-[#526058]">{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} className="border-b border-[#edf1ee] hover:bg-[#f8fbf9]">
                  <td className="px-3 py-2.5 text-xs"><span className={`rounded-full px-2 py-0.5 ${item.source_type === "回款收入" ? "bg-[#eaf7ee] text-[#24703e]" : "bg-[#fff1ee] text-[#ae412e]"}`}>{item.source_type}</span></td>
                  <td className="px-3 py-2.5 text-xs font-medium">{item.source_label}</td>
                  <td className="px-3 py-2.5 text-xs">{item.ref_date}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums">¥{item.expected_amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums">¥{item.journal_amount.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className={`px-3 py-2.5 text-xs font-semibold tabular-nums ${Math.abs(item.difference) > 0.01 ? "text-[#b74734]" : "text-[#216c40]"}`}>
                    {item.difference > 0 ? `+¥${item.difference.toLocaleString("zh-CN",{minimumFractionDigits:2})}` : `-¥${Math.abs(item.difference).toLocaleString("zh-CN",{minimumFractionDigits:2})}`}
                  </td>
                  <td className="px-3 py-2.5 text-xs"><span className="rounded bg-[#fff0ed] px-1.5 py-0.5 text-[#b74734]">{item.issue}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="shrink-0 border-t border-[#e7ece9] bg-[#fafcfb] px-4 py-2.5 text-xs text-[#7d8881]">
        {result ? (result.ok ? "数据一致" : `共 ${result.total} 处差异需处理`) : "准备就绪"}
      </div>
    </div>
  );
}

function DatabaseProfitPage({
  onImport,
  setError,
  reloadTrigger,
}: {
  onImport: () => void;
  setError: (v: string) => void;
  reloadTrigger: number;
}) {
  const now = new Date();
  const [result, setResult] = useState<ProfitMonthlyResult | null>(null);
  const [fromYear, setFromYear] = useState(String(now.getFullYear()));
  const [fromMonth, setFromMonth] = useState("01");
  const [toYear, setToYear] = useState(String(now.getFullYear()));
  const [toMonth, setToMonth] = useState(String(now.getMonth() + 1).padStart(2, "0"));
  const [loading, setLoading] = useState(false);

  const dateFrom = `${fromYear}-${fromMonth}-01`;
  const dateTo = `${toYear}-${toMonth}-01`;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResult(await profitMonthly(dateFrom, dateTo));
    } catch (e) {
      setError(readError(e));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, setError]);

  useEffect(() => { load(); }, [load, reloadTrigger]);

  const summary = result?.summary;
  const rows = result?.rows || [];

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-[#dfe6e1] bg-white">
      {/* Header */}
      <div className="shrink-0 border-b border-[#e8ede9] bg-[#f8faf9] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <b className="text-lg">利润核算</b>
            <div className="mt-0.5 text-xs text-[#7d8881]">
              利润 = 日记账收入 - 日记账支出
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onImport}>
              <Upload className="mr-2 h-4 w-4" />
              导入 Excel
            </Button>
          </div>
        </div>

        {/* Date filter row */}
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="flex items-center gap-1">
            <select value={fromYear} onChange={(e) => setFromYear(e.target.value)} className="h-9 rounded-md border border-[#dbe2dd] bg-white px-2 text-sm">
              {["2024","2025","2026","2027"].map(y => <option key={y} value={y}>{y}年</option>)}
            </select>
            <select value={fromMonth} onChange={(e) => setFromMonth(e.target.value)} className="h-9 rounded-md border border-[#dbe2dd] bg-white px-2 text-sm">
              {Array.from({length:12},(_,i)=>String(i+1).padStart(2,"0")).map(m => <option key={m} value={m}>{m}月</option>)}
            </select>
          </div>
          <span className="text-sm text-[#86909c]">至</span>
          <div className="flex items-center gap-1">
            <select value={toYear} onChange={(e) => setToYear(e.target.value)} className="h-9 rounded-md border border-[#dbe2dd] bg-white px-2 text-sm">
              {["2024","2025","2026","2027"].map(y => <option key={y} value={y}>{y}年</option>)}
            </select>
            <select value={toMonth} onChange={(e) => setToMonth(e.target.value)} className="h-9 rounded-md border border-[#dbe2dd] bg-white px-2 text-sm">
              {Array.from({length:12},(_,i)=>String(i+1).padStart(2,"0")).map(m => <option key={m} value={m}>{m}月</option>)}
            </select>
          </div>
          <Button variant="outline" onClick={load} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "查询"}
          </Button>
        </div>

        {/* Summary cards */}
        {summary && (
          <div className="mt-3 grid grid-cols-3 gap-3">
            <ImportCountCard label="总收入" value={summary.total_income} tone="success" />
            <ImportCountCard label="总支出" value={summary.total_expense} tone="danger" />
            <ImportCountCard label="净利润" value={summary.net_profit} tone="neutral" />
          </div>
        )}
      </div>

      {/* Content area */}
      <div className="min-h-0 flex-1 overflow-auto">
        {!rows.length
          ? <EmptyState title="暂无利润数据" description="所选月份范围内没有已确认的收入和成本数据，请点击查询" />
          : <table className="min-w-full table-fixed border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-[#f5f7f6] shadow-[0_1px_0_#e2e7e4]">
                <tr>
                  {["月份","收入","支出","净利润"].map(x => <th key={x} className="px-3 py-2.5 text-left text-xs font-medium text-[#526058]">{x}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map(r => <tr key={r.month} className="border-b border-[#edf1ee] hover:bg-[#f8fbf9]">
                  <td className="px-3 py-2.5 text-xs font-medium">{r.month}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums text-[#216c40]">¥{r.income.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums text-[#b74734]">¥{r.expense.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                  <td className={`px-3 py-2.5 text-xs font-semibold tabular-nums ${r.net_profit>=0?"text-[#216c40]":"text-[#b74734]"}`}>¥{r.net_profit.toLocaleString("zh-CN",{minimumFractionDigits:2})}</td>
                </tr>)}
              </tbody>
            </table>
        }
      </div>

      {/* Footer */}
      <div className="shrink-0 border-t border-[#e7ece9] bg-[#fafcfb] px-4 py-2.5 text-xs text-[#7d8881]">
        {rows.length > 0
          ? `共 ${rows.length} 个月 · 净利润 = 收入 - 支出`
          : "设置月份范围后点击查询"}
      </div>
    </div>
  );
}

function JournalField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-[#657169]">
        {label}
      </span>
      {children}
    </label>
  );
}

function DatePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const now = new Date();
  const currentYear = now.getFullYear();
  const years = ["2024","2025","2026","2027","2028"];
  const months = Array.from({length:12},(_,i)=>String(i+1).padStart(2,"0"));
  const [y, m, d] = value ? value.split("-") : [String(currentYear), String(now.getMonth()+1).padStart(2,"0"), String(now.getDate()).padStart(2,"0")];
  const daysInMonth = new Date(Number(y), Number(m), 0).getDate();
  const days = Array.from({length:daysInMonth},(_,i)=>String(i+1).padStart(2,"0"));

  const emit = (ny: string, nm: string, nd: string) => {
    const maxDay = new Date(Number(ny), Number(nm), 0).getDate();
    const safeDay = Math.min(Number(nd), maxDay);
    onChange(`${ny}-${nm}-${String(safeDay).padStart(2,"0")}`);
  };

  return (
    <div className="flex items-center gap-0.5">
      <select value={y} onChange={e => emit(e.target.value, m, d)} className="h-7 rounded border border-[#d8e0db] bg-white px-1 text-xs">
        {years.map(yr => <option key={yr} value={yr}>{yr}</option>)}
      </select>
      <select value={m} onChange={e => emit(y, e.target.value, d)} className="h-7 rounded border border-[#d8e0db] bg-white px-1 text-xs">
        {months.map(mo => <option key={mo} value={mo}>{Number(mo)}</option>)}
      </select>
      <select value={d} onChange={e => emit(y, m, e.target.value)} className="h-7 rounded border border-[#d8e0db] bg-white px-1 text-xs">
        {days.map(da => <option key={da} value={da}>{Number(da)}</option>)}
      </select>
    </div>
  );
}

function ImportDrawer({
  initialCategory,
  busy,
  setBusy,
  setError,
  onClose,
  onJournalCommitted,
  onCompanyCommitted,
  onEmployeeCommitted,
  onPositionCommitted,
  onContractCommitted,
  onAttendanceCommitted,
  onCreated,
}: {
  initialCategory: string;
  busy: boolean;
  setBusy: (value: boolean) => void;
  setError: (value: string) => void;
  onClose: () => void;
  onJournalCommitted: () => void;
  onCompanyCommitted: () => void;
  onEmployeeCommitted: () => void;
  onPositionCommitted: () => void;
  onContractCommitted: () => void;
  onAttendanceCommitted: () => void;
  onCreated: (dataset: Dataset) => Promise<void>;
}) {
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [sheetName, setSheetName] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [category, setCategory] = useState(initialCategory || "finance");
  const [headerRow, setHeaderRow] = useState<number | "">("");
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [stagedBatch, setStagedBatch] = useState<StagedImportBatch | null>(
    null,
  );

  const chooseFile = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".xlsx,.xls";
    input.onchange = async (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setBusy(true);
      setError("");
      try {
        const uploaded = await uploadFile(file);
        const firstSheet =
          uploaded.sheets.find((sheet) => sheet.row_count > 0) ||
          uploaded.sheets[0];
        setUpload(uploaded);
        setSheetName(firstSheet?.name || "");
        setDatasetName(firstSheet?.name || stripExcelName(uploaded.filename));
        setPreview(null);
        setStagedBatch(null);
        setHeaderRow("");
      } catch (err) {
        setError(readError(err));
      } finally {
        setBusy(false);
      }
    };
    input.click();
  };

  const loadPreview = async () => {
    if (!upload || !sheetName) return;
    setBusy(true);
    setError("");
    try {
      const result = await previewDatasetSheet(
        upload.upload_id,
        sheetName,
        headerRow === "" ? undefined : Number(headerRow),
      );
      setPreview(result);
      setHeaderRow(result.header_row);
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!upload || !sheetName) return;
    setBusy(true);
    setError("");
    try {
      const created = await createDatasetFromSheet({
        upload_id: upload.upload_id,
        sheet_name: sheetName,
        name: datasetName || sheetName,
        header_row: headerRow === "" ? undefined : Number(headerRow),
        category,
      });
      await onCreated(created);
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const saveWorkbook = async () => {
    if (!upload) return;
    setBusy(true);
    setError("");
    try {
      const created = await createWorkbookDataset({
        upload_id: upload.upload_id,
        name: datasetName || stripExcelName(upload.filename),
        category,
      });
      await onCreated(created);
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const stageJournal = async () => {
    if (!upload || !sheetName) return;
    setBusy(true); setError("");
    try {
      const staged = await stageJournalImport({ upload_id: upload.upload_id, sheet_name: sheetName, header_row: headerRow === "" ? undefined : Number(headerRow) });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const stageWorkbookJournal = async () => {
    if (!upload) return;
    setBusy(true); setError("");
    try {
      const staged = await stageJournalWorkbook(upload.upload_id);
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const confirmJournal = async () => {
    if (!upload || !sheetName || !stagedBatch) return;
    setBusy(true);
    setError("");
    try {
      await commitStagedImport(stagedBatch.batch_id);
      onJournalCommitted();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const stageCompany = async () => {
    if (!upload || !sheetName) return;
    setBusy(true);
    setError("");
    try {
      const staged = await stageCompanyImport({
        upload_id: upload.upload_id,
        sheet_name: sheetName,
        header_row: headerRow === "" ? undefined : Number(headerRow),
      });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const confirmCompany = async () => {
    if (!stagedBatch) return;
    setBusy(true);
    setError("");
    try {
      await commitStagedCompanies(stagedBatch.batch_id);
      onCompanyCommitted();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const stageEmployee = async () => {
    if (!upload || !sheetName) return;
    setBusy(true);
    setError("");
    try {
      const staged = await stageEmployeeImport({
        upload_id: upload.upload_id,
        sheet_name: sheetName,
        header_row: headerRow === "" ? undefined : Number(headerRow),
      });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const confirmEmployee = async () => {
    if (!stagedBatch) return;
    setBusy(true);
    setError("");
    try {
      await commitStagedEmployees(stagedBatch.batch_id);
      onEmployeeCommitted();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const stagePosition = async () => {
    if (!upload || !sheetName) return;
    setBusy(true); setError("");
    try {
      const staged = await stagePositionImport({ upload_id: upload.upload_id, sheet_name: sheetName, header_row: headerRow === "" ? undefined : Number(headerRow) });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const confirmPosition = async () => {
    if (!stagedBatch) return;
    setBusy(true); setError("");
    try {
      await commitStagedPositions(stagedBatch.batch_id);
      onPositionCommitted();
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const stageContract = async () => {
    if (!upload || !sheetName) return;
    setBusy(true); setError("");
    try {
      const staged = await stageContractImport({ upload_id: upload.upload_id, sheet_name: sheetName, header_row: headerRow === "" ? undefined : Number(headerRow) });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const confirmContract = async () => {
    if (!stagedBatch) return;
    setBusy(true); setError("");
    try {
      await commitStagedContracts(stagedBatch.batch_id);
      onContractCommitted();
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const stageAttendance = async () => {
    if (!upload || !sheetName) return;
    setBusy(true); setError("");
    try {
      const staged = await stageAttendanceImport({ upload_id: upload.upload_id, sheet_name: sheetName, header_row: headerRow === "" ? undefined : Number(headerRow) });
      setStagedBatch(await getStagedImportBatch(staged.batch_id));
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  const confirmAttendance = async () => {
    if (!stagedBatch) return;
    setBusy(true); setError("");
    try {
      await commitStagedAttendance(stagedBatch.batch_id);
      onAttendanceCommitted();
    } catch (err) { setError(readError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/25">
      <aside className="flex h-full w-full max-w-5xl flex-col bg-white shadow-2xl">
        <div className="flex h-14 items-center justify-between border-b border-[#e5e6eb] px-5">
          <div>
            <div className="text-sm font-semibold">导入 Excel</div>
            <div className="text-xs text-[#86909c]">
              选择业务板块，预览后保存并打开。
            </div>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr]">
          <div className="border-r border-[#e5e6eb] bg-[#f7f8fa] p-4">
            <Button className="w-full" onClick={chooseFile} disabled={busy}>
              {busy ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              选择文件
            </Button>
            {upload && (
              <div className="mt-4 space-y-3">
                <div className="rounded border border-[#e5e6eb] bg-white p-3">
                  <div className="text-xs text-[#86909c]">文件</div>
                  <div className="mt-1 break-all text-sm">
                    {upload.filename}
                  </div>
                </div>
                <div className="text-xs font-medium text-[#86909c]">工作表</div>
                {upload.sheets.map((sheet) => (
                  <button
                    key={sheet.name}
                    onClick={() => {
                      setSheetName(sheet.name);
                      setDatasetName(sheet.name);
                      setPreview(null);
                      setStagedBatch(null);
                    }}
                    className={`w-full rounded border p-3 text-left text-sm ${
                      sheetName === sheet.name
                        ? "border-[#165dff] bg-[#e8f3ff]"
                        : "border-[#e5e6eb] bg-white hover:bg-[#f2f3f5]"
                    }`}
                  >
                    <div className="font-medium">{sheet.name}</div>
                    <div className="mt-1 text-xs text-[#86909c]">
                      {sheet.row_count} 行 / {sheet.column_count} 列
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col p-4">
            {!upload ? (
              <EmptyState
                title="先选择 Excel 文件"
                description="选择后可以预览，并保存到人员、企业、合同、财务等板块。"
              />
            ) : (
              <>
                <div className="grid shrink-0 gap-3 rounded border border-[#e5e6eb] bg-[#fbfcff] p-4 md:grid-cols-[1fr_170px_120px_auto_auto]">
                  <label>
                    <div className="text-xs text-[#86909c]">保存名称</div>
                    <input
                      value={datasetName}
                      onChange={(event) => setDatasetName(event.target.value)}
                      className="mt-1 h-9 w-full rounded border border-[#dcdfe6] px-3 text-sm outline-none focus:border-[#165dff]"
                    />
                  </label>
                  <label>
                    <div className="text-xs text-[#86909c]">保存到板块</div>
                    <select
                      value={category}
                      onChange={(event) => {
                        setCategory(event.target.value);
                        setStagedBatch(null);
                      }}
                      className="mt-1 h-9 w-full rounded border border-[#dcdfe6] bg-white px-2 text-sm"
                    >
                      {MODULES.map((module) => (
                        <option key={module.key} value={module.key}>
                          {module.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <div className="text-xs text-[#86909c]">表头行</div>
                    <input
                      type="number"
                      min={0}
                      value={headerRow}
                      onChange={(event) =>
                        setHeaderRow(
                          event.target.value === ""
                            ? ""
                            : Number(event.target.value),
                        )
                      }
                      placeholder="自动"
                      className="mt-1 h-9 w-full rounded border border-[#dcdfe6] px-3 text-sm outline-none focus:border-[#165dff]"
                    />
                  </label>
                  <Button
                    variant="outline"
                    className="self-end"
                    onClick={loadPreview}
                    disabled={busy}
                  >
                    预览
                  </Button>
                  {upload && upload.sheets.filter(s => s.row_count > 2).length > 1 && (
                    <Button
                      className="self-end bg-[#165dff] hover:bg-[#1452e0]"
                      onClick={category === "journal" ? stageWorkbookJournal : saveWorkbook}
                      disabled={busy}
                    >
                      {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileSpreadsheet className="mr-2 h-4 w-4" />}
                      整本导入
                    </Button>
                  )}
                  <Button
                    className="self-end"
                    onClick={
                      category === "journal"
                        ? stagedBatch
                          ? confirmJournal
                          : stageJournal
                        : category === "company"
                          ? stagedBatch
                            ? confirmCompany
                            : stageCompany
                          : category === "employee"
                            ? stagedBatch
                              ? confirmEmployee
                              : stageEmployee
                        : category === "position"
                            ? stagedBatch
                              ? confirmPosition
                              : stagePosition
                        : category === "contract"
                            ? stagedBatch
                              ? confirmContract
                              : stageContract
                        : category === "attendance"
                            ? stagedBatch
                              ? confirmAttendance
                              : stageAttendance
                            : save
                    }
                    disabled={
                      busy ||
                      !sheetName ||
                      Boolean(stagedBatch && stagedBatch.ready_rows === 0)
                    }
                  >
                    {busy ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : stagedBatch ? (
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                    ) : null}
                    {category === "journal" ||
                    category === "company" ||
                    category === "employee"
                      ? stagedBatch
                        ? "确认写入数据库"
                        : "整理并校验"
                      : "保存并打开"}
                  </Button>
                </div>

                <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded border border-[#e5e6eb]">
                  {stagedBatch ? (
                    <StagedImportPreview batch={stagedBatch} />
                  ) : preview ? (
                    <DataTable
                      columns={preview.columns}
                      rows={preview.rows}
                      readonly
                    />
                  ) : (
                    <EmptyState
                      title="点击预览查看表格"
                      description={
                        category === "journal"
                          ? "也可以直接点击“整理并校验”，系统会识别收入和支出并在写入数据库前让你确认。"
                          : "如果表头识别不对，填入表头所在行号后重新预览。行号从 0 开始。"
                      }
                    />
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

function StagedImportPreview({ batch }: { batch: StagedImportBatch }) {
  const rows = batch.rows || [];
  if (batch.module === "employee") {
    return (
      <div className="flex h-full min-h-0 flex-col bg-white">
        <div className="grid grid-cols-3 gap-3 border-b p-4">
          <ImportCountCard
            label="识别人员"
            value={batch.total_rows}
            tone="neutral"
          />
          <ImportCountCard
            label="可以写入"
            value={batch.ready_rows}
            tone="success"
          />
          <ImportCountCard
            label="需要处理"
            value={batch.blocked_rows}
            tone={batch.blocked_rows ? "danger" : "neutral"}
          />
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 bg-[#f4f7f5]">
              <tr>
                {[
                  "原始行",
                  "姓名",
                  "手机号",
                  "性别",
                  "企业 / 岗位",
                  "入职日期",
                  "校验结果",
                ].map((x) => (
                  <th key={x} className="px-3 py-2 text-left text-xs">
                    {x}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const d = row.normalized_data;
                return (
                  <tr key={row.id} className="border-t">
                    <td className="px-3 py-2 text-xs">{row.source_row}</td>
                    <td className="px-3 py-2 text-xs font-medium">
                      {String(d.name || "-")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {String(d.phone || "-")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {d.gender === "male"
                        ? "男"
                        : d.gender === "female"
                          ? "女"
                          : "未识别"}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {String(d.company_name || "-")} /{" "}
                      {String(d.position_name || "-")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {String(d.entry_date || "-")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {row.status === "blocked" ? (
                        <span className="text-[#b74734]">
                          {row.issues.map((x) => x.message).join("；")}
                        </span>
                      ) : (
                        <span className="text-[#216c40]">可写入</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
  if (batch.module === "company") {
    return (
      <div className="flex h-full min-h-0 flex-col bg-white">
        <div className="grid grid-cols-3 gap-3 border-b p-4">
          <ImportCountCard
            label="识别企业"
            value={batch.total_rows}
            tone="neutral"
          />
          <ImportCountCard
            label="可以写入"
            value={batch.ready_rows}
            tone="success"
          />
          <ImportCountCard
            label="重复/错误"
            value={batch.blocked_rows}
            tone={batch.blocked_rows ? "danger" : "neutral"}
          />
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="sticky top-0 bg-[#f4f7f5]">
              <tr>
                {[
                  "原始行",
                  "企业名称",
                  "联系人",
                  "电话",
                  "合作状态",
                  "结果",
                ].map((x) => (
                  <th key={x} className="px-3 py-2 text-left text-xs">
                    {x}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t">
                  <td className="px-3 py-2 text-xs">{row.source_row}</td>
                  <td className="px-3 py-2 text-xs font-medium">
                    {String(row.normalized_data.name || "-")}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {String(row.normalized_data.contact_person || "-")}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {String(row.normalized_data.contact_phone || "-")}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {String(row.normalized_data.cooperation_status || "-")}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {row.status === "blocked" ? "需处理" : "可写入"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
  return (
    <div className="flex h-full min-h-0 flex-col bg-[#f7faf8]">
      <div className="grid shrink-0 grid-cols-3 gap-3 border-b border-[#dfe8e2] p-4">
        <ImportCountCard
          label="识别明细"
          value={batch.total_rows}
          tone="neutral"
        />
        <ImportCountCard
          label="可以写入"
          value={batch.ready_rows}
          tone="success"
        />
        <ImportCountCard
          label="阻断问题"
          value={batch.blocked_rows}
          tone={batch.blocked_rows ? "danger" : "neutral"}
        />
      </div>
      <div className="min-h-0 flex-1 overflow-auto bg-white">
        <table className="min-w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-[#f4f7f5] shadow-[0_1px_0_#dfe8e2]">
            <tr>
              {[
                "原始行",
                "区域",
                "日期",
                "收支",
                "金额",
                "方式",
                "摘要",
                "状态",
              ].map((label) => (
                <th
                  key={label}
                  className="px-3 py-2.5 text-left text-xs font-medium text-[#526159]"
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const data = row.normalized_data;
              return (
                <tr
                  key={row.id}
                  className="border-b border-[#edf1ee] hover:bg-[#f8fbf9]"
                >
                  <td className="px-3 py-2.5 text-xs text-[#748078]">
                    {row.source_row}
                  </td>
                  <td className="px-3 py-2.5 text-xs">{row.source_region}</td>
                  <td className="px-3 py-2.5 text-xs tabular-nums">
                    {String(data.transaction_date || "-")}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    {data.direction === "income" ? "收入" : "支出"}
                  </td>
                  <td className="px-3 py-2.5 text-xs font-medium tabular-nums">
                    ¥ {String(data.amount || "0")}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    {String(data.payment_method || "-")}
                  </td>
                  <td
                    className="max-w-64 truncate px-3 py-2.5 text-xs"
                    title={String(data.summary || "")}
                  >
                    {String(data.summary || "-")}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    <span
                      className={`rounded-full px-2 py-1 ${row.status === "blocked" ? "bg-[#fff0ed] text-[#b83d29]" : "bg-[#eaf7ee] text-[#257243]"}`}
                    >
                      {row.status === "blocked" ? "需修正" : "可写入"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="shrink-0 border-t border-[#dfe8e2] bg-[#f7faf8] px-4 py-3 text-xs text-[#66736c]">
        点击“确认写入数据库”后，可导入记录将进入正式日记账；阻断记录不会写入。
      </div>
    </div>
  );
}

function ImportCountCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "neutral" | "success" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "border-[#cce8d4] bg-[#eef9f1] text-[#216b3a]"
      : tone === "danger"
        ? "border-[#ffd2ca] bg-[#fff3f0] text-[#ad402e]"
        : "border-[#dfe6e1] bg-white text-[#34443b]";
  return (
    <div className={`rounded-lg border px-4 py-3 ${toneClass}`}>
      <div className="text-xs opacity-70">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function QueryPanel({
  dataset,
  setError,
}: {
  dataset: Dataset;
  setError: (value: string) => void;
}) {
  const [filters, setFilters] = useState<DatasetFilter[]>([]);
  const [groupBy, setGroupBy] = useState("");
  const [sumField, setSumField] = useState("");
  const [result, setResult] = useState<DatasetQueryResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await queryDataset(dataset.dataset_id, {
        filters: filters.filter((item) => item.field && item.operator),
        group_by: groupBy ? [groupBy] : [],
        aggregations: sumField ? [{ field: sumField, type: "sum" }] : [],
        limit: 1000,
      });
      setResult(data);
    } catch (err) {
      setError(readError(err));
    } finally {
      setLoading(false);
    }
  };

  const updateFilter = (index: number, patch: Partial<DatasetFilter>) => {
    setFilters((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)),
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="rounded border border-[#e5e6eb] bg-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">多条件查询</div>
            <div className="mt-1 text-xs text-[#86909c]">
              按任意字段筛选、分组、求和。
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setFilters((prev) => [
                  ...prev,
                  {
                    field: dataset.columns[0]?.key || "",
                    operator: "contains",
                    value: "",
                  },
                ])
              }
            >
              添加条件
            </Button>
            <Button size="sm" onClick={run} disabled={loading}>
              {loading ? "查询中..." : "执行查询"}
            </Button>
          </div>
        </div>
        <div className="mt-3 space-y-2">
          {filters.map((filter, index) => (
            <div
              key={index}
              className="grid gap-2 rounded bg-[#f7f8fa] p-2 md:grid-cols-[1fr_140px_1fr_auto]"
            >
              <select
                value={filter.field}
                onChange={(event) =>
                  updateFilter(index, { field: event.target.value })
                }
                className="h-8 rounded border border-[#dcdfe6] bg-white px-2 text-sm"
              >
                {dataset.columns.map((column) => (
                  <option key={column.key} value={column.key}>
                    {column.label}
                  </option>
                ))}
              </select>
              <select
                value={filter.operator}
                onChange={(event) =>
                  updateFilter(index, { operator: event.target.value })
                }
                className="h-8 rounded border border-[#dcdfe6] bg-white px-2 text-sm"
              >
                {OPERATORS.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.label}
                  </option>
                ))}
              </select>
              <input
                value={
                  Array.isArray(filter.value)
                    ? filter.value.join(",")
                    : String(filter.value ?? "")
                }
                onChange={(event) =>
                  updateFilter(index, {
                    value:
                      filter.operator === "between"
                        ? event.target.value
                            .split(",")
                            .map((item) => item.trim())
                        : event.target.value,
                  })
                }
                placeholder={
                  filter.operator === "between" ? "起始值,结束值" : "查询值"
                }
                className="h-8 rounded border border-[#dcdfe6] bg-white px-2 text-sm outline-none"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  setFilters((prev) => prev.filter((_, idx) => idx !== index))
                }
              >
                移除
              </Button>
            </div>
          ))}
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label>
            <div className="text-xs text-[#86909c]">分组字段</div>
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value)}
              className="mt-1 h-8 w-full rounded border border-[#dcdfe6] bg-white px-2 text-sm"
            >
              <option value="">不分组</option>
              {dataset.columns.map((column) => (
                <option key={column.key} value={column.key}>
                  {column.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <div className="text-xs text-[#86909c]">求和字段</div>
            <select
              value={sumField}
              onChange={(event) => setSumField(event.target.value)}
              className="mt-1 h-8 w-full rounded border border-[#dcdfe6] bg-white px-2 text-sm"
            >
              <option value="">不求和</option>
              {dataset.columns.map((column) => (
                <option key={column.key} value={column.key}>
                  {column.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {result && (
        <div className="min-h-0 flex-1 overflow-hidden rounded border border-[#e5e6eb] bg-white">
          <div className="flex h-11 items-center justify-between border-b border-[#e5e6eb] px-4">
            <div className="text-sm font-medium">查询结果</div>
            <Badge variant="secondary">{result.total} 条</Badge>
          </div>
          <div className="h-[calc(100%-44px)] overflow-hidden">
            <DataTable columns={dataset.columns} rows={result.rows} readonly />
          </div>
        </div>
      )}
    </div>
  );
}

function DataTable({
  columns,
  rows,
  readonly,
  onEditRow,
  onDeleteRow,
}: {
  columns: DatasetColumn[];
  rows: Record<string, unknown>[];
  readonly?: boolean;
  onEditRow?: (row: Record<string, unknown>) => void;
  onDeleteRow?: (row: Record<string, unknown>) => void;
}) {
  const visibleColumns = columns.filter((column) => column.visible !== false);
  if (rows.length === 0)
    return <EmptyState title="暂无数据" description="当前没有可展示的记录。" />;
  return (
    <div className="h-full min-h-0 overflow-auto">
      <table className="min-w-full border-collapse text-sm">
        <thead className="sticky top-0 z-10 bg-[#f7f8fa] shadow-[0_1px_0_#e5e6eb]">
          <tr>
            <th className="w-14 px-3 py-2.5 text-left text-xs font-medium text-[#4e5969] whitespace-nowrap">
              序号
            </th>
            {visibleColumns.map((column) => (
              <th
                key={column.key}
                className="px-3 py-2.5 text-left text-xs font-medium text-[#4e5969] whitespace-nowrap"
              >
                {column.label}
              </th>
            ))}
            {!readonly && (
              <th className="sticky right-0 w-24 bg-[#f7f8fa] px-3 py-2.5 text-left text-xs font-medium text-[#4e5969] whitespace-nowrap">
                操作
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={String(row.id ?? index)}
              className="border-b border-[#f0f1f4] hover:bg-[#f7fbff]"
            >
              <td className="px-3 py-2.5 text-xs text-[#86909c] whitespace-nowrap">
                {String(row.id ?? index + 1)}
              </td>
              {visibleColumns.map((column) => (
                <td
                  key={column.key}
                  className="max-w-72 truncate px-3 py-2.5 text-xs whitespace-nowrap"
                  title={formatValue(row[column.key])}
                >
                  {formatValue(row[column.key])}
                </td>
              ))}
              {!readonly && (
                <td className="sticky right-0 bg-white px-3 py-2.5 text-xs whitespace-nowrap shadow-[-8px_0_14px_rgba(255,255,255,0.86)]">
                  <button
                    onClick={() => onEditRow?.(row)}
                    className="mr-3 text-[#165dff] hover:underline"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => onDeleteRow?.(row)}
                    className="text-[#f53f3f] hover:underline"
                  >
                    删除
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

type JournalSectionKey = "income" | "expense" | "summary";

type JournalSection = {
  key: JournalSectionKey;
  label: string;
  description: string;
  columns: DatasetColumn[];
  rows: Record<string, unknown>[];
};

function JournalDatasetTable({
  columns,
  rows,
  onEditRow,
  onDeleteRow,
}: {
  columns: DatasetColumn[];
  rows: Record<string, unknown>[];
  onEditRow: (row: Record<string, unknown>) => void;
  onDeleteRow: (row: Record<string, unknown>) => void;
}) {
  const [activeSection, setActiveSection] =
    useState<JournalSectionKey>("income");
  const sections = getJournalSections(columns, rows);

  if (!sections) {
    return (
      <DataTable
        columns={columns}
        rows={rows}
        onEditRow={onEditRow}
        onDeleteRow={onDeleteRow}
      />
    );
  }

  const active =
    sections.find((section) => section.key === activeSection) || sections[0];
  const icons = {
    income: ArrowDownLeft,
    expense: ArrowUpRight,
    summary: CalendarRange,
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#f7f8fa]">
      <div className="shrink-0 border-b border-[#e5e6eb] bg-white px-4 py-3">
        <div
          className="flex flex-wrap items-center gap-2"
          role="tablist"
          aria-label="日记账分类"
        >
          {sections.map((section) => {
            const Icon = icons[section.key];
            const selected = active.key === section.key;
            return (
              <button
                key={section.key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setActiveSection(section.key)}
                className={`flex min-h-10 items-center gap-2 rounded-lg border px-3.5 text-sm font-medium transition-colors ${
                  selected
                    ? section.key === "income"
                      ? "border-[#b7ebc6] bg-[#eefbf2] text-[#16763a]"
                      : section.key === "expense"
                        ? "border-[#ffd0c7] bg-[#fff4f1] text-[#b83b26]"
                        : "border-[#c9dcff] bg-[#f1f6ff] text-[#245fae]"
                    : "border-transparent bg-[#f5f6f7] text-[#4e5969] hover:border-[#dcdfe6] hover:bg-white"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{section.label}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${selected ? "bg-white/75" : "bg-white text-[#86909c]"}`}
                >
                  {section.rows.length}
                </span>
              </button>
            );
          })}
        </div>
        <div className="mt-2 text-xs text-[#86909c]">{active.description}</div>
      </div>
      <div className="min-h-0 flex-1 bg-white">
        <DataTable
          columns={active.columns}
          rows={active.rows}
          onEditRow={active.key === "summary" ? undefined : onEditRow}
          onDeleteRow={active.key === "summary" ? undefined : onDeleteRow}
          readonly={active.key === "summary"}
        />
      </div>
    </div>
  );
}

function getJournalSections(
  columns: DatasetColumn[],
  rows: Record<string, unknown>[],
): JournalSection[] | null {
  const incomeAmountIndexes = findColumnIndexes(columns, "收入金额");
  const expenseAmountIndexes = findColumnIndexes(columns, "支出金额");
  const monthIndex = columns.findIndex((column) => column.label === "月份");

  if (incomeAmountIndexes.length === 0 || expenseAmountIndexes.length === 0)
    return null;

  const incomeAmountIndex = incomeAmountIndexes[0];
  const expenseAmountIndex = expenseAmountIndexes[0];
  const incomeColumns = selectDetailColumns(columns, incomeAmountIndex, [
    "收入方式",
  ]);
  const expenseColumns = selectDetailColumns(columns, expenseAmountIndex, [
    "支出方式",
    "备注信息",
  ]);

  if (incomeColumns.length < 2 || expenseColumns.length < 2) return null;

  const summaryIndexes = [
    monthIndex,
    incomeAmountIndexes[1] ?? -1,
    expenseAmountIndexes[1] ?? -1,
  ].filter((index) => index >= 0);
  const summaryColumns = summaryIndexes.map((index) => columns[index]);

  return [
    {
      key: "income",
      label: "收入明细",
      description:
        "只显示收入区域中有实际内容的记录，原始行号和完整数据仍然保留。",
      columns: incomeColumns,
      rows: rows.filter((row) =>
        hasMeaningfulValue(
          row[
            incomeColumns.find((column) => column.label === "收入金额")?.key ||
              ""
          ],
        ),
      ),
    },
    {
      key: "expense",
      label: "支出明细",
      description: "工资、返费及其他支出集中展示，不再被收入区域的空白列干扰。",
      columns: expenseColumns,
      rows: rows.filter((row) =>
        hasMeaningfulValue(
          row[
            expenseColumns.find((column) => column.label === "支出金额")?.key ||
              ""
          ],
        ),
      ),
    },
    {
      key: "summary",
      label: "月度汇总",
      description: "汇总区仅用于查看和核对，不与逐笔收入、支出明细混排。",
      columns: summaryColumns,
      rows:
        summaryColumns.length === 0
          ? []
          : rows.filter((row) =>
              summaryColumns.some((column) =>
                hasMeaningfulValue(row[column.key]),
              ),
            ),
    },
  ];
}

function findColumnIndexes(columns: DatasetColumn[], label: string): number[] {
  return columns.reduce<number[]>((indexes, column, index) => {
    if (column.label === label) indexes.push(index);
    return indexes;
  }, []);
}

function selectDetailColumns(
  columns: DatasetColumn[],
  amountIndex: number,
  extraLabels: string[],
): DatasetColumn[] {
  const dateIndex = columns
    .slice(0, amountIndex)
    .findLastIndex((column) => column.label === "日期");
  const nextAmountIndex = columns.findIndex(
    (column, index) => index > amountIndex && /金额$/.test(column.label),
  );
  const endIndex = nextAmountIndex === -1 ? columns.length : nextAmountIndex;
  const allowedLabels = new Set([
    "日期",
    columns[amountIndex].label,
    "摘要说明",
    ...extraLabels,
  ]);

  return columns.filter((column, index) => {
    if (index === dateIndex || index === amountIndex) return true;
    return (
      index > amountIndex && index < endIndex && allowedLabels.has(column.label)
    );
  });
}

function hasMeaningfulValue(value: unknown): boolean {
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function RowEditor({
  dataset,
  row,
  onClose,
  onSave,
}: {
  dataset: Dataset;
  row: Record<string, unknown> | null;
  onClose: () => void;
  onSave: (data: Record<string, unknown>) => Promise<void>;
}) {
  const [form, setForm] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    dataset.columns.forEach((column) => {
      initial[column.key] = row?.[column.key] ?? "";
    });
    return initial;
  });
  const [saving, setSaving] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/25">
      <aside className="flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl">
        <div className="flex h-14 items-center justify-between border-b border-[#e5e6eb] px-5">
          <div>
            <div className="text-sm font-semibold">
              {row ? "编辑记录" : "新增记录"}
            </div>
            <div className="text-xs text-[#86909c]">{dataset.name}</div>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-5">
          <div className="grid gap-3 md:grid-cols-2">
            {dataset.columns.map((column) => (
              <label
                key={column.key}
                className="block rounded border border-[#e5e6eb] bg-white p-3"
              >
                <div className="text-xs text-[#86909c]">{column.label}</div>
                <input
                  value={String(form[column.key] ?? "")}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      [column.key]: event.target.value,
                    }))
                  }
                  className="mt-2 w-full bg-transparent text-sm outline-none"
                />
              </label>
            ))}
          </div>
        </div>
        <div className="flex h-14 justify-end gap-2 border-t border-[#e5e6eb] px-5 py-3">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave(form);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "保存中..." : "保存"}
          </Button>
        </div>
      </aside>
    </div>
  );
}

function ClearDialog({
  module,
  onClose,
  onCleared,
}: {
  module: string;
  onClose: () => void;
  onCleared: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const yearStart = `${new Date().getFullYear()}-01-01`;
  const [dateFrom, setDateFrom] = useState(yearStart);
  const [dateTo, setDateTo] = useState(today);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState<"input" | "confirm">("input");
  const moduleLabel = MODULES.find((m) => m.key === module)?.label || module;

  const handleClear = async () => {
    setBusy(true);
    setError("");
    try {
      await clearByDateRange({
        module,
        date_from: dateFrom,
        date_to: dateTo,
      });
      onCleared();
    } catch (e) {
      setError(readError(e));
      setStep("input");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4">
      <div className="w-full max-w-md rounded-xl bg-white">
        <div className="flex justify-between border-b p-4">
          <div>
            <b>清空数据 — {moduleLabel}</b>
            <div className="mt-1 text-xs text-[#7d8881]">
              选择日期范围，清除指定模块的数据
            </div>
          </div>
          <Button size="icon" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="space-y-3 p-5">
          <JournalField label="开始日期">
            <DatePicker value={dateFrom} onChange={(v) => { setDateFrom(v); setStep("input"); }} />
          </JournalField>
          <JournalField label="结束日期">
            <DatePicker value={dateTo} onChange={(v) => { setDateTo(v); setStep("input"); }} />
          </JournalField>
          {step === "confirm" && (
            <div className="rounded-lg border border-[#ffd2ca] bg-[#fff3f0] p-3 text-sm text-[#ad402e]">
              <div className="flex items-start gap-2">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="font-medium">确认清空</div>
                  <div className="mt-1 text-xs">
                    将清除「{moduleLabel}」中 {dateFrom} 至 {dateTo}{" "}
                    范围内的所有数据。此操作不可撤销！
                  </div>
                </div>
              </div>
            </div>
          )}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t p-4">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          {step === "input" ? (
            <Button
              className="bg-[#f53f3f] hover:bg-[#e03a3a] text-white"
              onClick={() => setStep("confirm")}
            >
              清空
            </Button>
          ) : (
            <Button
              className="bg-[#f53f3f] hover:bg-[#e03a3a] text-white"
              disabled={busy}
              onClick={handleClear}
            >
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              确认清空
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full min-h-64 items-center justify-center bg-white p-8 text-center">
      <div>
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded bg-[#f2f3f5] text-[#86909c]">
          <FileSpreadsheet className="h-5 w-5" />
        </div>
        <div className="mt-4 text-sm font-medium">{title}</div>
        <div className="mt-1 text-xs text-[#86909c]">{description}</div>
      </div>
    </div>
  );
}

function PaginationBar({
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (ps: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="shrink-0 border-t border-[#e7ece9] bg-[#fafcfb] px-4 py-2.5 flex items-center justify-between text-xs text-[#7d8881]">
      <span>共 {total} 条</span>
      <div className="flex items-center gap-2">
        <select value={pageSize} onChange={e => { onPageSizeChange(Number(e.target.value)); }}
          className="h-7 rounded border border-[#dbe2dd] bg-white px-2 text-xs">
          {[30,50,100].map(n => <option key={n} value={n}>{n}条/页</option>)}
        </select>
        <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}
          className="h-7 rounded border border-[#dbe2dd] bg-white px-2 text-xs disabled:opacity-40">上一页</button>
        <span className="tabular-nums">{page}/{totalPages}</span>
        <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}
          className="h-7 rounded border border-[#dbe2dd] bg-white px-2 text-xs disabled:opacity-40">下一页</button>
      </div>
    </div>
  );
}

function WelcomePanel({
  moduleKey,
  onImport,
}: {
  moduleKey: string;
  onImport: () => void;
}) {
  return (
    <div className="flex h-full items-center justify-center rounded border border-[#e5e6eb] bg-white">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded bg-[#e8f3ff] text-[#165dff]">
          <FileSpreadsheet className="h-6 w-6" />
        </div>
        <h2 className="mt-5 text-lg font-semibold">{moduleLabel(moduleKey)}</h2>
        <p className="mt-2 text-sm text-[#86909c]">
          这个板块还没有打开的数据集。可以直接导入
          Excel，保存后会显示在左侧对应板块下。
        </p>
        <Button className="mt-5" onClick={onImport}>
          <Upload className="mr-2 h-4 w-4" />
          导入 Excel
        </Button>
      </div>
    </div>
  );
}

function groupDatasets(
  items: DatasetIndexItem[],
): Record<string, DatasetIndexItem[]> {
  return items.reduce<Record<string, DatasetIndexItem[]>>((acc, item) => {
    let key = item.category || "other";
    if (key === "finance") key = "journal"; // 旧版"财务记录"已合并到日记账
    acc[key] = acc[key] || [];
    acc[key].push(item);
    return acc;
  }, {});
}

function moduleLabel(key?: string): string {
  const resolved = key === "finance" ? "journal" : (key || "other");
  return (
    MODULES.find((module) => module.key === resolved)?.label ||
    "其他表格"
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function stripExcelName(filename: string): string {
  return filename.replace(/\.(xlsx|xls)$/i, "");
}

function readError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
// keep references to unused legacy editors so they don't trigger TS errors
void FinanceEditorV2; void FinanceEditor; void _JournalEditor; void AttendanceEditor; void EmployeeEditor; void CompanyEditor; void PositionEditor; void ContractEditor; void ComingSoonPage;
