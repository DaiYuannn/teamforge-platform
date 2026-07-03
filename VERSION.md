# 版本说明

> 当前版本：**v0.8.1-stable**
> 发布日期：2026-07-02
> 版本类型：稳定版（P0/P1/P2 全部修复完成，可部署演示）

---

## 版本摘要

v0.8.1-stable 在 v0.8-demo 基础上完成全部 P0/P1/P2 字段对齐与显示修复，所有核心流程通过回归验证。

### P0 修复（关键流程）
- 敏感资料申请字段对齐（`sensitive_data` / `usage_scenario` / `is_download`）
- 敏感资料审批/驳回字段对齐（`action` / `approval_opinion` / `expire_hours`）
- 三个敏感资料入口（SensitiveCenterView / AccessRequestsView / PendingApproveView）全部验证通过

### P1 修复（字段对齐）
- Dashboard 字段对齐（`total_income` / `total_used` / `status_distribution` / `risk_alerts`）
- 项目阶段 `current_stage_display`，任务列表移除空 `priority` 列
- 成员列表/详情移除后端不返回字段（`student_id` / `project_count` / `task_count`）
- 文件 `level`(public/internal/sensitive) + `level_display`
- 通知筛选 `category`，操作日志筛选 `operator` / `start_date` / `end_date`
- 用户管理 `name` / `global_role` / `password_confirm`，`ROLE_MAP` 全枚举对齐
- 知识产权贡献者下拉 `name`，导入预览 `field_mapping` / `error_rows` / `error_details`

### P2 修复（显示与常量）
- 敏感资料显示 `title` / `data_type_display`，查看弹窗 `access_expires_at` 倒计时
- 常量映射补全（`NOTIFICATION_CATEGORY_MAP` / `AUDIT_ACTION_MAP` / `FINANCE_CATEGORY_MAP` / `TASK_STATUS_MAP`）
- 经费筛选字段对齐后端 `filterset_fields`
- 操作日志详情异步获取 `request_ip`
- 排序异议显示 `ranking_user_name`

---

## 关键验证结果

| 验证项 | 结果 |
|--------|------|
| `python manage.py check` | 通过 |
| `python manage.py makemigrations --check --dry-run` | 通过 |
| `python manage.py migrate` | 通过 |
| `npx vue-tsc --noEmit` | 通过 |
| `npm run build` | 通过（2499 modules） |
| 5 类账号登录 | 通过（admin / teacher / leader / approver / member） |
| 权限安全回归 | 通过（普通成员 403 拦截，敏感资料不泄露明文） |
| 敏感资料申请/审批/驳回 | 通过（3 个入口全部通过） |
| 经费公开 | 通过（普通成员可查看经费明细和票据） |
| 操作日志 | 通过（IP 详情显示，权限拦截正常） |
| Excel 导出 | 通过 |
| 核心演示链路 | 通过（完整走通） |

---

## 已完成模块（功能可用）

以下模块已通过功能验证与权限测试，可用于实际演示：

| 序号 | 模块 | 说明 |
|------|------|------|
| 1 | 登录与权限 | JWT 认证，6 种全局角色 + 项目级角色，RBAC 三层权限模型 |
| 2 | 首页 Dashboard | 任务/经费/风险/日历聚合，后端字段全部对齐 |
| 3 | 项目管理 | 项目全生命周期管理，16 阶段流转，负责人打卡，成员管理 |
| 4 | 比赛管理 | 比赛信息录入，关联项目，级别/状态管理 |
| 5 | 任务管理 | 任务创建/指派/流转，看板与列表视图，5 种状态 |
| 6 | 成员管理 | 成员列表/详情，`global_role_display`，技能标签，灵活工作时间 |
| 7 | 经费管理 | 预算/支出/票据管理，经费全员公开透明，筛选参数对齐后端 |
| 8 | 文件资料 | 项目文件上传/下载/分类管理，`level` 权限体系 |
| 9 | 贡献记录 | 贡献填写/审核/驳回，13 种贡献类型，权重管理 |
| 10 | 成员排序与异议 | 自动生成排名草案，异议初审/终审流程 |
| 11 | 知识产权申请与责任追踪 | 14 状态机，5 种角色分工，退回修改责任追踪，贡献同步 |
| 12 | 敏感资料审批 | Fernet 加密存储，脱敏展示，审批流程，限时查看，3 个入口全部对齐 |
| 13 | 通知中心 | 站内通知，7 种定时提醒任务，未读统计，`category` 筛选 |
| 14 | 操作日志 | 中间件自动记录，`operator`/`start_date`/`end_date` 筛选，详情含 IP |
| 15 | 导入导出 | 导入 `field_mapping`/`error_rows`，Excel 6 类导出 |
| 16 | 演示数据 | 一键生成完整演示数据（53 账号/10 项目/40 任务/5 IP 等） |

---

## 仍为基础版的模块

| 序号 | 模块 | 当前状态 | 后续方向 |
|------|------|----------|----------|
| 1 | Word/PDF 导出 | 基础模板可用，PDF 依赖 GTK 运行时 | 丰富报告模板，PDF 服务端渲染方案 |
| 2 | 飞书/企业微信/QQ 群集成 | 接口与配置管理已预留，未实际接入 | 完成第三方 OAuth 与消息推送 |
| 3 | 公共展示面板 | 未实现 | 面向外部访客的项目成果展示页 |
| 4 | 移动端深度优化 | 有响应式布局切换，部分页面待优化 | 关键页面移动端 UI 重构 |
| 5 | 文件在线预览 | 仅支持上传下载 | 图片/PDF/Office 在线预览 |
| 6 | 历史项目整理 | 未实现 | 归档项目分类、检索与成果展示 |

---

## 技术栈版本

| 组件 | 版本 |
|------|------|
| Python | 3.10+ |
| Django | 5.0 |
| Django REST Framework | 3.15 |
| Vue | 3.x |
| TypeScript | 5.x |
| Element Plus | 最新稳定版 |
| PostgreSQL | 14+ |
| Redis | 7+ |
| Celery | 5.x |

---

## 版本约定

- **v0.8-demo**：初始演示版（2026-07-01）
- **v0.8.1-stable**：当前版本，稳定版（2026-07-02，P0/P1/P2 全部修复）
- **v0.9**：下一版本，预计完成前端美化 + 移动端优化
- **v1.0**：正式版，预计完成第三方集成 + 公共展示面板
