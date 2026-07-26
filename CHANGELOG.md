# CHANGELOG

## v2.0.0 - 2026-07-26

### 团队工作台发布

- 时间线精确事件类型、中文标签、业务分类和多选过滤统一。
- 账户主色、默认页、分页、数据范围、布局、收藏和通知偏好按登录账号持久化并隔离。
- 票据 OCR 使用真实 Tesseract 识别并要求人工复核，限制异常图片和执行时间。
- 演示备份包含业务快照、附件和 SHA-256 清单，恢复前自动创建回滚包。
- 定时报表支持 XLSX、DOCX、PDF、执行记录、下载、通知和 Celery 调度。
- 实时通知使用 SSE、Redis 唤醒和数据库游标补发，账户切换清除旧连接与状态。
- 完整演示入口生成 60 个账号、24 个项目、120 个任务及可打开的文档和票据。
- 按产品范围撤下 2FA 运行入口；OAuth 仅保留未配置的集成预留。
- 新增 Playwright 桌面端与移动端核心工作流验收。

本版本的通过状态以 2026-07-26 实际执行的测试、迁移检查、依赖审计和浏览器验收为准。

### 发布验收结果

- 后端：`1258` 项 pytest 全部通过；Django 系统检查通过，迁移无漂移。
- 前端：`28` 个测试文件、`149` 项 Vitest 全部通过；ESLint、类型检查和生产构建通过。
- 端到端：Playwright 桌面端与移动端共 `8/8` 通过，两端均实际下载并校验了非空 ZIP 备份包。
- 依赖安全：最终依赖树 `npm audit` 为 `0 vulnerabilities`，生产依赖审计同样为零。
- 下载校验：外部浏览器下载包为 `4,627,958` 字节，SHA-256 与服务端原包完全一致，ZIP 完整性检查通过。

## 2026-07-08 实现记录（历史快照）

> 以下测试数量和 Stub 状态只记录当时情况，不是当前发布证明。

### 全量实现：P05-P20 + M03-M10 + N01-N62

#### 验收统计
- 后端测试: 1009 项全部通过
- 前端测试: 27 项全部通过
- vue-tsc 类型检查: 通过
- Django check: 0 issues
- Migration check: No changes detected
- 总计: 1036 项测试通过

#### P05-P20 修复与增强

| ID | 描述 | 测试数 |
|----|------|--------|
| P05 | 经费导出 CSV 支持新增 | - |
| P06 | 导入模块新增 ip_applications 类型 | - |
| P07 | 导出中心新增 CSV 格式 + members/competitions 类型 | - |
| P08 | PDF 报告（当时使用 WeasyPrint 降级，v2.0 已改为 ReportLab） | - |
| P09 | WebhookConfig 模型 + CRUD API | 14 |
| P10 | 7 个 Celery 定时任务验证 | 17 |
| P11 | 个人中心 MyProfileView 全面测试 | 11 |
| P12 | 偏好设置 UserPreferenceView 全面测试 | 12 |
| P13 | Project 新增 archived_at 字段 + 自动归档逻辑 | 10 |
| P14 | 项目/任务/经费 ViewSet 新增 ordering_fields | 15 |
| P15 | 通知中心新增 delete/clear_all/delete_read 动作 | 14 |
| P16 | 移动端 API 分页结构验证 | 13 |
| P17 | 公共门户新增公告和项目统计 | 9 |
| P18 | 操作日志新增筛选和 Excel 导出 | 12 |
| P19 | 版本管理 VERSION 文件 + SystemInfoView | 10 |
| P20 | 安全设置 X-Frame-Options/XSS Filter/CSP | 16 |

#### M03-M10 基础能力

| ID | 描述 | 测试数 |
|----|------|--------|
| M03 | 公告管理: Announcement 模型 + CRUD + pin + public | 24 |
| M04 | SSE 实时通知: StreamingHttpResponse + broadcast | 16 |
| M08 | 软删除: SoftDeleteMixin + 回收站 API (Project/Task/Finance) | 29 |
| M09 | 项目复盘: ProjectReview 模型 + submit/approve 流程 | 18 |
| M10 | 历史项目导入: history_projects 类型 + 模板 + 字段映射 | 16 |

