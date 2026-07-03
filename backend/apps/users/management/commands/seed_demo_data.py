"""
生成完整演示数据的管理命令

用法:
    python manage.py seed_demo_data          # 生成演示数据（带确认提示）
    python manage.py seed_demo_data --clean  # 先清除所有演示数据再重新生成
    python manage.py seed_demo_data --force  # 跳过确认提示

数据概览:
    - 账号: 8 个固定账号 + 45 个普通成员
    - 项目: 10 个（2 个已关闭）
    - 比赛: 5 个
    - 任务: ~40 个（todo/doing/pending_review/done/overdue 分布）
    - 经费: 每项目 1 条预算 + 2~3 条支出
    - 技能标签: 15 个 + 部分成员技能
    - 灵活工时: ~15 条
    - 贡献记录: 15 条
    - 成员排序: 2 个项目（1 draft / 1 confirmed）+ 2 条异议
    - 知识产权申请: 5 个（含退回记录、贡献人、异议）
    - 敏感资料: 3 条 + 2 条访问申请
    - 通知: 10 条
    - 操作日志: 20 条
"""
import calendar
import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.users.models import User
from apps.projects.models import Project, ProjectMember
from apps.competitions.models import Competition
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget, FinanceExpense, FinanceReceipt
from apps.members.models import SkillTag, MemberSkill, FlexibleWorkSchedule
from apps.contributions.models import (
    Contribution, MemberRanking, RankingObjection,
)
from apps.intellectual_property.models import (
    IntellectualPropertyApplication, IPApplicationContributor,
    IPReturnRecord, IPObjection,
)
from apps.sensitive.models import SensitiveData, SensitiveAccessRequest
from apps.notifications.models import Notification
from apps.audit.models import OperationLog


# ============================================================================
# 中文姓名 / 数据池
# ============================================================================
SURNAMES = [
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙',
    '胡', '朱', '高', '林', '何', '郭', '马', '罗', '梁', '宋', '郑', '谢',
    '韩', '唐', '冯', '于', '董', '萧', '程', '曹', '袁', '邓', '许', '傅',
    '沈', '曾', '彭', '吕', '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛',
    '叶', '阎', '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
    '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆', '郝', '孔',
    '白', '崔', '康', '毛', '邱', '秦', '江', '史', '顾', '侯', '邵', '孟',
    '龙', '万', '段', '雷', '钱', '汤', '尹', '黎', '易', '常', '武', '乔',
    '贺', '赖', '龚', '文',
]
GIVEN_CHARS = [
    '伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳',
    '杰', '娟', '涛', '明', '超', '霞', '平', '刚', '华', '建', '晓', '志',
    '俊', '浩', '然', '涵', '欣', '怡', '思', '远', '雨', '泽', '宇', '轩',
    '嘉', '梦', '琪', '雅', '婷', '慧', '东', '燕', '晨', '曦', '佳', '瑞',
    '鑫', '鹏', '飞', '雪', '梅', '兰', '虎', '龙', '文', '博', '宁', '辉',
    '颖', '妍', '薇', '倩', '楠', '璐', '玥', '悦', '昕', '彤', '瑶', '洁',
]

GRADES = ['大一', '大二', '大三', '大四', '研一', '研二']
MAJORS = [
    '计算机科学', '软件工程', '电子信息', '人工智能',
    '数据科学', '网络安全', '通信工程',
]

PROJECT_DATA = [
    {
        'name': '智能校园导览系统',
        'intro': '基于移动端定位与AR技术的校园导览系统，为新生和访客提供室内外一体化导航、'
                 '景点语音讲解和实时活动指引，支持多语言与无障碍模式。',
    },
    {
        'name': '基于深度学习的医学影像辅助诊断平台',
        'intro': '利用卷积神经网络对CT/MRI影像进行病灶检测与分类，辅助医生提升诊断效率与准确率，'
                 '平台提供模型训练、推理服务和医生复核工作流。',
    },
    {
        'name': '校园二手交易小程序',
        'intro': '面向在校学生的二手物品交易小程序，支持发布、求购、信用评价和线下交接预约，'
                 '保障交易安全与便捷。',
    },
    {
        'name': '农产品溯源区块链平台',
        'intro': '基于联盟链的农产品全链路溯源平台，记录种植、加工、物流、销售各环节关键数据，'
                 '消费者扫码即可查验真伪与质量信息。',
    },
    {
        'name': '智能安防监控系统',
        'intro': '结合边缘计算与视频分析的智能安防系统，实现人员闯入检测、异常行为识别和告警推送，'
                 '适用于校园和园区场景。',
    },
    {
        'name': '在线协同文档编辑器',
        'intro': '支持多人实时协同编辑的在线文档工具，基于CRDT算法实现冲突自动合并，'
                 '提供评论、版本回溯和权限管理。',
    },
    {
        'name': '基于大模型的智能客服系统',
        'intro': '集成大语言模型的智能客服系统，支持多轮对话、知识库检索增强和工单流转，'
                 '可快速接入校园各类业务咨询场景。',
    },
    {
        'name': '校园活动管理平台',
        'intro': '一站式校园活动管理平台，覆盖活动发布、报名、签到、学分认定和数据分析，'
                 '面向社团、学院和校级活动。',
    },
    {
        'name': '环境监测物联网系统',
        'intro': '基于LoRa/WiFi的环境监测物联网系统，实时采集温湿度、PM2.5、噪声等数据，'
                 '通过可视化大屏展示并支持阈值告警。',
    },
    {
        'name': '学生学业预警分析系统',
        'intro': '整合教务数据与学习行为数据，运用机器学习模型识别学业困难学生并自动预警，'
                 '辅助辅导员及时干预帮扶。',
    },
]

COMPETITION_DATA = [
    {
        'name': '中国国际大学生创新大赛（互联网+）',
        'comp_type': '创新创业',
        'level': Competition.Level.NATIONAL,
        'organizer': '教育部',
        'status': Competition.Status.ONGOING,
    },
    {
        'name': '挑战杯大学生课外学术科技作品竞赛',
        'comp_type': '学术科技',
        'level': Competition.Level.PROVINCE,
        'organizer': '共青团中央',
        'status': Competition.Status.COMPLETED,
    },
    {
        'name': '蓝桥杯全国软件和信息技术专业人才大赛',
        'comp_type': '程序设计',
        'level': Competition.Level.CITY,
        'organizer': '工业和信息化部',
        'status': Competition.Status.PREPARING,
    },
    {
        'name': '中国大学生计算机设计大赛',
        'comp_type': '计算机设计',
        'level': Competition.Level.SCHOOL,
        'organizer': '教育部高等学校计算机类专业教指委',
        'status': Competition.Status.ONGOING,
    },
    {
        'name': '全国大学生数学建模竞赛',
        'comp_type': '数学建模',
        'level': Competition.Level.NATIONAL,
        'organizer': '中国工业与应用数学学会',
        'status': Competition.Status.COMPLETED,
    },
]

