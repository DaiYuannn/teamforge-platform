# TRAE Work：团队管理平台全功能开发、自动测试与最终验收总任务

你现在接手的是“团队管理软件 / 团队项目管理平台”的当前主线项目。不要使用旧 GitHub 仓库 `TeamFilePermissionCenter` 作为主线，也暂时不要处理 Docker。

本次任务不是只修复现有 Bug，也不是只补几个页面，而是：

1. 对当前成果做第一次全量自动化验收；
2. 修复当前所有 Bug 和前后端契约问题；
3. 补齐所有未完成模块；
4. 实现《团队管理平台_全功能制作与验收总清单.md》中列出的全部 M、P、N 功能；
5. 每个功能开发过程中持续执行“编写代码—自动测试—内置浏览器验收—Debug—回归测试”循环；
6. 完成新增制作验收；
7. 最后在干净环境中完成整个系统的最终全量验收。

请先读取项目根目录以及：

```text
团队管理平台_全功能制作与验收总清单.md
VERSION.md
CHANGELOG.md
README.md
```

将总清单中的 M01—M10、P01—P20、N01—N62 全部纳入正式开发计划。不要擅自删除或跳过。

---

## 一、不可改变的契约

### 用户

使用：

```text
name
global_role
global_role_display
```

不得未经正式模型设计擅自使用旧字段：

```text
real_name
role
```

### 文件

使用：

```text
level
level_display
```

枚举：

```text
public
internal
sensitive
```

不得使用旧字段：

```text
permission
```

### 通知筛选

使用：

```text
category
```

### 操作日志筛选

使用：

```text
operator
start_date
end_date
```

### 敏感资料申请

使用：

```text
sensitive_data
usage_scenario
is_download
```

### 敏感资料审批

使用：

```text
action
approval_opinion
expire_hours
```

### 导入

使用：

```text
field_mapping
error_rows
error_details
```

不得为了兼容错误前端而在后端增加重复字段。

---

## 二、不可破坏的业务规则

1. 不改变 JWT 登录和 token 结构。
2. 不降低后端权限。
3. 普通成员不能进入系统管理页面。
4. 经费明细和票据对所有登录成员公开。
5. 敏感资料必须经过申请、审批、限时查看或下载并记录日志。
6. 公共页面不得泄露内部或敏感数据。
7. 权限必须由后端执行，不能只隐藏按钮。
8. 暂不使用 Docker。
9. 不进行大范围无关视觉美化。
10. 不以删除测试、降低断言、放宽权限或写死数据的方式让测试通过。

---

# 三、必须严格执行的总顺序

```text
阶段 0：冻结、盘点和第一次全量自动化验收
阶段 1：修复当前所有 P0/P1/P2/P3 可用性问题和 P01—P20
阶段 2：补齐 M01—M10
阶段 3：实现 N01—N12
阶段 4：实现 N13—N25
阶段 5：实现 N26—N33
阶段 6：实现 N34—N39
阶段 7：实现 N40—N47
阶段 8：实现 N48—N55
阶段 9：实现 N56—N62
阶段 10：制作验收
阶段 11：干净环境最终全量验收
```

阶段顺序可以因技术依赖小范围调整，但不得跳过任何功能。调整必须记录原因。

---

# 四、优先使用 TRAE Work 内置浏览器

所有可以通过浏览器完成的验收必须由 TRAE Work 自动操作内置浏览器完成，尽量减少用户人工测试。

自动完成：

- 启动并打开系统
- 登录不同角色
- 导航页面
- 填写表单
- 新建、编辑、删除
- 审批、驳回、撤回、回滚
- 上传、预览、下载
- 导入、导出
- 搜索、筛选、分页
- 刷新和重新登录
- 直接 URL 越权测试
- 移动端尺寸切换
- Console 和 Network 检查
- 截图 QA
- 数据持久化验证

不能把页面验收大量留给用户手动完成。

内置浏览器临时操作之外，还必须将高价值流程固化成 Playwright 或项目现有 E2E，保证可以重复执行。

---

# 五、阶段 0：第一次全量验收

## 5.1 项目盘点

记录：

- Git 分支、commit、工作区状态
- 前端路由和页面
- Django 应用、模型、API
- 角色和权限
- migration
- 测试资产
- TODO/FIXME/占位页/空按钮
- README、VERSION、CHANGELOG 声称完成的功能
- 代码实际完成状态
- 密钥、dump、media、备份和缓存
- 依赖版本和启动方式

建立测试分支和备份点。

## 5.2 建立测试体系

后端：

```text
pytest
pytest-django
DRF APIClient
coverage
```

前端：

```text
Vitest
Vue Test Utils
```

E2E：

```text
Playwright 或项目现有工具
TRAE Work 内置浏览器
```

建立：

- fixture/factory
- 测试数据管理命令
- mock Webhook
- 自动截图
- 测试数据库重建
- 一键全量测试命令