#### N01-N12 任务与项目增强

| ID | 描述 | 测试数 |
|----|------|--------|
| N01 | 子任务 SubTask 模型 + CRUD + toggle | 11 |
| N03 | 任务依赖 TaskDependency + 循环依赖检测 | 10 |
| N04 | 任务评论 TaskComment + 多级回复 | 10 |
| N05 | 里程碑 Milestone + CRUD + toggle | 10 |
| N06 | 风险管理 ProjectRisk + Level/Status + resolve | 10 |
| N07 | 项目模板 ProjectTemplate + instantiate 动作 | 10 |
| N08 | 统一待办 UnifiedTodoView (任务+审批+贡献聚合) | 9 |

#### N13-N25 成员/比赛/经费/贡献

| ID | 描述 | 测试数 |
|----|------|--------|
| N13 | 成员统计: 任务完成率/项目数/贡献分 | 9 |
| N14 | 成员技能矩阵 MemberSkill | 10 |
| N15 | 成员工作量分析 | 7 |
| N16 | 成员成长记录 MemberGrowth | 11 |
| N17 | 比赛统计 | 8 |
| N18 | 比赛时间线 | 7 |
| N19 | 比赛对比 | 7 |
| N20 | 获奖记录追踪 CompetitionAward | 8 |
| N21 | 经费预警 (>80%/100%) | 9 |
| N22 | 经费趋势分析 | 7 |
| N23 | OCR 票据识别（当时为 Stub，v2.0 已替换为真实 OCR） | 10 |
| N24 | 贡献度统计 | 8 |
| N25 | 贡献度排行榜 | 8 |

#### N26-N33 协作与知识

| ID | 描述 | 测试数 |
|----|------|--------|
| N26 | 动态流 Activity Feed + log_activity | 25 |
| N27 | 讨论区 DiscussionTopic + DiscussionReply | 23 |
| N28 | 知识库 KnowledgeArticle + 搜索/标签 | 22 |
| N29 | 全文搜索增强 (知识库+讨论+search_type) | 14 |
| N31 | 文件哈希 SHA-256 + 查重 | 15 |
| N32 | 水印服务 Pillow + download_watermarked | 11 |
| N33 | 分享链接 FileShareLink + token 访问 | 25 |

#### N34-N39 安全与管理

| ID | 描述 | 测试数 |
|----|------|--------|
| N34 | 双因素认证（历史实现，v2.0 按产品范围撤下） | 13 |
| N35 | 登录安全 LoginAttempt + IPBlocklist (5次封禁) | 11 |
| N36 | 自定义角色 CustomRole + UserRoleAssignment | 13 |
| N37 | 敏感操作确认 SensitiveConfirmation + token | 9 |
| N38 | 备份恢复（当时为 Stub，v2.0 已替换） | 6 |
| N39 | 安全扫描 SecurityScanView (8项检查) | 9 |

#### N40-N47 平台化

| ID | 描述 | 测试数 |
|----|------|--------|
| N40 | 多团队 Team + TeamMember | 12 |
| N41 | 审批流 ApprovalFlow + ApprovalRequest | 13 |
| N42 | 自定义表单 CustomForm + FormSubmission | 10 |
| N43 | 第三方登录 OAuthAccount (stub) | 7 |
| N44 | 外部平台集成 ExternalPlatform | 7 |
| N45 | Git 集成 GitRepository | 7 |
| N46 | 日历同步 iCal 格式 | 7 |
| N47 | 开放 API Schema + 端点列表 | 5 |

#### N48-N55 数据分析与智能

| ID | 描述 | 测试数 |
|----|------|--------|
| N48 | 自定义看板 CustomDashboard + set_default | 14 |
| N49 | 自定义报表 CustomReport + generate 动作 | 15 |
| N50 | 定时报表 ScheduledReport + run_now | 12 |
| N51 | 风险预测 RiskPredictionView (0-100评分) | 11 |
| N52 | 健康度评分 ProjectHealthScoreView (A/B/C/D) | 12 |
| N53 | 智能周报 WeeklyReportView | 11 |
| N54 | 智能复盘 SmartReviewView | 13 |
| N55 | 材料检查 MaterialCheckView (6项检查) | 12 |

