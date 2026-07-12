# 00_BASELINE_BUGS - 基线 Bug 清单

> 生成时间：2026-07-07
> 来源：第一次全量自动化验收

## P0 - 阻断性 Bug

无

## P1 - 严重 Bug

| ID | 模块 | 描述 | 复现步骤 |
|----|------|------|----------|
| BUG-001 | tasks | Task 模型缺少 `priority` 字段，违反契约 | 运行 `test_task_has_priority` |
| BUG-002 | tasks | Task 模型缺少 `start_date` 字段，违反契约 | 运行 `test_task_has_start_date` |

## P2 - 中等 Bug

| ID | 模块 | 描述 | 复现步骤 |
|----|------|------|----------|
| BUG-003 | dashboard | DashboardView VNode key 为 NaN，控制台警告 | 打开 /dashboard，查看 Console |
| BUG-004 | stores/user | 用户 store 中 `global_role \|\| role` 回退到旧字段 | 检查 stores/user.ts 第 46/79 行 |

## P3 - 轻微 Bug

| ID | 模块 | 描述 |
|----|------|------|
| BUG-005 | 依赖 | exportedColors 解构失败（来自依赖库，非应用代码） |
| BUG-006 | 测试 | 无前端单元测试（Vitest 未配置） |
| BUG-007 | 测试 | 无 E2E 测试（Playwright 未配置） |
| BUG-008 | Git | 工作区有大量未提交变更 |

## 修复状态

| ID | 状态 | 修复时间 |
|----|------|----------|
| BUG-001 | 待修复 | - |
| BUG-002 | 待修复 | - |
| BUG-003 | 待修复 | - |
| BUG-004 | 待修复 | - |
