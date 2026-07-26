# API 接口文档

> 团队管理软件后端接口文档
> 版本：v1
> Base URL：`/api/v1`

> v2.0 说明：本文保留基础模块的详细契约；以下“当前扩展端点”是新功能的权威入口。OpenAPI 仍以运行中的 `/api/v1/common/openapi/` 输出为准。系统不提供 2FA；OAuth 端点仅在服务端提供商被实际配置后可用。

---

## 当前扩展端点

| 功能 | 方法与路径 | 说明 |
|------|------------|------|
| 账户偏好 | `GET/PATCH /users/preference/` | 主色、默认页、分页、范围、布局、收藏和通知偏好 |
| 统一时间线 | `GET /dashboard/timeline/` | 支持逗号分隔的精确 `event_type` 多选过滤 |
| 项目日历 | `GET /dashboard/calendar/` | 项目、任务、比赛和经费日期聚合 |
| 票据 OCR | `POST /finance/ocr/recognize/` | 上传票据并返回需人工复核的结构化字段 |
| 演示备份列表 | `GET /common/backup/` | 仅管理员，仅管理完整演示种子拥有的数据 |
| 创建演示备份 | `POST /common/backup/create/` | 生成快照、附件与校验清单 |
| 下载演示备份 | `GET /common/backup/{backup_id}/download/` | 下载 ZIP 包 |
| 恢复演示备份 | `POST /common/backup/{backup_id}/restore/` | 需要显式确认，先生成回滚包 |
| 定时报表 | `/exports/scheduled-reports/` | CRUD、启停、立即运行、执行记录与下载 |
| 自定义报表 | `/exports/custom-reports/` | 报表模板 CRUD 与生成 |
| 实时通知 | `GET /notifications/sse/` | JWT 鉴权的 SSE，支持游标补发 |
| 通知筛选 | `GET /notifications/?category=report` | 支持任务、项目、比赛、经费、报表等分类 |

---

## 目录