#### N56-N62 工程质量

| ID | 描述 | 测试数 |
|----|------|--------|
| N56 | CI 配置 .github/workflows/ci.yml | 10 |
| N57 | 错误监控 ErrorLog + API | 13 |
| N58 | 健康检查 HealthCheckView (DB/Cache/Celery) | 12 |
| N59 | 性能监控 PerformanceMetricsView | 11 |
| N60 | OpenAPI Schema + 端点列表 | 10 |
| N61 | 无障碍报告 AccessibilityReportView | 8 |
| N62 | 国际化/主题 TranslationView + ThemeView | 9 |

#### 前端测试基础设施
- Vitest + @vue/test-utils + jsdom 配置
- 27 项前端单元测试 (格式化工具 + 用户 Store)
- ESLint flat 配置 + lint 脚本

#### 新增模型清单 (40+)
ProjectReview, Announcement, SoftDeleteMixin(Project/Task/FinanceExpense), SubTask, TaskDependency, TaskComment, Milestone, ProjectRisk, ProjectTemplate, FileTag, FileTagRelation, FileShareLink, DiscussionTopic, DiscussionReply, KnowledgeArticle, Activity, MemberSkill, MemberGrowth, CompetitionAward, CustomRole, UserRoleAssignment, TwoFactorSecret, LoginAttempt, IPBlocklist, SensitiveConfirmation, Team, TeamMember, ApprovalFlow, ApprovalRequest, CustomForm, FormSubmission, OAuthAccount, ExternalPlatform, GitRepository, CustomDashboard, CustomReport, ScheduledReport, ErrorLog, WebhookConfig

#### 新增 API 端点 (60+)
- 公告管理 /api/v1/notifications/announcements/
- SSE 通知 /api/v1/notifications/sse/
- 回收站 /api/v1/recycle-bin/
- 项目复盘 /api/v1/projects/reviews/
- 子任务 /api/v1/tasks/subtasks/
- 任务依赖 /api/v1/tasks/dependencies/
- 任务评论 /api/v1/tasks/comments/
- 里程碑 /api/v1/projects/milestones/
- 风险管理 /api/v1/projects/risks/
- 项目模板 /api/v1/projects/templates/
- 统一待办 /api/v1/todo/
- 文件标签 /api/v1/files/tags/
- 文件分享 /api/v1/files/shares/
- 讨论区 /api/v1/projects/discussions/
- 知识库 /api/v1/projects/knowledge/
- 动态流 /api/v1/activities/
- 成员技能 /api/v1/users/skills/
- 成长记录 /api/v1/users/growth/
- 成员统计 /api/v1/users/statistics/
- 成员工作量 /api/v1/users/workload/
- 比赛统计 /api/v1/competitions/statistics/
- 比赛时间线 /api/v1/competitions/timeline/
- 比赛对比 /api/v1/competitions/comparison/
- 经费预警 /api/v1/finance/alerts/
- 经费趋势 /api/v1/finance/trends/
- OCR 识别 /api/v1/finance/ocr/recognize/
- 贡献度统计 /api/v1/contributions/statistics/
- 贡献度排行 /api/v1/contributions/leaderboard/
- 双因素认证 `/api/v1/users/2fa/`（历史端点，v2.0 已撤下）
- 登录安全 /api/v1/users/login-security/
- 自定义角色 /api/v1/users/roles/
- 敏感确认 /api/v1/common/confirmations/
- 备份恢复 /api/v1/common/backup/
- 安全扫描 /api/v1/common/security-scan/
- 多团队 /api/v1/common/teams/
- 审批流 /api/v1/common/approvals/
- 自定义表单 /api/v1/common/forms/
- 日历同步 /api/v1/common/calendar/
- 开放API /api/v1/common/openapi/
- 自定义看板 /api/v1/dashboard/custom/
- 自定义报表 /api/v1/exports/custom-reports/
- 定时报表 /api/v1/exports/scheduled-reports/
- 风险预测 /api/v1/projects/risk-prediction/
- 健康度 /api/v1/projects/health-score/
- 智能周报 /api/v1/dashboard/weekly-report/
- 智能复盘 /api/v1/projects/smart-review/
- 材料检查 /api/v1/projects/material-check/
- 健康检查 /api/v1/common/health/
- 错误监控 /api/v1/common/error-logs/
- 性能监控 /api/v1/common/performance/
- 无障碍 /api/v1/common/accessibility/
- 国际化/主题 /api/v1/common/i18n/
- Webhook /api/v1/integrations/webhooks/
- 外部平台 /api/v1/integrations/external-platforms/
- Git集成 /api/v1/integrations/git-repositories/
- 系统信息 /api/v1/dashboard/system-info/

