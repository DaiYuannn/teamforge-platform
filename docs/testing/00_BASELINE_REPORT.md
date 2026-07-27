# 00_BASELINE_REPORT - 第一次全量验收基线报告

> **历史快照：本文记录 2026-07-07 的第一次验收，不代表当前版本、当前测试数量或发布结论。当前验收以 v2.1 文档、代码和当次自动化测试结果为准。**

> 生成时间：2026-07-07
> 版本：v1.2.0-personalization
> Git 分支：main
> 最后提交：b63e5bd Initial commit for TeamForge Platform

---

## 1. 项目盘点

### 1.1 环境信息

| 项目 | 版本 |
|------|------|
| Python | 3.10.11 |
| Django | 5.0.6 |
| DRF | 3.15.1 |
| Node.js | v22.16.0 |
| Vite | 6.4.3 |
| PostgreSQL | 16 (Running) |
| pytest | 9.1.1 |

### 1.2 后端应用（16 个）

| 应用 | 模型 | URL 前缀 |
|------|------|----------|
| users | User, UserPreference | /api/v1/users/ |
| projects | Project, ProjectMember, ProjectStageLog | /api/v1/projects/ |
| competitions | Competition, CompetitionRecord | /api/v1/competitions/ |
| tasks | Task, TaskLog | /api/v1/tasks/ |
| members | Member (proxy) | /api/v1/members/ |
| finance | FinanceRecord | /api/v1/finance/ |
| files | FileAsset, FileVersion | /api/v1/files/ |
| imports | ImportRecord | /api/v1/imports/ |
| dashboard | (无模型，聚合视图) | /api/v1/dashboard/ |
| contributions | Contribution | /api/v1/contributions/ |
| sensitive | SensitiveData, SensitiveAccessRequest | /api/v1/sensitive/ |
| notifications | Notification | /api/v1/notifications/ |
| audit | OperationLog | /api/v1/audit/ |
| exports | (无模型，导出服务) | /api/v1/exports/ |
| intellectual_property | IPApplication | /api/v1/intellectual-property/ |
| integrations | IntegrationConfig, IntegrationLog | /api/v1/integrations/ |

### 1.3 前端页面（34 个视图）

- 登录页
- Dashboard（首页驾驶舱）
- 项目日历、项目甘特图
- 项目列表、项目详情、项目归档
- 比赛列表（含矩阵/漏斗视图）
- 任务列表
- 成员列表、成员详情、成员技能、我的/团队灵活工时
- 经费管理
- 文件管理
- 导入中心
- 知识产权列表/详情/表单/待办
- 操作日志
- 通知中心
- 贡献记录/待审核
- 敏感资料中心/我的资料/申请/待审批
- 集成配置、用户管理
- 公共展示页
- 个人设置、个人中心

### 1.4 测试资产

**基线状态**：项目无任何测试基础设施

已建立：
- `backend/pytest.ini` - pytest 配置
- `backend/config/settings/test.py` - 测试环境配置
- `backend/conftest.py` - 全局 fixtures
- `backend/tests/test_contracts.py` - 契约测试（23 项）
- `backend/tests/test_auth.py` - 认证测试（8 项）
- `backend/tests/test_api_smoke.py` - API 冒烟+权限测试（29 项）

### 1.5 Git 状态

- 分支：main
- 最后提交：b63e5bd (Initial commit)
- 工作区：有大量未提交修改（v1.0-v1.2 的变更）

---

## 2. 静态检查结果

| 检查项 | 结果 |
|--------|------|
| `python manage.py check` | 通过 (0 issues) |
| `python manage.py makemigrations --check --dry-run` | 通过 (No changes detected) |
| `python manage.py migrate` | 通过 (全部已应用) |
| `npx vue-tsc --noEmit` | 通过 |
| `npm run build` | 通过 |
| `python -m pytest` | 59 通过 / 2 失败 |

---

## 3. 后端测试结果

### 3.1 契约测试（23 项）

| 测试类 | 通过 | 失败 |
|--------|------|------|
| TestUserContract | 6/6 | 0 |
| TestFileContract | 8/8 | 0 |
| TestTaskContract | 2/4 | 2 |
| TestSensitiveContract | 6/6 | 0 |

失败项：
1. `test_task_has_priority` - Task 模型缺少 `priority` 字段 (P01)
2. `test_task_has_start_date` - Task 模型缺少 `start_date` 字段 (P01)

### 3.2 认证测试（8 项）- 全部通过

- JWT 登录/刷新/无效 token 拒绝
- 登录返回字段使用 `name`/`global_role`（非 `real_name`/`role`）

### 3.3 API 冒烟测试（29 项）- 全部通过

- 16 个模块 API 全部可访问
- 权限矩阵验证通过：
  - 普通成员不能访问用户管理 (403)
  - 普通成员不能访问操作日志 (403)
  - 普通成员不能访问集成配置 (403)
  - 老师可以访问操作日志 (200)
  - 管理员可以访问所有模块 (200)
  - 未认证全部被拦截 (401)
- 无 NaN/undefined 值

---

## 4. 浏览器验收结果

### 4.1 页面渲染验证

| 页面 | URL | 结果 |
|------|-----|------|
| Dashboard | /dashboard | 正常渲染 |
| 项目管理 | /projects | 正常渲染（项目列表+操作区） |
| 任务管理 | /tasks | 正常渲染（表格/看板+筛选） |
| 经费管理 | /finance | 正常渲染（汇总+明细） |

### 4.2 控制台问题

| 问题 | 严重度 | 来源 |
|------|--------|------|
| preload-browserView.js 加载失败 | P3 | 浏览器工具（非应用问题） |
| exportedColors 解构失败 | P3 | 依赖库（非应用代码） |
| DashboardView VNode key 为 NaN | P2 | 应用代码（需修复） |

### 4.3 权限验证

- 演示账号：admin@demo.com / admin123456 (sys_admin)
- 自动登录正常（localStorage token 持久化）
- 页面标题随路由正确切换

---

## 5. 已发现的 Bug 和问题清单

### P0（阻断性）
- 无

### P1（严重）
- P01-1: Task 模型缺少 `priority` 字段
- P01-2: Task 模型缺少 `start_date` 字段

### P2（中等）
- DashboardView 中 VNode key 为 NaN（控制台警告）
- 用户 store 中 `global_role || role` 回退到旧字段引用

### P3（轻微）
- `exportedColors` 依赖库警告（非应用代码）
- 无前端单元测试
- 无 E2E 测试
- Git 工作区有大量未提交变更

---

## 6. 契约合规性

| 契约 | 合规 | 说明 |
|------|------|------|
| 用户字段 name/global_role | ✅ | 不使用 real_name/role |
| 文件字段 level/level_display | ✅ | 不使用 permission |
| 通知筛选 category | ✅ | 不使用 notification_type |
| 操作日志筛选 operator/start_date/end_date | ✅ | |
| 敏感资料申请 sensitive_data/usage_scenario/is_download | ✅ | |
| 敏感资料审批 action/approval_opinion/expire_hours | ✅ | |
| 导入 field_mapping/error_rows/error_details | ✅ | |
| JWT 结构不变 | ✅ | |
| 经费全员公开 | ✅ | |
| 普通成员不能进入系统管理 | ✅ | |
| 权限由后端执行 | ✅ | |

---

## 7. 基线结论

当前版本 v1.2.0-personalization 基础功能完整，16 个后端模块和 34 个前端页面可用。后端契约合规，权限矩阵正确。主要缺口在测试基础设施（M01）和 Task 模型字段（P01）。进入阶段 1 修复和开发。