## 5.3 静态检查

至少执行：

```bash
python -m compileall backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
pytest
pytest --cov
npx vue-tsc --noEmit
npm run test
npm run build
npm run test:e2e
```

实际命令以最终配置为准。

## 5.4 第一次浏览器全量验收

覆盖：

- 登录和 token
- 权限矩阵
- Dashboard
- 项目
- 比赛
- 任务
- 成员
- 经费
- 文件
- 贡献
- 排序异议
- 知识产权
- 敏感资料
- 通知
- 日志
- 导入导出
- 时间线
- 日历/Gantt
- 归档复盘
- 公共页面
- 文件预览
- 机器人/Webhook
- 定时任务
- 报告
- 个人中心和偏好
- PC 和移动端

账号至少覆盖：

- sys_admin
- teacher
- project leader
- sens_approver
- member
- 未登录访客

尺寸至少覆盖：

```text
1366×768
1440×900
1920×1080
375×812
390×844
430×932
```

## 5.5 生成第一轮报告

生成：

```text
docs/testing/00_BASELINE_TEST_PLAN.md
docs/testing/00_BASELINE_TEST_MATRIX.md
docs/testing/00_BASELINE_REPORT.md
docs/testing/00_BASELINE_BUGS.md
docs/testing/00_SCREENSHOT_INDEX.md
docs/testing/00_IMPLEMENTATION_BACKLOG.md
```

不要在第一轮结束后停止，直接进入修复和开发。

---

# 六、强制代码—测试—Debug 循环

对每一个 M、P、N 功能，严格执行以下循环：

```text
1. 阅读当前代码、模型、接口、页面和历史文档
2. 明确需求、边界、权限和验收标准
3. 编写设计记录和数据契约
4. 先建立失败测试，或至少同时编写测试
5. 编写后端模型、migration、服务、序列化器、API、权限
6. 执行后端相关测试
7. 失败则定位根因并修改，直到通过
8. 编写前端类型、API、store、组件、页面和交互
9. 执行 vue-tsc、Vitest 和组件测试
10. 失败则继续 Debug，直到通过
11. 编写 Playwright/E2E
12. 使用 TRAE Work 内置浏览器执行真实操作
13. 检查页面、Console、Network、API 响应和数据库持久化
14. 刷新和重新登录后复查
15. 测试非法输入、空数据、权限、边界和并发/重复操作
16. 测试 PC 和移动端
17. 保存截图
18. 如发现 Bug，自动复现、定位、最小修改、再次测试
19. 执行相邻模块回归
20. 执行当前批次全量回归
21. 更新文档、测试矩阵、CHANGELOG
22. 建立 Git 检查点
23. 当前功能全部通过后，才允许进入下一个功能
```

任何一步失败，不得标记完成，也不得跳到下一个功能。

禁止：

- 删除失败测试
- 降低断言
- 用 try/except 吞掉异常
- 写死返回值
- 放宽权限
- 关闭认证或日志
- 仅隐藏失效按钮
- 页面显示成功但后端未保存
- 只测试管理员
- 只测试正常流程

---

# 七、各阶段开发和验收

## 阶段 1：修复 P01—P20

优先处理前后端契约、数据保存、权限、安全、导入导出、集成、移动端、Git 和发布包问题。

每完成一个 P 项：

- 后端测试
- 前端测试
- E2E
- 内置浏览器
- 相邻模块回归
- 更新报告

P01—P20 全部完成后执行一次完整回归。

## 阶段 2：补齐 M01—M10

特别注意：

- M01 是后续全部功能的基础
- M02 文件版本管理必须形成完整 API 和页面
- M03/M04 公告与实时通知要有降级机制
- M05 账号安全不能破坏 JWT
- M07/M09 搜索应进行权限过滤
- M08 回收站必须保留审计
- M09/M10 与归档、历史项目联动

阶段完成后执行专项验收和全量回归。

## 阶段 3：N01—N12

实现任务、里程碑、风险、模板、统一待办、文件夹、版本和公告。

## 阶段 4：N13—N25

实现成员、比赛、经费、OCR、贡献规则和可视化。

OCR 如需第三方服务，必须提供：

- 可替换 provider
- mock 测试
- 本地失败回退
- 真实外部联调状态说明

## 阶段 5：N26—N33

实现动态流、讨论区、知识库、全文搜索、Office 预览、文件哈希、水印和分享链接。

Office 预览和全文搜索如依赖外部服务，必须提供本地可测试方案和清晰降级。

## 阶段 6：N34—N39

实现双因素认证、登录安全、自定义角色权限、敏感确认、备份恢复和安全扫描。

这是高风险阶段，必须重点做：

- 权限回归
- token 撤销
- 数据隔离
- 恢复演练
- 文件安全
- 防绕过

## 阶段 7：N40—N47