## v1.4.0-acceptance - 2026-07-07

### M06: 头像上传闭环
- 新增 `UploadAvatarView`: 头像上传 API
- 支持 JPG/PNG/GIF/WebP 格式，最大 5MB
- 自动删除旧头像文件
- 前端 UserProfileView 新增头像上传按钮
- 前端 API 层新增 `uploadAvatar` 函数
- 5 项后端测试验证

### M07: 全局搜索
- 新增 `GlobalSearchView`: 跨模块搜索 API
- 搜索范围: 项目、任务、成员、文件、比赛
- 支持关键词模糊匹配，结果分类展示
- 前端 PCLayout 顶部栏新增搜索输入框
- 搜索结果弹窗展示，支持点击跳转
- 9 项后端测试验证

### 前端任务列表增强
- TaskListView 新增优先级列和优先级筛选器
- TaskQueryParams 类型新增 priority 字段

## v1.3.0-acceptance - 2026-07-07

### 全量验收与修复

#### 阶段 0：基线验收
- 建立完整后端测试体系: pytest + pytest-django + factory-boy + coverage
- 建立完整前端测试体系: Vitest + @vue/test-utils + jsdom
- 创建 `backend/conftest.py`: 全局 fixtures (6 种角色客户端、项目/任务/经费/文件/敏感数据工厂)
- 创建 `backend/config/settings/test.py`: 独立测试数据库 + Celery 同步 + MD5 哈希加速
- 创建 `frontend/vitest.config.ts`: Vitest 配置
- 生成基线报告: `docs/testing/00_BASELINE_REPORT.md`
- 生成基线 Bug 清单: `docs/testing/00_BASELINE_BUGS.md`
- 生成实现待办: `docs/testing/00_IMPLEMENTATION_BACKLOG.md`

#### P01：任务字段统一
- Task 模型新增 `priority` 字段 (low/medium/high/urgent)
- Task 模型新增 `start_date` 字段
- TaskSerializer/TaskListSerializer/TaskCreateSerializer 更新
- TaskViewSet 筛选和排序字段更新
- 前端 TaskFormDialog 修复 `due_date` → `deadline` 契约违规
- 前端类型定义移除 `due_date` 旧字段
- 10 项 API 测试验证

#### P02：文件字段统一
- 重命名 `FILE_PERMISSION_MAP` → `FILE_LEVEL_MAP`
- FileListView 修复 `file_type` → `content_type`, `file_size` → `size`, `permission` → `level`
- FileUploader 组件修复 `FilePermission` → `FileLevel`
- 类型定义移除 `file_type`, `file_size` 旧字段
- ProjectDetailView 修复文件级别字段引用

#### P03：敏感资料审批契约修复
- SensitiveAccessRequestCreateSerializer: `reason` 不再必填，从 `usage_scenario` 自动填充
- SensitiveAccessRequestReviewSerializer: reject 时 `expire_hours` 允许 0
- 16 项敏感资料和经费 API 测试验证

#### P04/P05：经费 CRUD 和导出验证
- 经费列表对所有登录成员公开 (验证通过)
- 经费 CRUD 全流程测试 (创建/查看/更新/删除/筛选)
- 经费金额无 NaN 验证
- 经费导出接口验证

#### M01：完整自动化测试体系
- 后端: 93 项测试 (契约 23 + 认证 8 + API 冒烟 30 + 任务 10 + 经费 8 + 敏感资料 8 + 密码 6)
- 前端: 27 项测试 (格式化工具 24 + 用户 Store 3)
- 覆盖: 6 种角色权限矩阵、16 个模块 API、NaN 检测

