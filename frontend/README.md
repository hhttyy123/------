# 劳务派遣经营管理系统前端

该目录包含劳务派遣经营管理系统的 React 前端。当前代码主要实现通用表格数据底座，后续按产品需求逐步接入人员、企业、财务、审批和预警模块。

## 当前能力

- Excel 上传、工作表选择和数据预览
- 数据集分类导航
- 表格浏览、搜索、新增、编辑和删除
- 多条件查询、分组和求和
- 数据集导出、重命名和删除

AI 顾问尚未接入。按照当前产品要求，未来 AI 只分析用户明确选中的数据，不参与导入映射，也不自动修改数据。

## 开发

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

默认通过 Vite 代理访问 `http://localhost:8000` 的后端 API。可设置 `VITE_API_PROXY_TARGET` 指向其他地址。

## 验证

```powershell
npm run build
npm run lint
```

产品范围以仓库根目录的 `README.md` 和 `docs/产品需求文档.md` 为准。