实现多团队、自定义审批流、自定义表单、第三方登录、外部平台、Git 集成、日历同步、开放 API/Webhook。

必须先完成架构设计和数据迁移方案，确保：

- 多租户数据隔离
- 旧数据迁移
- 权限兼容
- 审批历史不可丢失
- 外部服务可 mock
- 开放 API 有认证、限流和审计

## 阶段 8：N48—N55

实现 Dashboard、报表、定时报表、风险预测、健康度、智能周报、智能复盘和材料检查。

智能功能必须：

- 可解释
- 可关闭
- 不直接覆盖人工数据
- 输出注明自动生成
- 无模型服务时有规则引擎或 mock
- 测试中不得依赖不可控网络调用
- 不泄露敏感数据

## 阶段 9：N56—N62

实现 CI、错误监控、健康检查、性能优化、OpenAPI、a11y、国际化和深色模式。

CI 至少执行：

- 后端测试
- 前端测试
- type-check
- build
- E2E 核心集
- 覆盖率
- 密钥和依赖安全扫描

---

# 八、制作验收

全部 M、P、N 完成后，进行一次制作验收。

重点：

- 所有新增功能
- 所有修改功能
- 新旧模块衔接
- migration
- 权限
- 数据持久化
- PC/移动端
- 错误和边界
- 外部服务 mock
- 回归

生成：

```text
docs/testing/01_DEVELOPMENT_ACCEPTANCE_PLAN.md
docs/testing/01_DEVELOPMENT_ACCEPTANCE_MATRIX.md
docs/testing/01_DEVELOPMENT_ACCEPTANCE_REPORT.md
docs/testing/01_DEVELOPMENT_BUGS.md
docs/testing/01_DEVELOPMENT_SCREENSHOTS.md
```

制作验收发现任何 Bug，必须继续代码—测试—Debug 循环，直到无 P0/P1/P2。

---

# 九、最终全量验收

制作验收通过后，模拟干净环境：

1. 记录 Git commit
2. 清理前端缓存
3. 新测试数据库
4. 重新 migration
5. 重新 fixture
6. 新浏览器会话
7. 清理 cookie/localStorage/sessionStorage
8. 不复用 token
9. 重启前后端
10. 从登录开始执行全部流程

重新执行：

- 所有静态检查
- 所有后端测试
- 所有前端测试
- 所有 E2E
- 所有角色
- 所有模块
- 所有 PC/移动端尺寸
- 所有权限
- 所有文件、导入导出、敏感资料、报告、通知、日志、外部集成 mock
- 所有 M、P、N 功能

发现 Bug 后仍需继续：

```text
复现
→ 根因
→ 修改
→ Debug
→ 相关测试
→ 相邻回归
→ 最终全量重跑
```

不能只记录后结束。

生成：

```text
docs/testing/02_FINAL_TEST_PLAN.md
docs/testing/02_FINAL_TEST_MATRIX.md
docs/testing/02_FINAL_REPORT.md
docs/testing/02_FINAL_SCREENSHOT_INDEX.md
docs/testing/02_RELEASE_READINESS.md
```

---

# 十、版本和完成标准

只有同时满足以下条件，才能标记 stable：

1. M01—M10 完成
2. P01—P20 完成
3. N01—N62 完成
4. 静态检查通过
5. migration 通过
6. pytest 全部通过
7. 前端测试全部通过
8. E2E 全部通过
9. 内置浏览器全量验收通过
10. 所有角色权限通过
11. PC 和移动端通过
12. 无 P0/P1/P2
13. 核心流程无 P3 可用性问题
14. 无 NaN、undefined、假保存、重复货币符号
15. 敏感资料、文件分享、公共页面无越权和泄露
16. 自动化测试可重复执行
17. 外部服务 mock 与真实联调状态明确区分
18. 文档与实际一致
19. Git 和发布包无密钥、数据库、media、缓存
20. 最终报告明确通过

未满足时保留候选版本，不得提前改为 stable。

---

# 十一、最终汇报

全部完成后一次性汇报：

- 最终版本、分支、commit、环境
- 第一次全量验收结果
- P/M/N 各阶段完成情况
- 编写和修改的核心模块
- Debug 和回归次数
- 后端测试、前端测试、E2E、浏览器自动测试数量
- 覆盖率
- 截图数量
- PC/移动端结果
- 权限矩阵结果
- 外部服务 mock 和真实联调状态
- 仍未完成内容
- 发布建议

最终结论只能是：

```text
通过最终全量验收，可以冻结为稳定版本
```

或：

```text
未通过最终全量验收，继续保留候选版本
```

不能使用模糊表述。

现在开始执行。不要只输出方案，也不要在某一阶段后停止。先完成当前版本第一次全量自动化验收，然后持续实现总清单中的全部功能；每个功能严格执行代码、测试、内置浏览器、Debug 和回归循环；制作验收通过后，再完成最终全量验收。