#### M05：密码与账号安全
- 新增 `ChangePasswordView`: 修改密码 API
- 旧密码验证 + 新密码确认 + Django 密码强度验证
- 新密码不能与旧密码相同
- 修改密码记录操作日志
- JWT 结构不变 (修改后建议重新登录)
- 前端 PreferenceView 新增安全设置卡片
- 6 项后端测试验证

#### 其他修复
- BUG-003: DashboardView v-for key 为 NaN → 添加索引回退
- BUG-004: 用户 store `global_role || role` 旧字段引用 → 仅使用 `global_role`
- BUG-004: 用户类型移除 `real_name` 和 `role` 旧字段
- UserProfileView 移除 `real_name` 表单字段

### 测试统计
- 后端测试: 93 项全部通过
- 前端测试: 27 项全部通过
- vue-tsc 类型检查: 通过
- manage.py check: 通过
- makemigrations --check: 通过

## v1.2.0-personalization - 2026-07-07

### v1.1 新增功能

#### 后端
- 验证 Celery 定时提醒:7 个任务同步执行全部通过(任务延期/负责人更新/灵活工时/IP退回/IP异议/贡献审核/敏感审批)
- 新增 `integrations/services/wecom.py`:企业微信机器人 Provider(Markdown 消息+Webhook 发送)
- 新增 `integrations/services/webhook.py`:通用 Webhook Provider(自定义 headers+JSON 格式)
- 新增 `integrations/services/bot_push.py`:BotPushService 统一推送服务(任务延期/贡献审核/比赛节点/敏感审批+自定义消息)
- 修改 `notifications/tasks.py`:任务延期提醒自动推送群机器人
- 新增 `integrations/bot-push/test/`:群机器人推送测试 API
- 新增 `users/models.py` UserPreference 模型(主题色/着陆页/侧边栏/通知声音/每页条数)
- 新增 `users/preference_views.py`:个人偏好 GET/PUT API
- 新增 `exports/report_templates.py`:项目完整报告生成(python-docx 降级兼容)
- 新增 `exports/report_views.py`:项目报告下载 API

#### 前端
- 新增 `MobileFab.vue`:移动端浮动操作按钮(新建任务/项目/扫一扫/返回顶部)
- 新增 `useMobileNavigate.ts`:移动端智能跳转(push/新窗口/返回)
- 新增 `useMobileList.ts`:移动端列表卡片视图 composable
- 修改 `TaskBoard.vue`:移动端横向滑动卡片+状态切换按钮
- 修改 `MobileLayout.vue`:引入 FAB+底部 padding
- 修改 `ProjectListView.vue`+`MemberListView.vue`:移动端卡片视图+高级搜索+筛选标签
- 增强 `EmptyState.vue`:SVG 插图+自定义主题色+紧凑模式
- 修改 `DashboardView.vue`:ECharts 统一配色+渐变+loading 动画
- 新增 `AvatarWithName.vue`:成员首字彩色头像(12 色 hash)
- 新增 `PreferenceView.vue`:个人设置页面(主题色/着陆页/条数/声音/侧栏)
- 新增 `UserProfileView.vue`:个人中心页面
- 修改 `FinanceTable.vue`:经费标签深底浅字+货币符号
- 修改贡献记录页面:蓝色概括+绿色详细+紫色权重
- 修复 `PCLayout.vue` 个人中心跳转
- 增强 `NotificationBell.vue`:展开时同步刷新未读数
- 新增 `constants.ts` STAGE_COLOR_MAP/STAGE_HEX_COLOR_MAP
- 新增 `format.ts` 比赛级别颜色工具函数
- 新增路由: `user/preference`, `user/profile`
- 修改 `IntegrationConfigView.vue`:新增"测试群机器人推送"按钮

### v1.2 新增功能
- **Word 报告导出**:项目完整报告(7 章节),python-docx 降级为纯文本
- **账户级个人化配置**:UserPreference 模型+API+前端页面
- **需求 C**:比赛级别颜色区分(校赛蓝/市赛绿/省赛橙/国赛红/国际赛紫)
- **需求 D**:成员首字彩色头像
- **需求 E**:经费标签深底浅字+货币符号
- **需求 F**:贡献记录蓝色概括+绿色详细+紫色权重
- **需求 G**:个人中心跳转修复
- **需求 H**:通知未读数实时更新

