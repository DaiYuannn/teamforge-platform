# references/ 项目资料库

本目录用于存放项目相关的参考资料、文档、设计素材、聊天记录、验证报告和备份文件。

> **重要原则**：运行用文件不依赖本目录。正式运行的种子命令和素材保留在 `backend/apps/users/management/commands/` 和 `backend/seed_assets/`。

---

## 目录结构

| 目录 | 用途 | 说明 |
|---|---|---|
| `00_current-demo/` | 当前最新演示数据 | 服务器演示优先使用的 V2 比赛演示数据包及其说明 |
| `01_feature-tracker/` | 功能落地总表 | 记录功能实现状态、修改记录、版本路线图和未来需求规划 |
| `02_requirements/` | 需求文档 | 产品需求文档、页面设计需求、API 预留说明 |
| `03_chat-history/` | 聊天记录与上下文 | 历次会话的上下文文档、Docker 验证报告、回归分析 |
| `04_validation-reports/` | 验证报告 | 部署验收、截图 QA、API 检查结果（待后续补充） |
| `05_module-planning/` | 后续模块规划 | 新功能模块的规划文档，如公共展示主页等 |
| `06_design-assets/` | 设计素材 | 截图、Logo、Banner、首页图片等视觉素材（待后续补充） |
| `90_archives/` | 历史留存 | 旧版种子数据、不再使用的历史资料 |
| `99_backups/` | 备份文件 | 关键配置文件的自动/手动备份 |

---

## 各目录详情

### 00_current-demo/v2_competition_demo/

**当前最新演示数据源**，服务器部署时优先使用。包含：

- `team_management_competition_demo_seed_v2.zip` — V2 比赛演示数据完整包
- `V2_比赛矩阵与时间线说明.md` — 6 个项目 × 多赛事的矩阵设计说明
- `CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md` — 项目日历 / 横向时间线 / Gantt 模块缺口分析与规划
- `calendar_timeline_demo_events.json` — 24 条时间线事件预备数据（供后续 Gantt 模块使用）
- `extracted_snapshot/team_management_competition_demo_seed/` — zip 解压快照，包含种子脚本和完整素材文件

> **注意**：此目录下的 `calendar_timeline_demo_events.json`、`CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md`、`V2_比赛矩阵与时间线说明.md` 与 `extracted_snapshot/` 快照中的对应文件内容相同（重复保留）。

### 01_feature-tracker/

功能落地的核心文档：

- `功能落地总表与修改记录.md` — 完整的 16 模块状态表、P0/P1/P2/P3 修复记录、版本路线图、未来需求规划
- `功能落地总表与修改记录模板.md` — 上述文档的模板版本

### 02_requirements/

产品需求文档：

- `团队项目管理平台前端页面设计需求.md` — 前端页面设计需求
- `团队项目管理平台需求文档_v1.2_知识产权与API预留.md` — v1.2 需求文档，含知识产权与 API 预留说明

### 03_chat-history/

会话上下文与验证文档：

- `2026-07-02_local-docker-validation-report.md` — 本地 Docker 验证报告
- `2026-07-02_团队管理软件_v0.8.1-stable_P3回归与后续上下文.md` — P3 回归分析与后续建议
- `72_chathistory.md` — 早期会话记录

### 04_validation-reports/

> 待后续补充：部署验收截图、API 检查报告、移动端测试记录等。

### 05_module-planning/

后续功能模块的规划文档：

- `public-homepage/` — 网站公开首页设计任务说明（待后续补充）

### 06_design-assets/

> 待后续补充：Logo、Banner、首页图片、设计稿截图等视觉素材。

### 90_archives/

历史留存，不再作为当前演示首选：

- `old-seeds/` — 旧版种子数据（待后续补充，如有）

### 99_backups/

关键配置文件的历史备份：

- `20260702_194335/` — 2026-07-02 的自动备份，包含 `.env.docker`、`docker-compose.yml`、`backend.Dockerfile`、requirements 等

---

## 文件移动记录（2026-07-03）

### 已移动的文件

| 原位置 | 新位置 | 说明 |
|---|---|---|
| `team_management_competition_demo_seed_v2.zip` | `00_current-demo/v2_competition_demo/` | V2 演示数据包 |
| `V2_比赛矩阵与时间线说明.md` | `00_current-demo/v2_competition_demo/` | V2 设计说明 |
| `CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md` | `00_current-demo/v2_competition_demo/` | 日历/Gantt 缺口分析 |
| `calendar_timeline_demo_events.json` | `00_current-demo/v2_competition_demo/` | 时间线事件数据 |
| `team_management_competition_demo_seed_v2/` | `00_current-demo/v2_competition_demo/extracted_snapshot/` | 解压快照 |
| `团队项目管理平台前端页面设计需求.md` | `02_requirements/` | 前端设计需求 |
| `团队项目管理平台需求文档_v1.2_知识产权与API预留.md` | `02_requirements/` | v1.2 需求文档 |

### 已重命名的目录

| 原名 | 新名 | 说明 |
|---|---|---|
| `feature-tracker/` | `01_feature-tracker/` | 功能落地总表 |
| `chat-history/` | `03_chat-history/` | 聊天记录 |
| `backups/` | `99_backups/` | 备份文件 |

### 重复文件说明

以下文件在 `00_current-demo/v2_competition_demo/` 和 `extracted_snapshot/team_management_competition_demo_seed/` 中同时存在，内容完全相同，均保留：

- `calendar_timeline_demo_events.json`
- `CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md`
- `V2_比赛矩阵与时间线说明.md`

### 未移动的文件

- `extracted_snapshot/team_management_competition_demo_seed/__pycache__/` — 为 zip 解压产生的 Python 缓存目录，保留在快照中，不影响运行

---

## 更新记录

| 日期 | 操作 | 说明 |
|---|---|---|
| 2026-07-03 | 目录结构整理 | 创建编号目录，归档历史文件，统一 V2 演示数据 |
