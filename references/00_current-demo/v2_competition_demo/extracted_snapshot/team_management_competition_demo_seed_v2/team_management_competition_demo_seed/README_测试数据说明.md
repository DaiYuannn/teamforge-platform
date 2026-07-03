# 团队项目管理平台 V2 演示数据包

这是根据“每组 5-8 人、每个项目至少同时参加 3 个比赛、小挑/大挑全覆盖、数字中国只安排部分项目参加”的要求重新整理的测试数据。

## 文件结构

```text
seed_competition_demo.py
assets/
  project_plans/              # 每个项目真实 DOCX/PDF 计划书
  roadshow_placeholders/      # 每个项目 PPT 路演、Word 路演稿占位文件
  receipts/                   # 演示票据图片
V2_比赛矩阵与时间线说明.md
CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md
NEXT_STEPS_AFTER_CODEX.md
```

## 账号

```text
系统管理员：admin@demo.com / admin123456
指导老师1：teacher1@demo.com / teacher123456
指导老师2：teacher2@demo.com / teacher123456
敏感审批人：approver@demo.com / approver123456
六个项目负责人：leader1~leader6@demo.com / leader123456
普通协作成员：member1~member8@demo.com / member123456
```

## 数据规模

- 6 个项目；
- 6 个项目负责人；
- 每组 6-8 人；
- 22 条项目-比赛参赛记录；
- 每个项目至少 3 条参赛线；
- 小挑/大挑全项目参加；
- 数字中国 2 个项目参加；
- 覆盖任务、经费、票据、文件、文件版本、贡献、排序、异议、知识产权、敏感资料、通知、操作日志、导入记录。

## 安装方式

将 `seed_competition_demo.py` 放到：

```text
backend/apps/users/management/commands/seed_competition_demo.py
```

将 `assets` 内容复制到：

```text
backend/seed_assets/competition_demo_files/
```

运行：

```bash
cd backend
python manage.py seed_competition_demo --clean --force
```

## 注意

1. 这套数据用于演示系统功能，不是正式参赛日程表。
2. 不会修改后端模型、权限、登录 token、敏感资料流程和经费公开规则。
3. 日历/Gantt 横向项目历程模块当前还没有真正完成，详见 `CALENDAR_TIMELINE_MODULE_GAP_AND_CODEX_PROMPT.md`。