### 数据库迁移
- `users/0002_user_preference`:UserPreference 模型

### 验证结果
- `python manage.py check`:通过
- `makemigrations --check`:No changes detected
- `npx vue-tsc --noEmit`:通过
- `npm run build`:通过(11.85s)
- 权限安全回归:9/9 通过
- API 测试:15/15 通过
- 浏览器 UI 测试:11/11 页面通过(登录/Dashboard/日历/Gantt/比赛列表+矩阵+漏斗/项目列表+详情/成员列表+详情/文件管理/项目归档/公共展示/集成配置)
- 移动端 375px 测试:通过(移动端布局,无 PC 侧栏)

---

## v1.0.0-production-ready - 2026-07-07

### 变更内容
- 移除飞书(Feishu)和QQ机器人(QQBot)集成相关代码
  - 删除 `backend/apps/integrations/services/feishu.py`
  - 删除 `backend/apps/integrations/services/qqbot.py`
  - 模型 Provider 枚举清理:移除 FEISHU 和 QQBOT 选项
  - 前端常量 `INTEGRATION_PROVIDER_MAP` 同步清理
  - 集成配置页面副标题更新
  - 创建并应用数据库迁移 `remove_feishu_qqbot_providers`
- 保留通知渠道:企业微信、通用 Webhook、邮件
- 群机器人推送功能预留(后期实现)

### 全面测试验证
- 后端 API 测试:8/8 通过
  - 时间线聚合接口:200 个事件,14 种事件类型
  - 比赛矩阵:6 个项目 × 4 个级别
  - 比赛漏斗:校赛→市赛→省赛→国赛晋级率
  - 项目日历:52 个有事件的日期
  - Gantt 历程:6 个项目,含阶段和里程碑
  - 公共展示:无需认证,统计数据完整
  - 成员成长时间线:贡献/项目/比赛/IP/任务聚合
  - 飞书/QQ机器人移除验证:Providers 仅剩 wecom/webhook/email
- 前端代理 API 测试:7/7 通过
- `vue-tsc --noEmit`:通过
- `npm run build`:通过(13.02s)
- `python manage.py check`:通过(0 issues)
- `makemigrations --check --dry-run`:No changes detected

### 代码审查
- 所有 P1+P2 新增代码字段引用与模型定义完全匹配
- 时间线聚合:7 类事件(阶段/任务/比赛/经费/文件/IP/贡献)字段正确
- 成长时间线:5 类事件(贡献/项目参与/比赛/IP贡献/任务完成)字段正确
- 公共展示:统计数据、获奖项目、IP成果、核心成员字段正确
- 敏感资料安全:加密存储、脱敏显示、审批流程、限时查看、操作日志全链路完整

---

## v0.8.3-p1p2-complete - 2026-07-07

### P1 新增功能

#### 后端
- 新增 `dashboard/timeline_views.py`:统一时间线聚合接口,聚合 7 类事件(项目阶段/任务/比赛/经费/文件/知识产权/贡献)
- 新增 `dashboard/competition-matrix/`:比赛矩阵数据接口(项目×级别交叉)
- 新增 `dashboard/competition-funnel/`:比赛晋级漏斗接口(校赛→市赛→省赛→国赛)
- 新增 `dashboard/calendar/`:项目日历数据接口(全年事件密度)
- 新增 `dashboard/gantt/`:项目 Gantt 历程条数据接口
- 新增 `dashboard/public-portal/`:公共展示主页接口(无需认证)
- 新增 `members/growth-timeline/`:成员成长时间线接口

#### 前端
- 新增 `ProjectTimeline.vue` 组件:项目详情统一时间线 Tab,7 种事件颜色,支持筛选
- 新增 `ProjectCalendarView.vue`:ECharts 日历热力图页面
- 新增 `ProjectGanttView.vue`:ECharts custom series 横向甘特图页面
- 新增 `CompetitionMatrixView.vue`:比赛矩阵视图(列表视图切换)
- 新增 `CompetitionFunnelView.vue`:比赛晋级漏斗视图(ECharts funnel)
- 修改 `CompetitionListView.vue`:添加列表/矩阵/漏斗三视图切换
- 新增路由: `dashboard/calendar`, `dashboard/gantt`, `projects/archive`, `public-portal`