- [通用说明](#通用说明)
- [认证模块 (auth)](#认证模块-auth)
- [用户模块 (users)](#用户模块-users)
- [项目模块 (projects)](#项目模块-projects)
- [比赛模块 (competitions)](#比赛模块-competitions)
- [任务模块 (tasks)](#任务模块-tasks)
- [经费模块 (finance)](#经费模块-finance)
- [成员模块 (members)](#成员模块-members)
- [贡献模块 (contributions)](#贡献模块-contributions)
- [知识产权模块 (intellectual_property)](#知识产权模块-intellectual_property)
- [敏感资料模块 (sensitive)](#敏感资料模块-sensitive)
- [通知模块 (notifications)](#通知模块-notifications)
- [审计模块 (audit)](#审计模块-audit)
- [导出模块 (exports)](#导出模块-exports)
- [集成模块 (integrations)](#集成模块-integrations)

---

## 通用说明

### 统一响应格式

所有接口均返回统一的 JSON 结构：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示业务错误 |
| message | string | 提示消息，成功为 `"success"`，失败为错误描述 |
| data | object/array/null | 业务数据，失败时通常为 `null` |

常见业务错误码：

| code | 含义 |
|------|------|
| 0 | 成功 |
| 1001 | 参数缺失或无效 |
| 1003 | 权限不足 |
| 1004 | 资源不存在 |
| 1005 | 运行时依赖不可用（如 PDF 导出） |
| 1006 | 导出失败 |
| 1007 | 重复操作 / 资源已存在 |

### 认证方式

除登录、刷新 token 外，所有接口均需在请求头携带 JWT：

```
Authorization: Bearer <access_token>
```

### 分页约定

列表接口统一使用 `page` + `page_size` 查询参数进行分页，默认每页 20 条，最大 100 条。分页响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 100,
    "next": "http://host/api/v1/xxx/?page=2&page_size=20",
    "previous": null,
    "current_page": 1,
    "total_pages": 5,
    "page_size": 20,
    "results": [ ... ]
  }
}
```

### 通用查询参数

| 参数 | 说明 |
|------|------|
| page | 当前页码，从 1 开始 |
| page_size | 每页条数，默认 20，最大 100 |
| search | 关键词搜索（对应各接口 search_fields） |
| ordering | 排序字段，前缀 `-` 表示降序 |
| <filterset_field> | 各接口支持的字段过滤 |

### 全局角色（global_role）

| 角色值 | 中文名 | 说明 |
|--------|--------|------|
| sys_admin | 系统管理员 | 拥有全部权限 |
| teacher | 老师 | 确认排序、查看日志、知识产权归档等 |
| sens_approver | 敏感审批人 | 审批敏感资料查看申请 |
| member | 普通成员 | 默认角色，填写贡献/工时等 |

---

## 认证模块 (auth)

### POST /api/v1/auth/login/ - 登录

邮箱 + 密码登录，返回 JWT token 与用户信息。

- **方法**：POST
- **权限**：公开

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 登录邮箱 |
| password | string | 是 | 登录密码 |

```json
{
  "email": "admin@demo.com",
  "password": "admin123456"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "token": {
      "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user": {
      "id": 1,
      "name": "系统管理员",
      "email": "admin@demo.com",
      "global_role": "sys_admin",
      "username": "admin",
      "phone": "13800000000",
      "avatar": null,
      "is_student": false,
      "grade": "",
      "major": ""
    }
  }
}
```

- **备注**：账号被禁用时返回 `code: 1002`，提示「账号已被禁用」；邮箱或密码错误返回 `code: 1001`。

### POST /api/v1/auth/token/refresh/ - 刷新 token

使用 refresh token 换取新的 access token。

- **方法**：POST
- **权限**：公开

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| refresh | string | 是 | 登录时返回的 refresh token |

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

- **备注**：refresh token 过期或无效时返回 401，前端应跳转登录页。

---

## 用户模块 (users)

### GET /api/v1/users/ - 用户列表

获取系统用户列表。

- **方法**：GET
- **权限**：管理员 / 老师（`IsUserManager`）
- **查询参数**：`global_role`、`is_student`、`is_active`、`grade`、`major`、`search`、`ordering`、`page`、`page_size`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 8,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "name": "系统管理员",
        "email": "admin@demo.com",
        "global_role": "sys_admin",
        "phone": "13800000000",
        "is_active": true,
        "is_student": false,
        "date_joined": "2026-06-01T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/users/ - 创建用户

- **方法**：POST
- **权限**：管理员 / 老师

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 邮箱（唯一） |
| name | string | 是 | 姓名 |
| password | string | 是 | 密码 |
| global_role | string | 否 | 全局角色，默认 member |
| phone | string | 否 | 手机号 |
| is_student | bool | 否 | 是否学生 |
| grade | string | 否 | 年级 |
| major | string | 否 | 专业 |

```json
{
  "email": "newuser@demo.com",
  "name": "新用户",
  "password": "user123456",
  "global_role": "member",
  "phone": "13800000009",
  "is_student": true,
  "grade": "2024级",
  "major": "软件工程"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "用户创建成功",
  "data": {
    "id": 9,
    "email": "newuser@demo.com",
    "name": "新用户",
    "global_role": "member"
  }
}
```

### GET /api/v1/users/me/ - 当前用户信息

获取当前登录用户的个人信息。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "email": "admin@demo.com",
    "name": "系统管理员",
    "global_role": "sys_admin",
    "phone": "13800000000",
    "avatar": null,
    "is_student": false,
    "grade": "",
    "major": ""
  }
}
```

### PUT /api/v1/users/me/ - 更新个人信息

更新当前登录用户的个人资料（不可修改 global_role 等敏感字段）。

- **方法**：PUT / PATCH
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 姓名 |
| phone | string | 否 | 手机号 |
| avatar | string | 否 | 头像 |
| grade | string | 否 | 年级 |
| major | string | 否 | 专业 |

```json
{
  "name": "管理员",
  "phone": "13900000000"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "个人信息更新成功",
  "data": {
    "id": 1,
    "name": "管理员",
    "email": "admin@demo.com",
    "global_role": "sys_admin",
    "phone": "13900000000"
  }
}
```

- **备注**：完整 CRUD（`GET/POST/PUT/PATCH/DELETE /api/v1/users/{id}/`）均由管理员/老师操作。

---

## 项目模块 (projects)

### GET /api/v1/projects/ - 项目列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`status`、`priority`、`current_stage`、`leader`、`search`（名称/编号/简介）、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 10,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "name": "智能办公系统",
        "code": "PRJ-2026-001",
        "intro": "面向中小企业的智能办公平台",
        "leader": { "id": 4, "name": "王明" },
        "current_stage": 3,
        "current_stage_name": "材料准备",
        "status": "in_progress",
        "priority": "high",
        "start_date": "2026-03-01",
        "planned_end_date": "2026-12-31",
        "member_count": 6,
        "created_at": "2026-03-01T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/projects/ - 创建项目

- **方法**：POST
- **权限**：老师 / 管理员（项目负责人/老师/管理员）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 项目名称 |
| code | string | 是 | 项目编号 |
| intro | string | 否 | 项目简介 |
| leader | int | 是 | 项目负责人用户 ID |
| priority | string | 否 | 优先级 low/medium/high/urgent |
| start_date | date | 否 | 开始日期 |
| planned_end_date | date | 否 | 预计结束日期 |

```json
{
  "name": "智能办公系统",
  "code": "PRJ-2026-001",
  "intro": "面向中小企业的智能办公平台",
  "leader": 4,
  "priority": "high",
  "start_date": "2026-03-01",
  "planned_end_date": "2026-12-31"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "项目创建成功",
  "data": {
    "id": 1,
    "name": "智能办公系统",
    "code": "PRJ-2026-001",
    "leader": { "id": 4, "name": "王明" },
    "current_stage": 1,
    "status": "in_progress",
    "priority": "high"
  }
}
```

### GET /api/v1/projects/{id}/ - 项目详情

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "智能办公系统",
    "code": "PRJ-2026-001",
    "intro": "面向中小企业的智能办公平台",
    "leader": { "id": 4, "name": "王明", "email": "leader1@demo.com" },
    "current_stage": 3,
    "status": "in_progress",
    "priority": "high",
    "start_date": "2026-03-01",
    "planned_end_date": "2026-12-31",
    "members": [
      { "id": 1, "user": { "id": 8, "name": "普通成员" }, "role_in_project": "core", "joined_at": "2026-03-02T10:00:00+08:00" }
    ],
    "created_at": "2026-03-01T10:00:00+08:00"
  }
}
```

### PATCH /api/v1/projects/{id}/ - 更新项目

- **方法**：PUT / PATCH
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：同创建项目（字段均可选，部分更新）。

```json
{
  "intro": "更新后的项目简介",
  "priority": "urgent"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "项目更新成功",
  "data": { "id": 1, "intro": "更新后的项目简介", "priority": "urgent" }
}
```

- **备注**：`DELETE /api/v1/projects/{id}/` 删除项目，权限同更新。

### POST /api/v1/projects/{id}/stage/ - 阶段流转

推进项目阶段。

- **方法**：POST
- **权限**：项目负责人

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| to_stage | int | 是 | 目标阶段编号 |
| note | string | 否 | 流转备注 |

```json
{
  "to_stage": 3,
  "note": "进入材料准备阶段"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "阶段推进成功",
  "data": { "id": 1, "current_stage": 3, "current_stage_name": "材料准备" }
}
```

- **备注**：`to_stage` 必须为整数，且需符合阶段流转规则；非法流转返回错误提示。

### POST /api/v1/projects/{id}/leader_update/ - 负责人更新打卡

项目负责人定期打卡更新项目进展。

- **方法**：POST
- **权限**：项目负责人

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| note | string | 否 | 打卡内容说明 |

```json
{
  "note": "本周完成了需求分析与原型设计"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "打卡更新成功",
  "data": { "id": 1, "current_stage": 3, "status": "in_progress" }
}
```

- **备注**：项目还提供 `GET /api/v1/projects/{id}/members/`（成员管理）、`GET /api/v1/projects/{id}/stage_logs/`（阶段变更日志）等子接口。

---

## 比赛模块 (competitions)

### GET /api/v1/competitions/ - 比赛列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`project`、`level`、`status`、`is_promoted`、`is_awarded`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "name": "互联网+创新创业大赛",
        "organizer": "教育部",
        "level": "national",
        "status": "registered",
        "project": { "id": 1, "name": "智能办公系统" },
        "is_promoted": false,
        "is_awarded": false,
        "register_date": "2026-04-01",
        "defense_date": null
      }
    ]
  }
}
```

### POST /api/v1/competitions/ - 创建比赛

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 比赛名称 |
| organizer | string | 否 | 主办方 |
| level | string | 否 | 级别 school/provincial/national/international |
| project | int | 否 | 关联项目 ID |
| register_date | date | 否 | 报名日期 |

```json
{
  "name": "互联网+创新创业大赛",
  "organizer": "教育部",
  "level": "national",
  "project": 1,
  "register_date": "2026-04-01"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "比赛创建成功",
  "data": { "id": 1, "name": "互联网+创新创业大赛", "level": "national", "status": "registered" }
}
```

### PATCH /api/v1/competitions/{id}/ - 更新比赛

- **方法**：PUT / PATCH
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：同创建比赛（字段均可选）。

```json
{
  "status": "awarded",
  "is_awarded": true,
  "defense_date": "2026-06-15"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "比赛更新成功",
  "data": { "id": 1, "status": "awarded", "is_awarded": true }
}
```

- **备注**：`DELETE /api/v1/competitions/{id}/` 删除比赛。

---

## 任务模块 (tasks)

> 任务完成情况对所有认证用户可见。

### GET /api/v1/tasks/ - 任务列表

- **方法**：GET
- **权限**：已认证（完成情况全员可见）
- **查询参数**：`project`、`assignee`、`creator`、`status`、`reviewer`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 20,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "title": "完成首页原型设计",
        "project": { "id": 1, "name": "智能办公系统" },
        "assignee": { "id": 8, "name": "普通成员" },
        "status": "in_progress",
        "priority": "high",
        "deadline": "2026-07-10",
        "progress": 60
      }
    ]
  }
}
```

### POST /api/v1/tasks/ - 创建任务

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 任务标题 |
| project | int | 是 | 所属项目 ID |
| assignee | int | 否 | 指派给谁 |
| description | string | 否 | 任务描述 |
| priority | string | 否 | 优先级 |
| deadline | date | 否 | 截止日期 |
| reviewer | int | 否 | 审核人 |

```json
{
  "title": "完成首页原型设计",
  "project": 1,
  "assignee": 8,
  "priority": "high",
  "deadline": "2026-07-10"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "任务创建成功",
  "data": { "id": 1, "title": "完成首页原型设计", "status": "todo", "priority": "high" }
}
```

### PATCH /api/v1/tasks/{id}/ - 更新任务

- **方法**：PUT / PATCH
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：同创建任务（字段均可选）。

```json
{
  "title": "完成首页及详情页原型设计",
  "priority": "urgent"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "任务更新成功",
  "data": { "id": 1, "title": "完成首页及详情页原型设计", "priority": "urgent" }
}
```

### PATCH /api/v1/tasks/{id}/status/ - 状态流转

修改任务状态。

- **方法**：POST（状态流转动作）
- **权限**：已认证（任务指派人 / 协作者 / 创建者 / 审核人 / 管理员 / 老师）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| to_status | string | 是 | 目标状态 todo/in_progress/done/pending_review/blocked |
| delay_reason | string | 否 | 延期原因 |

```json
{
  "to_status": "done",
  "delay_reason": ""
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "任务状态更新成功",
  "data": { "id": 1, "status": "done", "progress": 100 }
}
```

- **备注**：`to_status` 必须为合法状态值；无权限的用户返回 `code: 1003`。

---

## 经费模块 (finance)

> 经费明细和票据对所有认证用户完全公开可见。

### GET /api/v1/finance/budgets/ - 经费总表

- **方法**：GET
- **权限**：已认证（完全公开）
- **查询参数**：`project`、`status`、`period`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "project": { "id": 1, "name": "智能办公系统", "code": "PRJ-2026-001" },
        "bonus_amount": "50000.00",
        "other_income": "10000.00",
        "total_budget": "60000.00",
        "used_amount": "12000.00",
        "remaining": "48000.00",
        "status": "active",
        "period": "2026",
        "updated_at": "2026-06-20T10:00:00+08:00"
      }
    ]
  }
}
```

### GET /api/v1/finance/expenses/ - 经费明细

- **方法**：GET
- **权限**：已认证（完全公开）
- **查询参数**：`project`、`category`、`spender`、`expense_date`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 15,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "project": { "id": 1, "name": "智能办公系统" },
        "title": "服务器采购",
        "category": "equipment",
        "amount": "8000.00",
        "spender": { "id": 4, "name": "王明" },
        "expense_date": "2026-06-15",
        "purpose": "项目部署服务器"
      }
    ]
  }
}
```

### POST /api/v1/finance/expenses/ - 创建支出

- **方法**：POST
- **权限**：项目负责人

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project | int | 是 | 项目 ID |
| title | string | 是 | 支出标题 |
| category | string | 是 | 类别 equipment/material/travel/other 等 |
| amount | decimal | 是 | 金额 |
| expense_date | date | 是 | 支出日期 |
| purpose | string | 否 | 用途说明 |
| spender | int | 否 | 经办人 ID，默认当前用户 |

```json
{
  "project": 1,
  "title": "服务器采购",
  "category": "equipment",
  "amount": "8000.00",
  "expense_date": "2026-06-15",
  "purpose": "项目部署服务器"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "经费明细创建成功",
  "data": { "id": 1, "title": "服务器采购", "amount": "8000.00", "category": "equipment" }
}
```

### POST /api/v1/finance/expenses/{id}/receipts/ - 上传票据

为指定经费明细上传票据文件。

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员
- **Content-Type**：`multipart/form-data`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| expense | int | 是 | 经费明细 ID |
| file | file | 是 | 票据文件 |
| note | string | 否 | 备注 |

**返回示例**：

```json
{
  "code": 0,
  "message": "票据上传成功",
  "data": {
    "id": 1,
    "expense": 1,
    "file": "/media/receipts/receipt_001.pdf",
    "uploaded_by": { "id": 4, "name": "王明" },
    "created_at": "2026-06-15T10:00:00+08:00"
  }
}
```

- **备注**：票据列表 `GET /api/v1/finance/receipts/` 对所有认证用户开放读取。

---

## 成员模块 (members)

> 成员列表对已认证用户开放，联系方式可见。

### GET /api/v1/members/ - 成员列表

- **方法**：GET
- **权限**：已认证（联系方式可见）
- **查询参数**：`global_role`、`is_student`、`grade`、`major`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 8,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 4,
        "name": "王明",
        "email": "leader1@demo.com",
        "global_role": "member",
        "phone": "13800000004",
        "is_student": false,
        "grade": "",
        "major": "软件工程"
      }
    ]
  }
}
```

### GET /api/v1/members/member-detail/ - 成员详情

获取成员基本信息 + 技能 + 灵活工时 + 参与项目 + 任务。

- **方法**：GET
- **权限**：已认证
- **查询参数**：`user_id`（不传则返回当前用户）

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 4,
    "name": "王明",
    "email": "leader1@demo.com",
    "global_role": "member",
    "phone": "13800000004",
    "skills": [
      { "id": 1, "skill": { "id": 1, "name": "Vue" }, "proficiency": "proficient" }
    ],
    "latest_schedule": {
      "period_start": "2026-06-16",
      "period_end": "2026-06-30",
      "available_hours": 40
    },
    "projects": [
      { "id": 1, "name": "智能办公系统", "role_in_project": "leader" }
    ]
  }
}
```

### GET /api/v1/members/skill-tags/ - 技能标签列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 10,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      { "id": 1, "name": "Vue", "category": "frontend", "created_at": "2026-06-01T10:00:00+08:00" }
    ]
  }
}
```

### POST /api/v1/members/skill-tags/ - 创建技能标签

- **方法**：POST
- **权限**：管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 标签名称 |
| category | string | 否 | 分类 frontend/backend/design/other |

```json
{
  "name": "React",
  "category": "frontend"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "技能标签创建成功",
  "data": { "id": 11, "name": "React", "category": "frontend" }
}
```

- **备注**：技能标签的更新/删除仅管理员可操作。

### GET /api/v1/members/member-skills/ - 我的技能

获取当前用户的技能列表。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "user": { "id": 8, "name": "普通成员" },
      "skill": { "id": 1, "name": "Vue" },
      "proficiency": "proficient",
      "created_at": "2026-06-05T10:00:00+08:00"
    }
  ]
}
```

### POST /api/v1/members/member-skills/ - 添加技能

为当前用户添加技能。

- **方法**：POST
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| skill | int | 是 | 技能标签 ID |
| proficiency | string | 否 | 熟练度 beginner/proficient/expert |

```json
{
  "skill": 1,
  "proficiency": "proficient"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "技能添加成功",
  "data": { "id": 2, "skill": { "id": 1, "name": "Vue" }, "proficiency": "proficient" }
}
```

- **备注**：重复添加返回 `code: 1007`；只能修改/删除自己的技能。

### GET /api/v1/members/flexible-schedules/ - 我的灵活工时

获取当前用户的灵活工作时间记录。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "user": { "id": 8, "name": "普通成员" },
        "period_start": "2026-06-16",
        "period_end": "2026-06-30",
        "available_hours": 40,
        "note": "本周可全职投入",
        "created_at": "2026-06-16T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/members/flexible-schedules/ - 填写灵活工时

每半月填写一次灵活工作时间。

- **方法**：POST
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period_start | date | 是 | 周期开始日期 |
| period_end | date | 是 | 周期结束日期 |
| available_hours | int | 是 | 可用工时 |
| note | string | 否 | 备注 |

```json
{
  "period_start": "2026-06-16",
  "period_end": "2026-06-30",
  "available_hours": 40,
  "note": "本周可全职投入"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "灵活工作时间填写成功",
  "data": { "id": 2, "period_start": "2026-06-16", "available_hours": 40 }
}
```

- **备注**：同一周期不可重复填写，重复返回 `code: 1007`。

### GET /api/v1/members/flexible-schedules/current_period/ - 当前周期

获取当前半月周期及当前用户是否已填写。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "period_start": "2026-06-16",
    "period_end": "2026-06-30",
    "is_filled": true,
    "schedule": {
      "id": 1,
      "available_hours": 40,
      "note": "本周可全职投入"
    }
  }
}
```

