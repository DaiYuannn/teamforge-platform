# CHANGELOG

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
