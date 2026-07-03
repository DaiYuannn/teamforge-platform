# 日历/Gantt 时间线模块现状判断与后续 Codex 任务

## 结论

你最初设想的模块是：

> 页面上方可以是日历/筛选，下方用一根根横线展示每个项目从立项到比赛、结项的时间跨度；鼠标悬停到某一段时间或某一天时，可以展示人员变化、文件变化、方向变化、比赛节点、经费节点、知识产权节点等信息。

当前项目里不能算已经完成。

## 当前源码现状

1. `frontend/package.json` 已安装：
   - `@fullcalendar/core`
   - `@fullcalendar/daygrid`
   - `@fullcalendar/interaction`
   - `@fullcalendar/vue3`

2. 但是前端源码中没有独立的 `ProjectCalendarView.vue` / `TimelineGanttView.vue` / `ProjectTimelineView.vue` 这类页面。

3. Dashboard 里有“比赛节点日历”的标题，但实际使用的是 Element Plus 的 `el-timeline` 纵向时间线，不是 FullCalendar，也不是横向 Gantt。

4. Dashboard 前端计算 `dashboardData.calendar_events`，但后端 `apps/dashboard/views.py` 当前返回的数据结构里没有 `calendar_events` 字段。因此这一块最多算“前端预留/半成品”，不是闭环功能。

## 建议不要现在立刻做

当前刚完成 P0 前端回归修复，应该先完成：

1. Codex 修复验收；
2. V2 演示数据导入；
3. Dashboard / 项目 / 比赛 / 经费 / 移动端截图确认；
4. 冻结 `v0.8.2-ui-recovery`。

日历/Gantt 时间线模块建议作为 `P3.5` 或 `P4`，不要混入当前修复分支。

## 后续给 Codex 的任务提示词

```text
你现在要新增“项目日历与项目历程时间线”模块，但不要破坏现有 P0/P1/P2 功能和 v0.8.2-ui-recovery 的前端稳定布局。

目标：实现一个项目级日历/Gantt 页面，用于展示多个项目从立项、材料准备、比赛报名、校赛、市赛、省赛、国赛、获奖、结项的时间跨度。页面上方为筛选区，下方为横向时间轴，每个项目一根或多根横线；鼠标悬停到某一段时间或某个节点时，展示该时间段内的人员变化、文件变化、方向变化、比赛节点、经费节点、知识产权节点和操作日志摘要。

技术边界：
1. 不修改登录 token、权限规则、敏感资料流程、经费公开规则。
2. 不改已有接口字段语义。
3. 可以新增后端只读聚合接口，例如 `/api/v1/dashboard/timeline/` 或 `/api/v1/projects/timeline/`。
4. 前端优先新增独立页面和组件，不污染全局样式，不再使用全局 px-to-vw。
5. 使用局部 scoped 样式。

后端聚合来源：
- Project.start_date / planned_end_date / current_stage / stage_logs；
- Competition 的 register_date、material_deadline、review_date、defense_date、school_date、city_date、province_date、national_date、result_date；
- ProjectMember.joined_at 和 OperationLog 中 ProjectMember 相关日志；
- FileAsset / FileVersion 的上传和版本记录；
- FinanceExpense / FinanceReceipt 的支出和票据节点；
- IntellectualPropertyApplication / IPReturnRecord / IPMaterialVersion；
- SensitiveAccessRequest；
- OperationLog 中带 timeline_event_type 或 module 的关键日志。

前端页面建议：
- 路由：`/timeline` 或 `/projects/timeline`
- 组件：`ProjectTimelineGantt.vue`
- 筛选：项目、比赛、阶段、负责人、时间范围、事件类型
- 展示：
  - 每个项目一行；
  - 主线条显示项目整体周期；
  - 比赛线条显示每条赛事线；
  - 节点点位显示材料截止、网评、答辩、结果公布；
  - hover popover 显示事件清单；
  - 点击节点跳转项目详情/比赛详情/文件详情。

验收：
1. `npx vue-tsc --noEmit`
2. `npm run build`
3. `python manage.py check`
4. 截图验证 PC 端 1366px 与移动端 375px。
```
