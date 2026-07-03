# Codex 修复后下一步：验收、V2 演示数据、版本冻结

## 1. 先验收 Codex 的 P0 前端可用性回归修复

Codex 已经完成：

- 移除全局 px-to-vw；
- 修复 Dashboard 卡片巨大化；
- 修复 PC 内容区压缩；
- 修复移动端初始断点；
- 修复金额格式化导致的 `¥NaN`；
- `npx vue-tsc --noEmit` 通过；
- `npm run build` 通过；
- `python manage.py check` 因当前环境缺 `celery` 依赖未真正执行到 Django 检查阶段。

你本地应先补依赖：

```bash
cd backend
pip install -r requirements/dev.txt
python manage.py check
```

如果没有 `requirements/dev.txt`，使用项目实际 requirements 文件。

## 2. 导入 V2 多赛事并行演示数据

复制文件：

```powershell
Copy-Item .\seed_competition_demo.py .\backend\apps\users\management\commands\seed_competition_demo.py -Force
New-Item -ItemType Directory -Force .\backend\seed_assets\competition_demo_files
Copy-Item .\assets\* .\backend\seed_assets\competition_demo_files\ -Recurse -Force
```

运行：

```bash
cd backend
python manage.py migrate
python manage.py seed_competition_demo --clean --force
```

## 3. 必须截图验收

PC 端：

- 登录页；
- Dashboard；
- 项目列表；
- 项目详情；
- 比赛列表；
- 经费总览；
- 文件资料；
- 贡献记录；
- 成员排序；
- 知识产权；
- 敏感资料；
- 通知中心；
- 操作日志。

移动端 375px：

- 登录页；
- Dashboard；
- 项目页；
- 比赛页；
- 经费页；
- 文件页。

重点确认：

```text
不出现 ¥NaN
不出现 undefined
不出现表头冒号
不出现标题逐字竖排
不出现内容区被压缩
移动端不显示 PC 左侧栏
Dashboard 卡片不巨大化
```

## 4. 冻结版本

验收通过后建议冻结：

```text
v0.8.2-ui-recovery
```

含义：P3 第一批前端回归后的可用性恢复版本。

不要在这个版本里继续做大规模美化，也不要把“日历/Gantt 时间线模块”混进来。

## 5. 后续再开 P3.5/P4

下一阶段推荐：

```text
P3.5：项目日历与横向项目历程时间线模块
```

这一模块应独立新增页面和只读聚合接口，不污染现有 Dashboard、项目详情、比赛、经费等稳定页面。