# 15 个技能标签
SKILL_NAMES = [
    '前端', '后端', 'UI设计', '文档撰写', 'PPT制作', '答辩', '绘图',
    '视频制作', '数据整理', '算法', '实验', '机械设计', '财务整理',
    '比赛申报', '项目统筹',
]


def gen_chinese_name(used):
    """生成一个未使用过的中文姓名"""
    for _ in range(200):
        surname = random.choice(SURNAMES)
        length = random.randint(1, 2)
        given = ''.join(random.choice(GIVEN_CHARS) for _ in range(length))
        name = surname + given
        if name not in used:
            used.add(name)
            return name
    # 兜底：姓名 + 序号
    name = '同学' + str(len(used) + 1)
    used.add(name)
    return name


def gen_phone():
    """生成一个随机手机号（演示用）"""
    second = random.choice(['3', '5', '7', '8', '9'])
    tail = ''.join(str(random.randint(0, 9)) for _ in range(9))
    return '1' + second + tail


class Command(BaseCommand):
    """生成完整演示数据"""

    help = '生成完整的团队管理软件演示数据（账号、项目、任务、经费、知识产权等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            dest='clean',
            default=False,
            help='先清除所有演示数据再重新生成',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            default=False,
            help='跳过确认提示',
        )

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        random.seed(42)  # 固定随机种子，保证可复现

        clean = options['clean']
        force = options['force']

        # 重复运行保护：已存在演示数据且未指定 --clean 时提示
        if not clean and User.objects.filter(email__endswith='@demo.com').exists():
            self.stdout.write(self.style.ERROR(
                '检测到数据库中已存在演示数据（@demo.com 账号）。'
                '请使用 --clean 参数清除后重新生成。'
            ))
            return

        if not force:
            tip = '即将生成大量演示数据' + ('（会先清除现有演示数据）' if clean else '')
            confirm = input(f'{tip}，是否继续？[y/N]: ')
            if confirm.strip().lower() not in ('y', 'yes'):
                self.stdout.write(self.style.WARNING('已取消操作。'))
                return

        try:
            with transaction.atomic():
                if clean:
                    self.clean_demo_data()

                self.stdout.write(self.style.MIGRATE_HEADING('开始生成演示数据...'))

                # 容器，保存生成结果供后续步骤引用
                self.users = {}
                self.members = []
                self.leaders = []
                self.teachers = []
                self.projects = []
                self.project_members = {}  # project -> [users]

                self.create_users()
                self.create_projects()
                self.create_competitions()
                self.create_tasks()
                self.create_finance()
                self.create_skills()
                self.create_work_schedules()
                self.create_contributions()
                self.create_rankings()
                self.create_ip_applications()
                self.create_sensitive_data()
                self.create_sensitive_requests()
                self.create_notifications()
                self.create_operation_logs()

            self.stdout.write(self.style.SUCCESS('\n========== 演示数据生成完成 =========='))
            self.print_account_summary()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n生成失败，已回滚: {e}'))
            raise

    # ------------------------------------------------------------------
    # 账号
    # ------------------------------------------------------------------
    def _make_user(self, email, username, password, name, role,
                   grade='', major='', is_student=True,
                   is_staff=False, is_superuser=False, phone=''):
        user = User(
            email=email, username=username, name=name,
            global_role=role, grade=grade, major=major,
            is_student=is_student, is_staff=is_staff,
            is_superuser=is_superuser, phone=phone or gen_phone(),
        )
        user.set_password(password)
        user.save()
        return user

    def create_users(self):
        self.stdout.write('-> 创建账号...')
        U = User.GlobalRole

        self.users['admin'] = self._make_user(
            'admin@demo.com', 'admin', 'admin123456', '系统管理员',
            U.SYS_ADMIN, is_student=False, is_staff=True, is_superuser=True,
            phone='13800000000',
        )
        self.users['teacher1'] = self._make_user(
            'teacher1@demo.com', 'teacher1', 'teacher123456', '张老师',
            U.TEACHER, is_student=False, is_staff=True, major='计算机科学',
            phone='13800000001',
        )
        self.users['teacher2'] = self._make_user(
            'teacher2@demo.com', 'teacher2', 'teacher123456', '李老师',
            U.TEACHER, is_student=False, is_staff=True, major='软件工程',
            phone='13800000002',
        )
        self.users['leader1'] = self._make_user(
            'leader1@demo.com', 'leader1', 'leader123456', '王明',
            U.MEMBER, grade='研二', major='计算机科学', phone='13800000003',
        )
        self.users['leader2'] = self._make_user(
            'leader2@demo.com', 'leader2', 'leader123456', '赵芳',
            U.MEMBER, grade='研一', major='软件工程', phone='13800000004',
        )
        self.users['leader3'] = self._make_user(
            'leader3@demo.com', 'leader3', 'leader123456', '刘强',
            U.MEMBER, grade='大三', major='电子信息', phone='13800000005',
        )
        self.users['approver'] = self._make_user(
            'approver@demo.com', 'approver', 'approver123456', '审批员陈姐',
            U.SENS_APPROVER, is_student=False, is_staff=True,
            phone='13800000006',
        )

        self.leaders = [self.users['leader1'], self.users['leader2'], self.users['leader3']]
        self.teachers = [self.users['teacher1'], self.users['teacher2']]

        used_names = {'系统管理员', '张老师', '李老师', '王明', '赵芳', '刘强', '审批员陈姐'}
        for i in range(1, 46):
            email = f'member{i}@demo.com'
            username = f'member{i}'
            name = gen_chinese_name(used_names)
            user = self._make_user(
                email, username, 'member123456', name, U.MEMBER,
                grade=random.choice(GRADES), major=random.choice(MAJORS),
            )
            self.members.append(user)
            self.users[f'member{i}'] = user

        self.stdout.write(self.style.SUCCESS(
            f'   账号创建完成：8 个固定账号 + {len(self.members)} 个普通成员'
        ))

    # ------------------------------------------------------------------
    # 项目
    # ------------------------------------------------------------------
    def create_projects(self):
        self.stdout.write('-> 创建项目...')
        now = timezone.now()
        all_pool = self.members + self.leaders

        # 轮流分配负责人
        leader_rotation = [self.users['leader1'], self.users['leader2'], self.users['leader3']]

        for idx, pdata in enumerate(PROJECT_DATA):
            code = f'PROJ-{idx + 1:03d}'
            leader = leader_rotation[idx % 3]

            start_date = (now - timedelta(days=random.randint(30, 330))).date()
            planned_end = (now + timedelta(days=random.randint(90, 180))).date()

            # 前 8 个 active，后 2 个 closed
            if idx < 8:
                status = Project.Status.ACTIVE
                actual_end = None
            else:
                status = Project.Status.CLOSED
                actual_end = (now - timedelta(days=random.randint(5, 30))).date()

            # current_stage 随机 3~12（已关闭项目设为已结项 14）
            if status == Project.Status.CLOSED:
                current_stage = Project.Stage.CLOSED
            else:
                current_stage = random.randint(3, 12)

            priority = random.choice([
                Project.Priority.NORMAL, Project.Priority.NORMAL,
                Project.Priority.HIGH, Project.Priority.URGENT,
            ])

            # last_leader_update：大部分近 10 天内，2 个超过 11 天
            if idx in (2, 6):
                last_update = now - timedelta(days=random.randint(12, 20))
            else:
                last_update = now - timedelta(days=random.randint(0, 10))

            project = Project.objects.create(
                name=pdata['name'],
                code=code,
                leader=leader,
                current_stage=current_stage,
                start_date=start_date,
                planned_end_date=planned_end,
                actual_end_date=actual_end,
                status=status,
                priority=priority,
                intro=pdata['intro'],
                last_leader_update=last_update,
            )
            self.projects.append(project)

            # 项目成员：3~8 个（不含负责人本身）
            member_count = random.randint(3, 8)
            pool = [u for u in all_pool if u != leader]
            chosen = random.sample(pool, min(member_count, len(pool)))
            member_users = [leader] + chosen

            self.project_members[project.id] = member_users

            # 负责人作为 leader 角色
            ProjectMember.objects.create(
                project=project, user=leader,
                role_in_project=ProjectMember.RoleInProject.LEADER,
            )
            for u in chosen:
                role = random.choice([
                    ProjectMember.RoleInProject.CORE,
                    ProjectMember.RoleInProject.PARTICIPANT,
                ])
                ProjectMember.objects.create(
                    project=project, user=u, role_in_project=role,
                )

        self.stdout.write(self.style.SUCCESS(
            f'   项目创建完成：{len(self.projects)} 个'
        ))

    # ------------------------------------------------------------------
    # 比赛
    # ------------------------------------------------------------------
    def create_competitions(self):
        self.stdout.write('-> 创建比赛...')
        now = timezone.now()
        for i, cdata in enumerate(COMPETITION_DATA):
            project = self.projects[i]
            register_date = (now - timedelta(days=random.randint(10, 60))).date()
            comp = Competition(
                project=project,
                name=cdata['name'],
                comp_type=cdata['comp_type'],
                level=cdata['level'],
                organizer=cdata['organizer'],
                register_date=register_date,
                status=cdata['status'],
                current_stage=cdata['comp_type'] + '阶段',
            )
            # 已结束的比赛设置获奖信息
            if cdata['status'] == Competition.Status.COMPLETED:
                comp.is_awarded = True
                comp.is_promoted = True
                comp.award_level = random.choice(['一等奖', '二等奖', '三等奖', '优胜奖'])
                comp.result_date = (now - timedelta(days=random.randint(5, 30))).date()
                comp.review_summary = '团队表现出色，作品完整度高，获得评委好评。'
            else:
                # 进行中/准备中的比赛设置后续关键日期
                comp.material_deadline = (now + timedelta(days=random.randint(7, 30))).date()
                if cdata['status'] == Competition.Status.ONGOING:
                    comp.review_date = (now + timedelta(days=random.randint(15, 45))).date()
                    comp.defense_date = (now + timedelta(days=random.randint(30, 60))).date()
            comp.save()

        self.stdout.write(self.style.SUCCESS(f'   比赛创建完成：{len(COMPETITION_DATA)} 个'))

    # ------------------------------------------------------------------
    # 任务
    # ------------------------------------------------------------------
    def create_tasks(self):
        self.stdout.write('-> 创建任务...')
        now = timezone.now()

        # 状态池：todo(10) doing(10) pending_review(5) done(10) overdue(5) = 40
        status_pool = (
            [Task.Status.TODO] * 10 +
            [Task.Status.DOING] * 10 +
            [Task.Status.PENDING_REVIEW] * 5 +
            [Task.Status.DONE] * 10 +
            [Task.Status.OVERDUE] * 5
        )
        random.shuffle(status_pool)

        task_titles = [
            '需求调研与整理', '原型设计', '数据库表结构设计', '接口文档编写',
            '前端页面开发', '后端接口开发', '核心算法实现', '单元测试编写',
            '系统集成联调', '用户手册撰写', '答辩PPT制作', '比赛报名材料准备',
            '软件说明书撰写', '源代码文档整理', '性能优化', '部署上线',
            'Bug 修复与回归', '数据采集与清洗', '模型训练与调优', 'UI 视觉规范制定',
        ]

        # 每个项目分配 3~6 个任务，总数约 40
        per_project = [4, 5, 3, 4, 6, 3, 4, 5, 3, 3]  # sum = 40
        cursor = 0
        total = 0
        for pidx, project in enumerate(self.projects):
            members = self.project_members[project.id]
            leader = project.leader
            count = per_project[pidx]
            for _ in range(count):
                if cursor >= len(status_pool):
                    status = random.choice([Task.Status.TODO, Task.Status.DOING])
                else:
                    status = status_pool[cursor]
                    cursor += 1

                assignee = random.choice(members)
                title = random.choice(task_titles)
                # 标题去重：附加项目编号后缀
                title = f'{title}（{project.code}）'

                deadline = None
                completed_at = None
                overdue_reminded = False

                if status == Task.Status.TODO:
                    deadline = now + timedelta(days=random.randint(2, 14))
                elif status == Task.Status.DOING:
                    deadline = now + timedelta(days=random.randint(1, 10))
                elif status == Task.Status.PENDING_REVIEW:
                    deadline = now - timedelta(days=random.randint(0, 3))
                elif status == Task.Status.DONE:
                    completed_at = now - timedelta(days=random.randint(1, 20))
                    deadline = completed_at - timedelta(days=random.randint(1, 5))
                elif status == Task.Status.OVERDUE:
                    deadline = now - timedelta(days=3)
                    overdue_reminded = True

                reviewer = leader if status == Task.Status.PENDING_REVIEW else None

                Task.objects.create(
                    project=project,
                    title=title,
                    assignee=assignee,
                    creator=leader,
                    status=status,
                    deadline=deadline,
                    completed_at=completed_at,
                    overdue_reminded=overdue_reminded,
                    reviewer=reviewer,
                    description=f'本项目「{project.name}」的{title}任务，由{assignee.name}负责。',
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f'   任务创建完成：{total} 个'))

    # ------------------------------------------------------------------
    # 经费
    # ------------------------------------------------------------------
    def create_finance(self):
        self.stdout.write('-> 创建经费数据...')
        now = timezone.now()
        budget_count = 0
        expense_count = 0
        receipt_count = 0

        expense_titles = {
            'material': '实验材料采购',
            'equipment': '开发设备购置',
            'printing': '项目材料打印',
            'travel': '调研差旅费',
            'software': '开发软件授权',
            'competition_fee': '比赛报名费',
            'promotion': '项目宣传推广',
            'labor': '劳务支出',
            'other': '其他杂项支出',
        }

        for project in self.projects:
            members = self.project_members[project.id]
            bonus = Decimal(random.randint(5000, 50000))
            other_income = Decimal(random.randint(0, 10000))
            total_income = bonus + other_income

            # 生成 2~3 条支出，汇总 used_amount
            expense_num = random.randint(2, 3)
            expenses = []
            for _ in range(expense_num):
                category = random.choice(list(expense_titles.keys()))
                amount = Decimal(random.randint(100, 5000))
                spender = random.choice(members)
                expense_date = (now - timedelta(days=random.randint(1, 60))).date()
                expense = FinanceExpense.objects.create(
                    project=project,
                    title=expense_titles[category],
                    amount=amount,
                    spender=spender,
                    expense_date=expense_date,
                    category=category,
                    purpose=f'{project.name} - {expense_titles[category]}，用于项目推进所需。',
                )
                expenses.append(amount)
                expense_count += 1

                # 为每条支出创建 1~2 张模拟票据
                for _r in range(random.randint(1, 2)):
                    receipt = FinanceReceipt(
                        expense=expense,
                        uploaded_by=spender,
                    )
                    mock_content = f'模拟票据图片 - {expense.title} - {project.name}'
                    receipt.file.save(
                        f'receipt_{project.id}_{expense.id}_{_r+1}.txt',
                        ContentFile(mock_content.encode('utf-8')),
                        save=True,
                    )
                    receipt_count += 1

            used_amount = sum(expenses, Decimal('0'))
            # 保证已用不超过总收入
            if used_amount > total_income:
                used_amount = total_income * Decimal('0.8')
            pending_reimbursement = Decimal(random.randint(0, int(used_amount)))

            # 根据剩余判断状态
            remaining = total_income - used_amount
            if remaining < 0:
                budget_status = FinanceBudget.Status.ABNORMAL
            elif remaining < total_income * Decimal('0.2'):
                budget_status = FinanceBudget.Status.WARNING
            else:
                budget_status = FinanceBudget.Status.NORMAL

            FinanceBudget.objects.create(
                project=project,
                bonus_amount=bonus,
                other_income=other_income,
                used_amount=used_amount,
                pending_reimbursement=pending_reimbursement,
                status=budget_status,
                period=now.strftime('%Y-%m'),
            )
            budget_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'   经费创建完成：预算 {budget_count} 条，支出 {expense_count} 条，票据 {receipt_count} 条'
        ))

    # ------------------------------------------------------------------
    # 技能标签与成员技能
    # ------------------------------------------------------------------
    def create_skills(self):
        self.stdout.write('-> 创建技能标签与成员技能...')
        skills = []
        for name in SKILL_NAMES:
            skills.append(SkillTag.objects.create(name=name))

        all_members = self.members + self.leaders
        # 为约 20 个成员分配 2~3 个技能
        chosen_members = random.sample(all_members, min(20, len(all_members)))
        count = 0
        for user in chosen_members:
            num = random.randint(2, 3)
            picked = random.sample(skills, num)
            for skill in picked:
                MemberSkill.objects.create(
                    user=user, skill=skill,
                    proficiency=random.randint(1, 5),
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(
            f'   技能创建完成：标签 {len(skills)} 个，成员技能 {count} 条'
        ))

    # ------------------------------------------------------------------
    # 灵活工作时间
    # ------------------------------------------------------------------
    def create_work_schedules(self):
        self.stdout.write('-> 创建灵活工作时间...')
        today = timezone.localdate()
        if today.day <= 15:
            period_start = today.replace(day=1)
            period_end = today.replace(day=15)
        else:
            period_start = today.replace(day=16)
            last_day = calendar.monthrange(today.year, today.month)[1]
            period_end = today.replace(day=last_day)

        all_members = self.members + self.leaders
        chosen = random.sample(all_members, min(15, len(all_members)))
        count = 0
        for user in chosen:
            work_hours = Decimal(random.randint(20, 80))
            detail = {
                '周一': random.randint(2, 8),
                '周二': random.randint(2, 8),
                '周三': random.randint(2, 8),
                '周四': random.randint(2, 8),
                '周五': random.randint(2, 8),
                '周末': random.randint(0, 6),
                '备注': '本周期可投入工时如上，课表已避开。',
            }
            FlexibleWorkSchedule.objects.create(
                user=user,
                period_start=period_start,
                period_end=period_end,
                work_hours=work_hours,
                detail=detail,
                can_offline=random.choice([True, False]),
                can_urgent=random.choice([True, False]),
                is_saturated=random.choice([True, False, False]),
                notes=random.choice(['', '近期有考试，工时偏少', '可接受紧急任务', '已满负荷']),
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'   灵活工时创建完成：{count} 条'))

    # ------------------------------------------------------------------
    # 贡献记录
    # ------------------------------------------------------------------
    def create_contributions(self):
        self.stdout.write('-> 创建贡献记录...')
        now = timezone.now()
        period = now.strftime('%Y-%m')

        # 15 条：8 approved / 5 pending / 2 rejected
        statuses = (
            [Contribution.Status.APPROVED] * 8 +
            [Contribution.Status.PENDING] * 5 +
            [Contribution.Status.REJECTED] * 2
        )
        random.shuffle(statuses)

        contrib_types = [
            Contribution.ContributionType.STAGE_TASK,
            Contribution.ContributionType.CORE,
            Contribution.ContributionType.LONG_TERM,
            Contribution.ContributionType.RESOURCE,
            Contribution.ContributionType.TEMPORARY_HELP,
            Contribution.ContributionType.COMPETITION,
            Contribution.ContributionType.FINANCE_MANAGE,
            Contribution.ContributionType.IP_WRITING,
        ]

        contents = [
            '负责项目核心模块开发，按时完成阶段性目标。',
            '承担大量文档撰写与材料整理工作。',
            '长期参与项目，持续贡献代码与思路。',
            '为团队提供关键测试设备与数据资源。',
            '临时协助完成答辩PPT制作。',
            '作为核心成员主导技术方案设计。',
            '负责比赛申报材料撰写并顺利提交。',
            '协助完成经费报销与票据整理。',
        ]

        for i, status in enumerate(statuses):
            project = self.projects[i % len(self.projects)]
            members = self.project_members[project.id]
            user = random.choice(members)
            leader = project.leader
            ctype = random.choice(contrib_types)
            content = random.choice(contents)
            weight = Decimal(random.randint(1, 10))

            kwargs = dict(
                user=user,
                project=project,
                contribution_type=ctype,
                content=content,
                description=content,
                weight=weight,
                status=status,
                period=period,
                filled_by=leader,
            )
            if status == Contribution.Status.APPROVED:
                kwargs.update(
                    reviewer=leader,
                    reviewed_at=now - timedelta(days=random.randint(1, 10)),
                    review_opinion='贡献属实，予以确认。',
                    score=weight * Decimal('2'),
                )
            elif status == Contribution.Status.REJECTED:
                kwargs.update(
                    reviewer=leader,
                    reviewed_at=now - timedelta(days=random.randint(1, 5)),
                    review_opinion='描述与实际不符，暂不确认。',
                )
            Contribution.objects.create(**kwargs)

        self.stdout.write(self.style.SUCCESS(
            f'   贡献记录创建完成：{len(statuses)} 条'
        ))

    # ------------------------------------------------------------------
    # 成员排序与异议
    # ------------------------------------------------------------------
    def create_rankings(self):
        self.stdout.write('-> 创建成员排序与异议...')
        now = timezone.now()
        period = now.strftime('%Y-%m')

        # 前 2 个项目：第 1 个 draft，第 2 个 confirmed
        ranking_specs = [
            (self.projects[0], MemberRanking.Status.DRAFT),
            (self.projects[1], MemberRanking.Status.CONFIRMED),
        ]

        all_rankings = []
        for project, status in ranking_specs:
            members = self.project_members[project.id]
            ranked_members = random.sample(members, min(5, len(members)))
            # 按随机的“分值”降序排名
            scored = [(m, Decimal(random.randint(10, 100))) for m in ranked_members]
            scored.sort(key=lambda x: x[1], reverse=True)

            is_public = status == MemberRanking.Status.CONFIRMED
            for rank, (user, score) in enumerate(scored, start=1):
                ranking = MemberRanking.objects.create(
                    user=user,
                    project=project,
                    period=period,
                    status=status,
                    total_score=score,
                    rank=rank,
                    task_completed_count=random.randint(0, 12),
                    project_count=random.randint(1, 3),
                    competition_count=random.randint(0, 2),
                    ip_contribution_count=random.randint(0, 2),
                    is_published=is_public,
                    is_public=is_public,
                )
                all_rankings.append(ranking)

        # 2 条异议：1 pending / 1 leader_reviewed
        if len(all_rankings) >= 2:
            # 第一条：pending（来自 draft 项目，提出人为该项目成员）
            r1 = all_rankings[0]
            objector1 = random.choice(self.project_members[r1.project_id])
            RankingObjection.objects.create(
                ranking=r1,
                objector=objector1,
                content='我对自己的排名有异议，本周期完成了较多阶段性任务，'
                        '认为贡献分值应更高。',
                status=RankingObjection.Status.PENDING,
            )
            # 第二条：leader_reviewed（来自 confirmed 项目）
            r2 = all_rankings[-1]
            members2 = self.project_members[r2.project_id]
            objector2 = random.choice(members2)
            RankingObjection.objects.create(
                ranking=r2,
                objector=objector2,
                content='排名结果未充分考虑 IP 撰写贡献，请求复核。',
                status=RankingObjection.Status.LEADER_REVIEWED,
                leader_opinion='经核实，该成员 IP 贡献确有遗漏，建议老师最终确认后调整。',
                leader_reviewer=self.projects[1].leader,
                leader_reviewed_at=now - timedelta(days=1),
            )

        self.stdout.write(self.style.SUCCESS(
            f'   排序创建完成：{len(all_rankings)} 条，异议 2 条'
        ))

    # ------------------------------------------------------------------
    # 知识产权申请
    # ------------------------------------------------------------------
    def create_ip_applications(self):
        self.stdout.write('-> 创建知识产权申请...')
        now = timezone.now()
        leader1 = self.users['leader1']
        leader2 = self.users['leader2']
        leader3 = self.users['leader3']

        def pick_members(project, n):
            members = self.project_members[project.id]
            return random.sample(members, min(n, len(members)))

        # --- 1. 智能校园导览系统 软著 - 已授权 ---
        p1 = self.projects[0]
        ip1 = IntellectualPropertyApplication.objects.create(
            title='智能校园导览系统',
            application_code='IP-2025-001',
            ip_type=IntellectualPropertyApplication.IPType.SOFTWARE_COPYRIGHT,
            related_project=p1,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
            main_writer=leader1,
            applicant_executor=leader1,
            material_manager=pick_members(p1, 1)[0],
            project_reviewer=leader1,
            teacher_confirmer=self.teachers[0],
            start_date=(now - timedelta(days=180)).date(),
            submit_date=(now - timedelta(days=150)).date(),
            accepted_date=(now - timedelta(days=90)).date(),
            authorized_date=(now - timedelta(days=30)).date(),
            return_count=0,
            intro='基于移动端定位与AR技术的校园导览系统软件著作权，'
                  '包含室内外导航、景点讲解与活动指引等核心模块。',
            created_by=leader1,
        )
        self._add_ip_contributors(ip1, leader1, p1, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.EXECUTOR,
            IPApplicationContributor.ContributorRole.MATERIAL_MANAGER,
        ])

        # --- 2. 医学影像辅助诊断算法 发明专利 - 科研处退回 ---
        p2 = self.projects[1]
        writer2 = leader2
        ip2 = IntellectualPropertyApplication.objects.create(
            title='医学影像辅助诊断算法',
            application_code='IP-2025-002',
            ip_type=IntellectualPropertyApplication.IPType.INVENTION_PATENT,
            related_project=p2,
            status=IntellectualPropertyApplication.Status.RETURNED,
            main_writer=writer2,
            applicant_executor=writer2,
            material_manager=pick_members(p2, 1)[0],
            project_reviewer=writer2,
            start_date=(now - timedelta(days=120)).date(),
            submit_date=(now - timedelta(days=60)).date(),
            return_count=1,
            current_problem='科研处退回：权利要求书保护范围不够清晰，说明书技术方案描述需补充实施例。',
            intro='一种基于深度卷积神经网络的医学影像病灶检测与分类方法及系统。',
            created_by=writer2,
        )
        self._add_ip_contributors(ip2, writer2, p2, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.CODE_PROVIDER,
            IPApplicationContributor.ContributorRole.EXECUTOR,
        ])
        # 退回记录
        IPReturnRecord.objects.create(
            application=ip2,
            return_time=now - timedelta(days=7),
            return_source=IPReturnRecord.ReturnSource.RESEARCH_OFFICE,
            return_reason='权利要求保护范围过宽，说明书缺少足够实施例支撑，需补充技术效果描述。',
            responsibility_type=IPReturnRecord.ResponsibilityType.WRITING_PROBLEM,
            responsible_user=writer2,
            assigned_by=self.teachers[0],
            modify_deadline=now + timedelta(days=7),
            actual_modifier=writer2,
            modify_description='',
            result=IPReturnRecord.ReturnResult.PENDING,
        )

        # --- 3. 农产品溯源链码生成方法 发明专利 - 科研处审核中 ---
        p4 = self.projects[3]
        writer3 = leader1
        ip3 = IntellectualPropertyApplication.objects.create(
            title='农产品溯源链码生成方法',
            application_code='IP-2025-003',
            ip_type=IntellectualPropertyApplication.IPType.INVENTION_PATENT,
            related_project=p4,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
            main_writer=writer3,
            applicant_executor=writer3,
            material_manager=pick_members(p4, 1)[0],
            project_reviewer=writer3,
            teacher_confirmer=self.teachers[0],
            start_date=(now - timedelta(days=90)).date(),
            submit_date=(now - timedelta(days=30)).date(),
            return_count=0,
            intro='一种基于联盟链的农产品溯源链码生成与校验方法，确保数据不可篡改。',
            created_by=writer3,
        )
        self._add_ip_contributors(ip3, writer3, p4, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.DRAWING_PROVIDER,
            IPApplicationContributor.ContributorRole.EXECUTOR,
        ])

        # --- 4. 校园二手交易小程序 软著 - 材料撰写中 ---
        p3 = self.projects[2]
        writer4 = leader2
        ip4 = IntellectualPropertyApplication.objects.create(
            title='校园二手交易小程序',
            application_code='IP-2025-004',
            ip_type=IntellectualPropertyApplication.IPType.SOFTWARE_COPYRIGHT,
            related_project=p3,
            status=IntellectualPropertyApplication.Status.WRITING,
            main_writer=writer4,
            applicant_executor=writer4,
            material_manager=pick_members(p3, 1)[0],
            start_date=(now - timedelta(days=30)).date(),
            return_count=0,
            current_problem='软件说明书撰写中，源代码文档待整理。',
            intro='面向在校学生的二手物品交易小程序软件著作权。',
            created_by=writer4,
        )
        self._add_ip_contributors(ip4, writer4, p3, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.DOCUMENT_WRITER,
        ])

        # --- 5. 环境监测数据异常检测方法 实用新型专利 - 科研处退回 ---
        p9 = self.projects[8]
        writer5 = leader3
        ip5 = IntellectualPropertyApplication.objects.create(
            title='环境监测数据异常检测方法',
            application_code='IP-2025-005',
            ip_type=IntellectualPropertyApplication.IPType.UTILITY_MODEL,
            related_project=p9,
            status=IntellectualPropertyApplication.Status.RETURNED,
            main_writer=writer5,
            applicant_executor=writer5,
            material_manager=pick_members(p9, 1)[0],
            project_reviewer=writer5,
            start_date=(now - timedelta(days=150)).date(),
            submit_date=(now - timedelta(days=90)).date(),
            return_count=2,
            current_problem='第二次退回：附图标记与说明书不一致，权利要求项引用关系有误。',
            intro='一种用于环境监测物联网数据的异常检测与告警方法及装置。',
            created_by=writer5,
        )
        self._add_ip_contributors(ip5, writer5, p9, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.DRAWING_PROVIDER,
            IPApplicationContributor.ContributorRole.MATERIAL_MANAGER,
        ])
        # 退回记录
        IPReturnRecord.objects.create(
            application=ip5,
            return_time=now - timedelta(days=3),
            return_source=IPReturnRecord.ReturnSource.RESEARCH_OFFICE,
            return_reason='附图标记与说明书描述不一致，权利要求项引用关系存在错误，需重新核对。',
            responsibility_type=IPReturnRecord.ResponsibilityType.MATERIAL_PROBLEM,
            responsible_user=pick_members(p9, 1)[0],
            assigned_by=self.teachers[0],
            modify_deadline=now + timedelta(days=10),
            actual_modifier=None,
            modify_description='',
            result=IPReturnRecord.ReturnResult.PENDING,
        )

        # 2 条知识产权异议
        IPObjection.objects.create(
            application=ip2,
            objector=pick_members(p2, 1)[0],
            objection_type=IPObjection.ObjectionType.RETURN_RESPONSIBILITY,
            content='退回责任不应全部由撰写人承担，材料整理环节也存在疏漏。',
            status=IPObjection.ObjectionStatus.PENDING,
        )
        IPObjection.objects.create(
            application=ip1,
            objector=pick_members(p1, 1)[0],
            objection_type=IPObjection.ObjectionType.WRITING_CREDIT,
            content='申请执行贡献认定偏低，请求复核贡献排序。',
            status=IPObjection.ObjectionStatus.RESOLVED,
            leader_opinion='经核实贡献属实，已调整排序。',
            leader_reviewer=leader1,
            leader_reviewed_at=now - timedelta(days=5),
            teacher_confirmer=self.teachers[0],
            teacher_confirmed_at=now - timedelta(days=3),
            final_result='维持原贡献认定，排序微调。',
        )

        self.stdout.write(self.style.SUCCESS(
            '   知识产权创建完成：申请 5 个，退回记录 2 条，异议 2 条'
        ))

    def _add_ip_contributors(self, application, main_writer, project, roles):
        """为 IP 申请添加贡献人（第一个角色固定为主撰写人）"""
        members = [u for u in self.project_members[project.id] if u != main_writer]
        random.shuffle(members)
        # 第一个角色由主撰写人担任
        application_contributors = [(main_writer, roles[0])]
        # 其余角色从项目成员中分配
        for role in roles[1:]:
            if members:
                application_contributors.append((members.pop(), role))
        for user, role in application_contributors:
            IPApplicationContributor.objects.create(
                application=application,
                user=user,
                role=role,
                contribution_description=f'{user.name} 在「{application.title}」中担任'
                                         f'{role} 角色。',
                is_confirmed=random.choice([True, False]),
            )

    # ------------------------------------------------------------------
    # 敏感资料
    # ------------------------------------------------------------------
    def create_sensitive_data(self):
        self.stdout.write('-> 创建敏感资料...')
        # 为 leader1, leader2, member1 各创建 1 条身份证敏感资料
        owners = [self.users['leader1'], self.users['leader2'], self.users['member1']]
        # 模拟身份证号（非真实号码，均为 110101 开头的演示号码）
        fake_ids = ['110101200001011234', '110101200106072345', '110101200311225678']

        self.sensitive_data_map = {}
        for owner, fake_id in zip(owners, fake_ids):
            sd = SensitiveData(
                data_type=SensitiveData.DataType.ID_CARD,
                title=f'{owner.name}的身份证号码',
                display_name='身份证号码',
                key_version=1,
                uploader=owner,
                is_encrypted=False,
                encrypted_content='',
            )
            sd.save()
            # 使用模型的加密方法加密模拟身份证号
            sd.encrypt_content(fake_id)
            self.sensitive_data_map[owner.email] = sd

        self.stdout.write(self.style.SUCCESS(
            f'   敏感资料创建完成：{len(owners)} 条（已加密）'
        ))

    # ------------------------------------------------------------------
    # 敏感资料访问申请
    # ------------------------------------------------------------------
    def create_sensitive_requests(self):
        self.stdout.write('-> 创建敏感资料访问申请...')
        now = timezone.now()
        approver = self.users['approver']

        # 1. member5 申请查看 leader1 的身份证 - 已通过，30 分钟内有效
        sd_leader1 = self.sensitive_data_map[self.users['leader1'].email]
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd_leader1,
            applicant=self.users['member5'],
            reason='办理比赛获奖奖金发放，需核对负责人身份证信息。',
            usage_scenario='奖金发放身份核验',
            project=self.projects[0],
            expected_use_time=now + timedelta(hours=2),
            is_download=False,
            status=SensitiveAccessRequest.Status.APPROVED,
            approver=approver,
            approval_opinion='情况属实，同意在有效期内查看。',
            approved_at=now - timedelta(minutes=10),
            access_expires_at=now + timedelta(minutes=30),
        )

        # 2. member10 申请查看 member1 的身份证 - 待审批
        sd_member1 = self.sensitive_data_map[self.users['member1'].email]
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd_member1,
            applicant=self.users['member10'],
            reason='协助办理报销需要核对经办人身份信息。',
            usage_scenario='财务报销身份核对',
            project=self.projects[2],
            expected_use_time=now + timedelta(days=1),
            is_download=True,
            status=SensitiveAccessRequest.Status.PENDING,
        )

        self.stdout.write(self.style.SUCCESS('   敏感资料访问申请创建完成：2 条'))

    # ------------------------------------------------------------------
    # 通知
    # ------------------------------------------------------------------
    def create_notifications(self):
        self.stdout.write('-> 创建通知...')
        now = timezone.now()
        NT = Notification.NotificationType
        admin = self.users['admin']

        notifs = [
            {
                'recipient': self.users['member5'],
                'sender': admin,
                'type': NT.TASK,
                'title': '任务逾期提醒',
                'content': '您有任务已逾期，请尽快处理或申请延期。',
                'priority': Notification.Priority.HIGH,
                'ref_type': 'task', 'ref_id': 1,
            },
            {
                'recipient': self.users['leader1'],
                'sender': self.teachers[0],
                'type': NT.PROJECT,
                'title': '负责人更新提醒',
                'content': '您负责的项目已超过 11 天未更新进度，请及时填写进展。',
                'priority': Notification.Priority.NORMAL,
                'ref_type': 'project', 'ref_id': self.projects[2].id,
            },
            {
                'recipient': self.users['leader2'],
                'sender': admin,
                'type': NT.PROJECT,
                'title': '知识产权退回通知',
                'content': '您的发明专利申请被科研处退回，请尽快查看退回原因并修改。',
                'priority': Notification.Priority.HIGH,
                'ref_type': 'ip_application', 'ref_id': 2,
            },
            {
                'recipient': self.users['leader1'],
                'sender': self.users['member3'],
                'type': NT.PROJECT,
                'title': '贡献记录待审核',
                'content': '有新的贡献记录等待您审核，请及时处理。',
                'priority': Notification.Priority.NORMAL,
                'ref_type': 'contribution', 'ref_id': 1,
            },
            {
                'recipient': self.users['approver'],
                'sender': self.users['member10'],
                'type': NT.SYSTEM,
                'title': '敏感资料访问申请待审批',
                'content': '有新的敏感资料访问申请等待您审批。',
                'priority': Notification.Priority.HIGH,
                'ref_type': 'sensitive_request', 'ref_id': 2,
            },
            {
                'recipient': self.users['leader3'],
                'sender': admin,
                'type': NT.TASK,
                'title': '任务待审核',
                'content': '有任务已提交完成，等待您审核确认。',
                'priority': Notification.Priority.NORMAL,
                'ref_type': 'task', 'ref_id': 3,
            },
            {
                'recipient': self.users['member1'],
                'sender': admin,
                'type': NT.FINANCE,
                'title': '经费报销进度通知',
                'content': '您提交的报销申请已进入审核流程，请关注后续状态。',
                'priority': Notification.Priority.LOW,
                'ref_type': 'finance_expense', 'ref_id': 1,
            },
            {
                'recipient': self.users['leader1'],
                'sender': self.teachers[1],
                'type': NT.COMPETITION,
                'title': '比赛报名截止提醒',
                'content': '互联网+大赛报名即将截止，请尽快完成材料提交。',
                'priority': Notification.Priority.HIGH,
                'ref_type': 'competition', 'ref_id': 1,
            },
            {
                'recipient': self.users['member7'],
                'sender': admin,
                'type': NT.SYSTEM,
                'title': '灵活工时填写提醒',
                'content': '本周期灵活工作时间表尚未填写，请尽快提交。',
                'priority': Notification.Priority.NORMAL,
                'ref_type': 'work_schedule', 'ref_id': 1,
            },
            {
                'recipient': self.users['leader1'],
                'sender': self.users['member4'],
                'type': NT.PROJECT,
                'title': '排名异议通知',
                'content': '有成员对项目排名结果提出异议，请及时处理。',
                'priority': Notification.Priority.NORMAL,
                'ref_type': 'ranking_objection', 'ref_id': 1,
            },
        ]

        for n in notifs:
            Notification.objects.create(
                recipient=n['recipient'],
                sender=n['sender'],
                notification_type=n['type'],
                channel=Notification.Channel.INAPP,
                title=n['title'],
                content=n['content'],
                priority=n['priority'],
                related_object_type=n['ref_type'],
                related_object_id=n['ref_id'],
                is_read=random.choice([True, False, False]),
            )

        self.stdout.write(self.style.SUCCESS(f'   通知创建完成：{len(notifs)} 条'))

    # ------------------------------------------------------------------
    # 操作日志
    # ------------------------------------------------------------------
    def create_operation_logs(self):
        self.stdout.write('-> 创建操作日志...')
        OT = OperationLog.OperationType

        log_specs = [
            (self.users['admin'], OT.LOGIN, 'auth', 'User', '登录系统', 'POST', '/api/auth/login/', 200),
            (self.users['leader1'], OT.CREATE, 'projects', 'Project', '创建项目 智能校园导览系统', 'POST', '/api/projects/', 201),
            (self.users['leader1'], OT.UPDATE, 'projects', 'Project', '更新项目进度', 'PATCH', '/api/projects/1/', 200),
            (self.users['member3'], OT.CREATE, 'tasks', 'Task', '创建任务 需求调研与整理', 'POST', '/api/tasks/', 201),
            (self.users['member5'], OT.UPDATE, 'tasks', 'Task', '更新任务状态为进行中', 'PATCH', '/api/tasks/3/', 200),
            (self.users['leader2'], OT.APPROVE, 'contributions', 'Contribution', '审核通过贡献记录', 'POST', '/api/contributions/1/review/', 200),
            (self.users['leader1'], OT.REJECT, 'contributions', 'Contribution', '驳回贡献记录', 'POST', '/api/contributions/2/review/', 200),
            (self.users['member10'], OT.CREATE, 'sensitive', 'SensitiveAccessRequest', '提交敏感资料访问申请', 'POST', '/api/sensitive/requests/', 201),
            (self.users['approver'], OT.APPROVE, 'sensitive', 'SensitiveAccessRequest', '审批通过敏感资料访问申请', 'POST', '/api/sensitive/requests/1/approve/', 200),
            (self.users['member5'], OT.VIEW_SENSITIVE, 'sensitive', 'SensitiveData', '查看敏感资料明文', 'GET', '/api/sensitive/1/view/', 200),
            (self.users['admin'], OT.UPLOAD, 'files', 'FileAsset', '上传项目文件', 'POST', '/api/files/', 201),
            (self.users['member12'], OT.DOWNLOAD, 'files', 'FileAsset', '下载公开文件', 'GET', '/api/files/1/download/', 200),
            (self.users['leader3'], OT.CREATE, 'ip', 'IPApplication', '创建知识产权申请', 'POST', '/api/ip/applications/', 201),
            (self.users['teacher1'], OT.REVIEW, 'ip', 'IPApplication', '确认知识产权申请', 'POST', '/api/ip/applications/1/confirm/', 200),
            (self.users['admin'], OT.EXPORT, 'exports', 'Project', '导出项目汇总报告', 'GET', '/api/exports/project-report/', 200),
            (self.users['leader1'], OT.CREATE, 'finance', 'FinanceExpense', '登记经费支出', 'POST', '/api/finance/expenses/', 201),
            (self.users['member8'], OT.DELETE, 'tasks', 'Task', '删除作废任务', 'DELETE', '/api/tasks/9/', 204),
            (self.users['admin'], OT.IMPORT, 'imports', 'Member', '批量导入成员', 'POST', '/api/imports/members/', 200),
            (self.users['member15'], OT.UPDATE, 'members', 'FlexibleWorkSchedule', '填写灵活工时', 'POST', '/api/members/work-schedules/', 201),
            (self.users['leader2'], OT.OTHER, 'rankings', 'MemberRanking', '提交成员排序草案', 'POST', '/api/contributions/rankings/', 201),
        ]

        for spec in log_specs:
            operator, op_type, module, obj_type, desc, method, path, status = spec
            OperationLog.objects.create(
                operator=operator,
                operation_type=op_type,
                module=module,
                object_type=obj_type,
                object_id=str(random.randint(1, 50)),
                description=desc,
                request_method=method,
                request_path=path,
                request_ip='127.0.0.1',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) DemoBrowser/1.0',
                request_data={'demo': True, 'source': 'seed_demo_data'},
                response_status=status,
                is_success=status < 400,
            )

        self.stdout.write(self.style.SUCCESS(f'   操作日志创建完成：{len(log_specs)} 条'))

    # ------------------------------------------------------------------
    # 清除演示数据
    # ------------------------------------------------------------------
    def clean_demo_data(self):
        self.stdout.write(self.style.WARNING('-> 清除现有演示数据...'))
        # 按依赖顺序删除（子表先于父表）
        models_to_clean = [
            OperationLog,
            Notification,
            SensitiveAccessRequest,
            SensitiveData,
            IPObjection,
            IPReturnRecord,
            IPApplicationContributor,
            IntellectualPropertyApplication,
            RankingObjection,
            MemberRanking,
            Contribution,
            FlexibleWorkSchedule,
            MemberSkill,
            SkillTag,
            FinanceReceipt,
            FinanceExpense,
            FinanceBudget,
            Task,
            Competition,
            ProjectMember,
            Project,
        ]
        total = 0
        for model in models_to_clean:
            count, _ = model.objects.all().delete()
            # delete() 返回的 dict 中包含每个表的删除条数
            if isinstance(count, dict):
                total += sum(count.values())
            else:
                total += count
        # 删除演示账号（@demo.com），其它账号保留
        user_count, _ = User.objects.filter(email__endswith='@demo.com').delete()
        if isinstance(user_count, dict):
            total += sum(user_count.values())
        else:
            total += user_count

        self.stdout.write(self.style.SUCCESS(f'   已清除演示数据（约 {total} 条记录）'))

    # ------------------------------------------------------------------
    # 账号汇总
    # ------------------------------------------------------------------
    def print_account_summary(self):
        self.stdout.write('账号清单：')
        self.stdout.write('  系统管理员: admin@demo.com / admin123456')
        self.stdout.write('  老师1:     teacher1@demo.com / teacher123456')
        self.stdout.write('  老师2:     teacher2@demo.com / teacher123456')
        self.stdout.write('  负责人1:   leader1@demo.com / leader123456')
        self.stdout.write('  负责人2:   leader2@demo.com / leader123456')
        self.stdout.write('  负责人3:   leader3@demo.com / leader123456')
        self.stdout.write('  敏感审批:  approver@demo.com / approver123456')
        self.stdout.write('  普通成员:  member1~45@demo.com / member123456')