### GET /api/v1/members/flexible-schedules/all_latest/ - 全员最新工时

获取所有成员最新一条灵活工时记录（全员可见）。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "user": { "id": 4, "name": "王明" },
      "period_start": "2026-06-16",
      "period_end": "2026-06-30",
      "available_hours": 40
    }
  ]
}
```

---

## 贡献模块 (contributions)

### GET /api/v1/contributions/contributions/ - 贡献列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`project`、`status`、`user`、`contribution_type`、`period`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 12,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "project": { "id": 1, "name": "智能办公系统" },
        "user": { "id": 8, "name": "普通成员" },
        "contribution_type": "development",
        "content": "完成用户认证模块开发",
        "weight": 10,
        "status": "pending",
        "period": "2026-06",
        "filled_by": { "id": 8, "name": "普通成员" },
        "created_at": "2026-06-20T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/contributions/contributions/ - 填写贡献

- **方法**：POST
- **权限**：项目成员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project | int | 是 | 项目 ID |
| user | int | 是 | 贡献人 ID |
| contribution_type | string | 是 | 类型 development/design/document/other |
| content | string | 是 | 贡献内容 |
| weight | int | 否 | 权重 |
| period | string | 否 | 统计周期，如 2026-06 |

```json
{
  "project": 1,
  "user": 8,
  "contribution_type": "development",
  "content": "完成用户认证模块开发",
  "weight": 10,
  "period": "2026-06"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "贡献记录创建成功，等待项目负责人审核",
  "data": { "id": 1, "status": "pending", "content": "完成用户认证模块开发" }
}
```

- **备注**：仅项目成员可创建该项目贡献记录，非成员返回 `code: 1003`。

### POST /api/v1/contributions/contributions/{id}/review/ - 审核

项目负责人审核贡献记录。

- **方法**：PATCH
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | approved / rejected |
| review_opinion | string | 否 | 审核意见 |
| weight | int | 否 | 调整后权重 |

```json
{
  "status": "approved",
  "review_opinion": "工作扎实，权重合理",
  "weight": 12
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "贡献记录审核完成",
  "data": { "id": 1, "status": "approved", "weight": 12, "reviewer": { "id": 4, "name": "王明" } }
}
```

- **备注**：仅待审核（pending）状态可审核，重复审核返回错误。

### GET /api/v1/contributions/contributions/my_contributions/ - 我的贡献

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      { "id": 1, "contribution_type": "development", "content": "完成用户认证模块开发", "status": "approved" }
    ]
  }
}
```