### P2 新增功能

- 修改 `MemberDetailView.vue`:新增贡献汇总卡片 + 成长时间线区域
- 新增 `PublicPortalView.vue`:公共展示主页(Hero + 获奖项目 + 知识产权 + 核心成员)
- 增强 `PublicLayout.vue`:完整公共布局(导航 + 登录入口 + 版权)
- 修改 `FileListView.vue`:新增文件在线预览(图片/PDF/视频/音频 Blob 预览)
- 新增 `ProjectArchiveView.vue`:项目复盘归档页面(检索 + 统计 + 详情弹窗)

### 安全审查
- 敏感资料全链路复核通过:加密存储、脱敏显示、审批流程、限时查看、操作日志、权限控制

### 验证结果
- `python manage.py check`:通过
- `npx vue-tsc --noEmit`:通过
- `npm run build`:通过

---

## v0.8.1-stable - 2026-07-02

### P0 修复

- 敏感资料申请字段对齐：`target_user`/`data_type`/`use_scenario`/`need_download` → `sensitive_data`/`usage_scenario`/`is_download`
- 敏感资料审批/驳回字段对齐：`valid_duration`/`approve_comment`/`reject_comment` → `action`/`approval_opinion`/`expire_hours`
- 三个敏感资料入口（SensitiveCenterView / AccessRequestsView / PendingApproveView）全部验证通过

### P1 修复

- Dashboard 字段对齐：`total_income`/`total_used`/`status_distribution`/`risk_alerts`（移除 `total_budget`/`todo`/`doing`）
- 项目阶段 `current_stage_display`，比赛 Tab 空状态，移除 `competition` 字段读取
- 任务列表移除空 `priority` 列（后端模型无此字段）
- 成员列表/详情移除 `student_id`/`department`/`position` 等后端不返回字段
- 文件 `permission` → `level`(public/internal/sensitive)，新增 `level_display`
- 通知筛选 `notification_type` → `category`
- 操作日志筛选 `search`/`start_time`/`end_time` → `operator`/`start_date`/`end_date`
- 用户管理 `real_name`/`role` → `name`/`global_role`，新增 `password_confirm`，`ROLE_MAP` 全枚举对齐
- 知识产权贡献者下拉 `real_name` → `name`（兜底 username/email）
- 导入预览 `invalid_rows`/`suggested_mapping` → `error_rows`/`field_mapping`/`error_details`/`headers`

### P2 修复

- 敏感资料显示 `label` → `title`，类型优先 `data_type_display`
- 查看弹窗倒计时 `valid_duration` → `access_expires_at`，明文字段 `plain_value` → `plaintext`
- 常量映射补全：`NOTIFICATION_CATEGORY_MAP`(finance)、`AUDIT_ACTION_MAP`(upload/download/approve/reject/view_sensitive)、`FINANCE_CATEGORY_MAP`(printing/software/competition_fee/promotion)、`TASK_STATUS_MAP`(overdue: 已延期→已逾期)
- 经费筛选字段对齐后端 `filterset_fields`（预算移除 `category`，支出移除 `status`）
- 操作日志详情异步获取 `request_ip`（列表序列化器不含此字段）
- 排序异议表格移除 `objection_status` 列（后端无此字段），改为显示 `ranking_user_name`

### 验证结果

- 后端检查通过：`python manage.py check` / `makemigrations --check --dry-run` / `migrate`
- 前端检查通过：`npx vue-tsc --noEmit` / `npm run build`（2499 modules）
- 5 类账号登录通过（admin / teacher / leader / approver / member）
- 权限安全回归通过（普通成员 403 拦截，敏感资料不泄露明文）
- 核心演示链路通过

---

## v0.8-demo - 2026-07-01

### 初始版本

- 16 个核心模块功能实现
- JWT 认证 + RBAC 三层权限
- 敏感资料 Fernet 加密 + 审批流程
- 知识产权 14 状态机 + 责任追踪
- 操作日志中间件自动记录
- Excel 6 类导出
- 演示数据一键生成
