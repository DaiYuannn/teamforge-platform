# 版本说明

> 当前版本：**v1.2.0-personalization**
> 发布日期：2026-07-07
> 版本类型：正式版（v1.1 移动端+群机器人+P3美化 + v1.2 报告导出+个人化配置+需求A-K 全部完成）

---

## 版本摘要

v1.2.0 在 v1.0.0 基础上完成 v1.1（移动端深度优化、Celery 验证、群机器人推送、P3 美化）和 v1.2（Word/PDF 报告导出增强、账户级个人化配置、需求 A-K）全部功能。系统功能完整度达到生产可用标准。

### v1.1 新增功能
- **Celery 定时提醒验证通过**：7 个定时任务同步执行验证通过（任务延期/负责人更新/灵活工时/IP退回/IP异议/贡献审核/敏感审批）
- **群机器人推送**：企业微信 Provider + 通用 Webhook Provider + BotPushService 统一推送服务，集成配置页新增"测试推送"按钮
- **移动端深度优化**：FAB 浮动操作按钮、智能跳转、任务看板横向滑动、移动端底部导航栏、列表页卡片视图
- **P3 美化**：空状态 SVG 插图、表格高级搜索+筛选标签、ECharts 统一配色+渐变+loading

### v1.2 新增功能
- **Word 报告导出**：项目完整报告（基本信息+阶段历程+比赛+经费+成员+知识产权+贡献），python-docx 降级兼容
- **账户级个人化配置**：主题色选择、默认着陆页、每页条数、侧边栏折叠、通知声音（UserPreference 模型+API+页面）
- **需求 A-K**：比赛级别颜色区分(C)、成员首字头像(D)、经费标签深底浅字(E)、贡献蓝概括绿详细(F)、个人中心跳转修复(G)、通知未读数实时更新(H)

### 验证结果
- `python manage.py check`：通过（0 issues）
- `makemigrations --check`：No changes detected
- `npx vue-tsc --noEmit`：通过
- `npm run build`：通过（11.85s）
- 权限安全回归：9/9 通过
- API 测试：15/15 通过

### P1 新增功能（已完成）
- **统一时间线聚合接口** (`/api/v1/dashboard/timeline/`):聚合项目阶段/任务/比赛/经费/文件/知识产权/贡献 7 类事件
- **项目详情时间线 Tab**:基于聚合接口,el-timeline 按日期分组展示,7 种事件颜色区分,支持类型筛选和日期范围
- **项目日历热力图** (`/dashboard/calendar`):ECharts calendar 展示全年事件密度,点击查看当天事件详情
- **项目 Gantt 历程条** (`/dashboard/gantt`):ECharts custom series 横向甘特图,里程碑标记,今日线
- **比赛矩阵视图**:项目×比赛级别交叉矩阵,单元格显示参赛数(获奖/晋级),汇总行
- **比赛晋级漏斗** (ECharts funnel):校赛→市赛→省赛→国赛晋级率,详细数据表格

### P2 新增功能（已完成）
- **成员成长时间线** (`/api/v1/members/growth-timeline/`):聚合贡献/项目参与/比赛/IP/任务完成,el-timeline 展示
- **成员个人主页完善**:贡献汇总卡片 + 成长时间线,5 种事件颜色区分
- **公共展示主页** (`/public`):无需认证,Hero 统计 + 获奖项目卡片网格 + 知识产权成果 + 核心成员展示
- **文件在线预览**:图片/PDF/视频/音频前端 Blob 预览,不支持的类型提示下载
- **项目复盘归档** (`/projects/archive`):已获奖/已结项项目检索,统计卡片,详情弹窗

### 安全审查
- 敏感资料全链路复核通过:Fernet 加密存储、脱敏显示、审批流程、限时查看(默认1小时)、操作日志(含IP)、权限三层控制、过期自动关闭

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
| 1 | Word/PDF 导出 | 基础模板可用,PDF 依赖 GTK 运行时 | 丰富报告模板,PDF 服务端渲染方案 |
| 2 | 飞书/企业微信/QQ 群集成 | 接口与配置管理已预留,未实际接入 | 完成第三方 OAuth 与消息推送 |
| 3 | 移动端深度优化 | 有响应式布局切换,部分页面待优化 | 关键页面移动端 UI 重构 |

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

- **v0.8-demo**:初始演示版(2026-07-01)
- **v0.8.1-stable**:稳定版(2026-07-02,P0/P1/P2 全部修复)
- **v0.8.3-p1p2-complete**:P1+P2 功能完成版(2026-07-07)
- **v1.0.0-production-ready**:正式版(2026-07-07,飞书移除+全面测试通过)
- **v1.1.0-mobile-bot**:移动端+群机器人+P3美化(2026-07-07)
- **v1.2.0-personalization**:当前版本(2026-07-07,报告导出+个人化配置+需求A-K)
- **v1.3**:下一版本,预计完成代码分割优化+性能调优+更多第三方集成