### GET /api/v1/contributions/contributions/pending_review/ - 待我审核

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      { "id": 1, "user": { "id": 8, "name": "普通成员" }, "content": "完成用户认证模块开发", "status": "pending" }
    ]
  }
}
```

- **备注**：老师/管理员可见所有待审核贡献；项目负责人仅可见自己负责项目的待审核贡献。

### POST /api/v1/contributions/rankings/generate/ - 生成排序

项目负责人生成成员排序草案。

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project | int | 是 | 项目 ID |
| period | string | 否 | 统计周期，如 2026-06 |

```json
{
  "project": 1,
  "period": "2026-06"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "排序草案生成成功",
  "data": [
    { "id": 1, "user": { "id": 8, "name": "普通成员" }, "rank": 1, "total_score": 95, "status": "draft" },
    { "id": 2, "user": { "id": 9, "name": "赵同学" }, "rank": 2, "total_score": 88, "status": "draft" }
  ]
}
```

### POST /api/v1/contributions/rankings/confirm/ - 确认排序

老师确认排序（确认后不可改，对全员公开）。

- **方法**：POST
- **权限**：老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | array | 否 | 排序记录 ID 列表 |
| project | int | 否 | 项目 ID（与 period 配合确认全部草案） |
| period | string | 否 | 统计周期 |

```json
{
  "project": 1,
  "period": "2026-06"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "成功确认2条排名",
  "data": { "confirmed_count": 2 }
}
```

### POST /api/v1/contributions/objections/ - 提交异议

项目成员对排名提出异议。

- **方法**：POST
- **权限**：项目成员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ranking | int | 是 | 排名记录 ID |
| content | string | 是 | 异议内容 |

```json
{
  "ranking": 1,
  "content": "我认为排名未充分考虑文档贡献"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "异议提交成功",
  "data": { "id": 1, "status": "pending", "content": "我认为排名未充分考虑文档贡献" }
}
```

- **备注**：排名须已公开（已确认）才能提异议。

### POST /api/v1/contributions/objections/{id}/leader_review/ - 初审

项目负责人对异议进行初审。

- **方法**：PATCH
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| leader_opinion | string | 否 | 负责人意见 |
| action | string | 是 | 固定为 `leader_review` |

```json
{
  "action": "leader_review",
  "leader_opinion": "经核实，文档贡献已计入"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "异议初审完成",
  "data": { "id": 1, "status": "leader_reviewed", "leader_opinion": "经核实，文档贡献已计入" }
}
```

### POST /api/v1/contributions/objections/{id}/teacher_confirm/ - 终审

老师对异议进行最终确认。

- **方法**：PATCH
- **权限**：老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 `teacher_confirm` |
| teacher_opinion | string | 否 | 老师意见 |
| final_result | string | 否 | 最终结果说明 |
| final_status | string | 是 | approved / rejected |

```json
{
  "action": "teacher_confirm",
  "teacher_opinion": "维持原排名",
  "final_result": "排名合理，维持原排序",
  "final_status": "approved"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "异议最终确认完成",
  "data": { "id": 1, "status": "approved", "final_result": "排名合理，维持原排序" }
}
```

- **备注**：异议须先经负责人初审，老师才能终审。

---

## 知识产权模块 (intellectual_property)

### GET /api/v1/intellectual-property/applications/ - 申请列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`ip_type`、`status`、`related_project`、`main_writer`、`applicant_executor`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 4,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "title": "智能办公调度方法及系统",
        "application_code": "IP-2026-001",
        "ip_type": "invention",
        "status": "writing",
        "related_project": { "id": 1, "name": "智能办公系统" },
        "main_writer": { "id": 4, "name": "王明" },
        "created_at": "2026-05-01T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/intellectual-property/applications/ - 创建申请

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 成果名称 |
| ip_type | string | 是 | 类型 invention/utility_model/software_copyright/paper |
| related_project | int | 否 | 关联项目 ID |
| main_writer | int | 否 | 主导撰写人 ID |
| applicant_executor | int | 否 | 申请执行人 ID |
| intro | string | 否 | 简介 |

```json
{
  "title": "智能办公调度方法及系统",
  "ip_type": "invention",
  "related_project": 1,
  "main_writer": 4,
  "intro": "一种面向任务调度的智能方法"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "知识产权申请创建成功",
  "data": { "id": 1, "title": "智能办公调度方法及系统", "ip_type": "invention", "status": "writing" }
}
```

### GET /api/v1/intellectual-property/applications/{id}/ - 申请详情

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "title": "智能办公调度方法及系统",
    "application_code": "IP-2026-001",
    "ip_type": "invention",
    "status": "writing",
    "related_project": { "id": 1, "name": "智能办公系统" },
    "main_writer": { "id": 4, "name": "王明" },
    "applicant_executor": { "id": 8, "name": "普通成员" },
    "contributors": [
      { "id": 1, "user": { "id": 8, "name": "普通成员" }, "role": "writer", "is_confirmed": false }
    ],
    "return_records": [],
    "created_at": "2026-05-01T10:00:00+08:00"
  }
}
```

- **备注**：项目成员可见完整字段，非成员仅可见公开字段。

### POST /api/v1/intellectual-property/applications/{id}/transition/ - 状态流转

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员，或主导撰写人 / 申请执行人

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_status | string | 是 | 目标状态 writing/leader_review/teacher_confirm/returned/research_office_review/accepted/archived 等 |

```json
{
  "target_status": "leader_review"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "状态流转成功",
  "data": { "id": 1, "status": "leader_review" }
}
```

### POST /api/v1/intellectual-property/applications/{id}/archive/ - 成果归档

- **方法**：POST
- **权限**：老师 / 管理员

**请求参数**：无

**返回示例**：

```json
{
  "code": 0,
  "message": "成果归档成功",
  "data": { "id": 1, "status": "archived" }
}
```

### POST /api/v1/intellectual-property/applications/{id}/sync-contribution/ - 同步贡献

将知识产权成果同步为项目成员的贡献记录。

- **方法**：POST
- **权限**：项目负责人 / 老师 / 管理员

**请求参数**：无

**返回示例**：

```json
{
  "code": 0,
  "message": "成功同步3条贡献记录",
  "data": { "synced_count": 3 }
}
```

### GET /api/v1/intellectual-property/applications/my_todo/ - 待我处理

根据当前用户在申请中的角色及申请状态，返回需要处理的申请列表。

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 2,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      { "id": 1, "title": "智能办公调度方法及系统", "status": "writing", "main_writer": { "id": 4, "name": "王明" } }
    ]
  }
}
```

### POST /api/v1/intellectual-property/returns/ - 创建退回记录

- **方法**：POST
- **权限**：申请执行人 / 项目负责人 / 老师 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| application | int | 是 | 申请 ID |
| return_source | string | 否 | 退回来源 |
| return_reason | string | 是 | 退回原因 |
| responsibility_type | string | 否 | 责任类型 |
| responsible_user | int | 否 | 责任人 ID |
| modify_deadline | date | 否 | 修改截止日期 |

```json
{
  "application": 1,
  "return_source": "research_office",
  "return_reason": "权利要求书需补充技术特征",
  "modify_deadline": "2026-07-15"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "退回记录创建成功",
  "data": { "id": 1, "application": 1, "return_reason": "权利要求书需补充技术特征", "result": "pending" }
}
```

### POST /api/v1/intellectual-property/returns/{id}/resolve/ - 完成修改

- **方法**：POST
- **权限**：责任人 / 主导撰写人 / 申请执行人

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| modify_description | string | 否 | 修改说明 |
| result | string | 否 | 结果 modified/unresolved |

```json
{
  "modify_description": "已补充独立权利要求的技术特征",
  "result": "modified"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "退回修改已完成",
  "data": { "id": 1, "result": "modified", "modify_description": "已补充独立权利要求的技术特征" }
}
```

### POST /api/v1/intellectual-property/objections/ - 提交异议

- **方法**：POST
- **权限**：项目成员 / 已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| application | int | 是 | 申请 ID |
| objection_type | string | 否 | 异议类型 |
| content | string | 是 | 异议内容 |

```json
{
  "application": 1,
  "content": "责任分工与实际贡献不符"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "异议创建成功",
  "data": { "id": 1, "status": "pending", "content": "责任分工与实际贡献不符" }
}
```

### PATCH /api/v1/intellectual-property/objections/{id}/review/ - 处理异议

负责人初审 / 老师最终确认。

- **方法**：PATCH
- **权限**：已认证（负责人初审需项目负责人/老师/管理员；终审需老师/管理员）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | leader_review / teacher_confirm |
| leader_opinion | string | 否 | 负责人意见（初审） |
| teacher_opinion | string | 否 | 老师意见（终审） |
| final_result | string | 否 | 最终结果（终审） |
| final_status | string | 终审必填 | resolved / rejected |

```json
{
  "action": "teacher_confirm",
  "teacher_opinion": "已重新核对分工",
  "final_result": "调整分工比例",
  "final_status": "resolved"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "异议处理成功",
  "data": { "id": 1, "status": "resolved", "final_result": "调整分工比例" }
}
```

- **备注**：知识产权模块还包含责任分工 `contributors`、材料版本 `materials` 等子资源接口。

---

## 敏感资料模块 (sensitive)

> 敏感资料明文绝不裸露，必须审批后限时查看，每次查看写 OperationLog。

### GET /api/v1/sensitive/data/ - 敏感资料列表（脱敏）

- **方法**：GET
- **权限**：已认证（管理员/敏感审批人/老师可见全部，普通成员仅可见自己上传的，均脱敏展示）

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "title": "王明身份证",
        "data_type": "id_card",
        "masked_content": "330***********1234",
        "project": { "id": 1, "name": "智能办公系统" },
        "uploader": { "id": 4, "name": "王明" },
        "created_at": "2026-06-01T10:00:00+08:00"
      }
    ]
  }
}
```

### GET /api/v1/sensitive/data/my_data/ - 我的资料（脱敏）

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 2,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      { "id": 1, "title": "王明身份证", "data_type": "id_card", "masked_content": "330***********1234" }
    ]
  }
}
```

### POST /api/v1/sensitive/data/{id}/view/ - 查看明文（需审批）

凭有效访问申请查看敏感资料明文。

- **方法**：POST
- **权限**：已认证且持有有效审批（`HasValidAccessApproval`）

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| request_id | int | 是 | 访问申请 ID |

```json
{
  "request_id": 1
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "查看成功，请注意明文保密",
  "data": { "plaintext": "330106199001011234" }
}
```

- **备注**：申请须已通过且未过期，每次查看写操作日志；申请与资料不匹配返回 `code: 1003`。

### GET /api/v1/sensitive/access-requests/ - 申请列表

- **方法**：GET
- **权限**：已认证（申请人查看自己的申请，审批人/管理员/老师查看待审批的）
- **查询参数**：`status`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "sensitive_data": { "id": 1, "title": "王明身份证" },
        "applicant": { "id": 8, "name": "普通成员" },
        "status": "pending",
        "reason": "办理签证需要核对身份信息",
        "created_at": "2026-06-25T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/sensitive/access-requests/ - 创建申请

- **方法**：POST
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sensitive_data | int | 是 | 敏感资料 ID |
| reason | string | 是 | 查看原因 |
| project | int | 否 | 关联项目 ID |

```json
{
  "sensitive_data": 1,
  "reason": "办理签证需要核对身份信息"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "访问申请提交成功，等待审批",
  "data": { "id": 1, "status": "pending", "reason": "办理签证需要核对身份信息" }
}
```

### POST /api/v1/sensitive/access-requests/{id}/approve/ - 审批通过

- **方法**：POST
- **权限**：敏感审批人 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 `approve` |
| approval_opinion | string | 否 | 审批意见 |
| expire_hours | int | 否 | 有效时长（小时），默认 1 |

```json
{
  "action": "approve",
  "approval_opinion": "同意",
  "expire_hours": 1
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "审批通过",
  "data": { "id": 1, "status": "approved", "access_expires_at": "2026-06-25T11:00:00+08:00" }
}
```

### POST /api/v1/sensitive/access-requests/{id}/reject/ - 驳回

- **方法**：POST
- **权限**：敏感审批人 / 管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 `reject` |
| approval_opinion | string | 否 | 驳回理由 |

```json
{
  "action": "reject",
  "approval_opinion": "理由不充分，请补充说明"
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "已驳回",
  "data": { "id": 1, "status": "rejected", "approval_opinion": "理由不充分，请补充说明" }
}
```

### POST /api/v1/sensitive/access-requests/{id}/view_data/ - 限时查看明文（写日志）

凭已通过的申请限时查看明文，并写操作日志。

- **方法**：POST
- **权限**：已认证且持有有效审批

**请求参数**：无

**返回示例**：

```json
{
  "code": 0,
  "message": "查看成功，请在有效期内使用并注意明文保密",
  "data": {
    "plaintext": "330106199001011234",
    "sensitive_data_id": 1,
    "sensitive_data_title": "王明身份证",
    "access_expires_at": "2026-06-25T11:00:00+08:00"
  }
}
```

- **备注**：申请未通过或已过期返回 `code: 1003`；模块另提供 `my_requests`、`pending_approve` 子接口。

---

## 通知模块 (notifications)

### GET /api/v1/notifications/ - 通知列表

- **方法**：GET
- **权限**：已认证
- **查询参数**：`is_read`、`category`、`channel`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 10,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "title": "新的贡献待审核",
        "content": "普通成员提交了一条贡献记录，请及时审核",
        "notification_type": "contribution",
        "is_read": false,
        "sender": { "id": 8, "name": "普通成员" },
        "created_at": "2026-06-20T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/notifications/{id}/mark_as_read/ - 标记已读

- **方法**：POST
- **权限**：已认证

**请求参数**：无

**返回示例**：

```json
{
  "code": 0,
  "message": "已标记为已读",
  "data": null
}
```

### POST /api/v1/notifications/mark_all_as_read/ - 全部已读

- **方法**：POST
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "已标记 8 条通知为已读",
  "data": { "count": 8 }
}
```

### GET /api/v1/notifications/unread_count/ - 未读数

- **方法**：GET
- **权限**：已认证

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": { "count": 5 }
}
```

---

## 审计模块 (audit)

> 操作日志查询权限：老师 / 管理员。

### GET /api/v1/audit/operation-logs/ - 日志列表

- **方法**：GET
- **权限**：老师 / 管理员
- **查询参数**：`module`、`operator`、`operation_type`、`is_success`、`start_date`、`end_date`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 100,
    "next": "http://host/api/v1/audit/operation-logs/?page=2&page_size=20",
    "previous": null,
    "current_page": 1,
    "total_pages": 5,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "operator": { "id": 4, "name": "王明" },
        "operation_type": "create",
        "module": "projects",
        "object_type": "Project",
        "object_id": "1",
        "description": "创建项目: 智能办公系统",
        "is_success": true,
        "request_path": "/api/v1/projects/",
        "response_status": 201,
        "created_at": "2026-03-01T10:00:00+08:00"
      }
    ]
  }
}
```

### GET /api/v1/audit/operation-logs/{id}/ - 日志详情

- **方法**：GET
- **权限**：老师 / 管理员

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "operator": { "id": 4, "name": "王明" },
    "operation_type": "create",
    "module": "projects",
    "object_type": "Project",
    "object_id": "1",
    "description": "创建项目: 智能办公系统",
    "is_success": true,
    "request_path": "/api/v1/projects/",
    "request_method": "POST",
    "response_status": 201,
    "ip_address": "192.168.1.100",
    "created_at": "2026-03-01T10:00:00+08:00"
  }
}
```

### GET /api/v1/audit/operation-logs/module_stats/ - 模块统计

- **方法**：GET
- **权限**：老师 / 管理员
- **查询参数**：`days`（统计最近 N 天，默认 30）

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "days": 30,
    "total": 500,
    "module_stats": [
      { "module": "projects", "total": 120, "success_count": 115, "fail_count": 5 },
      { "module": "contributions", "total": 80, "success_count": 78, "fail_count": 2 }
    ],
    "operation_type_stats": [
      { "operation_type": "create", "total": 150 },
      { "operation_type": "update", "total": 200 }
    ]
  }
}
```

### GET /api/v1/audit/operation-logs/recent/ - 最近日志

- **方法**：GET
- **权限**：老师 / 管理员
- **查询参数**：`limit`（条数，默认 20，最大 100）

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 100,
      "operator": { "id": 4, "name": "王明" },
      "operation_type": "update",
      "module": "tasks",
      "description": "更新任务状态",
      "is_success": true,
      "created_at": "2026-06-30T15:00:00+08:00"
    }
  ]
}
```

---

## 导出模块 (exports)

> 导出接口直接返回文件流（非统一 JSON 响应）。参数使用 `file_format` 而非 `format`，避免与 DRF 内容协商冲突。

### GET /api/v1/exports/?type=projects&file_format=xlsx - 导出项目列表

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 导出类型，此处 `projects` |
| file_format | string | 否 | 格式，默认 `xlsx` |

**返回**：Excel 文件流（`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）

- **备注**：表头为「项目名称、项目编号、负责人、当前阶段、状态、开始时间、预计结束」。

### GET /api/v1/exports/?type=finance_budget&file_format=xlsx - 导出经费总表

- **方法**：GET
- **权限**：已认证

**返回**：Excel 文件流。

- **备注**：表头为「项目编号、奖金总额、其他收入、统计周期」。

### GET /api/v1/exports/?type=finance_detail&file_format=xlsx&project_id=1 - 导出经费明细

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `finance_detail` |
| file_format | string | 否 | 默认 `xlsx` |
| project_id | int | 是 | 项目 ID |

**返回**：Excel 文件流。

### GET /api/v1/exports/?type=tasks&file_format=xlsx - 导出任务清单

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `tasks` |
| file_format | string | 否 | 默认 `xlsx` |
| project_id | int | 否 | 项目 ID（可选，按项目筛选） |

**返回**：Excel 文件流。

- **备注**：表头为「任务标题、项目编号、指派给、截止时间」。

### GET /api/v1/exports/?type=contributions&file_format=xlsx&project_id=1 - 导出贡献记录

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `contributions` |
| file_format | string | 否 | 默认 `xlsx` |
| project_id | int | 是 | 项目 ID |

**返回**：Excel 文件流。

- **备注**：表头为「项目编号、贡献人、贡献类型、贡献内容、权重、统计周期」。

### GET /api/v1/exports/?type=ip_applications&file_format=xlsx - 导出知识产权

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `ip_applications` |
| file_format | string | 否 | 默认 `xlsx` |

**返回**：Excel 文件流。

- **备注**：表头为「成果名称、内部编号、成果类型、关联项目编号、主导撰写人」。

### GET /api/v1/exports/?type=project_report&file_format=docx&project_id=1 - 项目报告 Word

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `project_report` |
| file_format | string | 是 | `docx` |
| project_id | int | 是 | 项目 ID |

**返回**：Word 文档流。

### GET /api/v1/exports/?type=project_report&file_format=pdf&project_id=1 - 项目报告 PDF

- **方法**：GET
- **权限**：已认证

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | `project_report` |
| file_format | string | 是 | `pdf` |
| project_id | int | 是 | 项目 ID |

**返回**：PDF 文件流。

- **备注**：PDF 由 ReportLab 与 CID 中文字体生成，不依赖 GTK。另提供 `GET /api/v1/exports/template/?type=<类型>` 下载空白导入模板。

---

## 集成模块 (integrations)

> 全部接口仅限系统管理员。

### GET /api/v1/integrations/configs/ - 配置列表

- **方法**：GET
- **权限**：管理员
- **查询参数**：`provider`、`enabled`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 2,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "name": "企业微信通知",
        "provider": "wecom",
        "app_id": "ww123456",
        "enabled": true,
        "created_by": { "id": 1, "name": "系统管理员" },
        "created_at": "2026-06-01T10:00:00+08:00"
      }
    ]
  }
}
```

### POST /api/v1/integrations/configs/ - 创建配置

- **方法**：POST
- **权限**：管理员

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 配置名称 |
| provider | string | 是 | 提供商 wecom/dingtalk/feishu/email 等 |
| app_id | string | 否 | 应用 ID |
| app_secret | string | 否 | 应用密钥 |
| enabled | bool | 否 | 是否启用 |

```json
{
  "name": "企业微信通知",
  "provider": "wecom",
  "app_id": "ww123456",
  "app_secret": "secret_xxx",
  "enabled": true
}
```

**返回示例**：

```json
{
  "code": 0,
  "message": "集成配置创建成功",
  "data": { "id": 1, "name": "企业微信通知", "provider": "wecom", "enabled": true }
}
```

- **备注**：创建/更新/删除均自动写操作日志。

### GET /api/v1/integrations/logs/ - 日志列表

- **方法**：GET
- **权限**：管理员
- **查询参数**：`provider`、`status`、`event_type`、`search`、`ordering`

**返回示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 50,
    "next": null,
    "previous": null,
    "current_page": 1,
    "total_pages": 3,
    "page_size": 20,
    "results": [
      {
        "id": 1,
        "provider": "wecom",
        "event_type": "send_message",
        "target": "user_8",
        "status": "success",
        "created_at": "2026-06-20T10:00:00+08:00"
      }
    ]
  }
}
```

---

> 文档版本：v1.0
> 维护者：团队管理软件项目组
