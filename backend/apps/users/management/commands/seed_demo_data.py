"""
生成完整演示数据的管理命令

用法:
    python manage.py seed_demo_data          # 生成演示数据（带确认提示）
    python manage.py seed_demo_data --clean  # 先清除所有演示数据再重新生成
    python manage.py seed_demo_data --force  # 跳过确认提示

数据概览:
    - 账号: 8 个固定账号 + 52 个普通成员
    - 团队: 1 个总团队 + 3 个二级小团队
    - 项目: 24 个（覆盖 2022 年至今，并包含已结项、暂停、进行中）
    - 比赛: 5 个
    - 任务: 120 个（覆盖完整状态分布）
    - 文件: 96 个项目文档 + 1 个授权证书 PDF，并含版本与任务附件
    - 生命周期: 团队成员、项目成员、项目阶段历史
    - 导入历史: 7 个模块的成功、预览、失败与回滚记录
    - 公开门户: 显式公开决策、精选与成员授权
    - 经费: 每项目 1 条预算 + 2~3 条支出
    - 技能标签: 15 个 + 部分成员技能
    - 灵活工时: ~15 条
    - 贡献记录: 15 条
    - 成员排序: 2 个项目（1 draft / 1 confirmed）+ 2 条异议
    - 定时报表: 3 个计划 + 3 个成功执行文件（XLSX/DOCX/PDF）
    - 知识产权申请: 5 个（含退回记录、贡献人、异议）
    - 敏感资料: 3 条 + 2 条访问申请
    - 通知: 10 条
    - 公告: 3 条
    - 操作日志: 20 条
"""
import calendar
import random
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from docx import Document
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from openpyxl import Workbook
from PIL import Image as PILImage, ImageDraw, ImageFont
from pptx import Presentation
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from apps.users.models import User, UserLifecycleEvent, UserPreference
from apps.projects.models import (
    Project,
    ProjectMember,
    ProjectMembershipEvent,
    ProjectStageLog,
)
from apps.competitions.models import Competition
from apps.tasks.models import Task
from apps.finance.models import FinanceBudget, FinanceExpense, FinanceIncome, FinanceReceipt
from apps.files.models import FileAsset, FileVersion
from apps.imports.models import ImportTask
from apps.common.team_models import Team, TeamMember, TeamMembershipEvent
from apps.dashboard.portal_models import PortalPublication, PortalSettings
from apps.members.models import SkillTag, MemberSkill, FlexibleWorkSchedule
from apps.contributions.models import (
    Contribution, MemberRanking, RankingObjection,
)
from apps.intellectual_property.models import (
    IntellectualPropertyApplication, IPApplicationContributor,
    IPReturnRecord, IPMaterialVersion, IPObjection,
)
from apps.exports.custom_report_models import CustomReport
from apps.exports.scheduled_report_models import (
    ScheduledReport,
    ScheduledReportExecution,
)
from apps.exports.scheduled_report_service import compute_next_run
from apps.sensitive.models import SensitiveData, SensitiveAccessRequest
from apps.notifications.models import Announcement, Notification
from apps.audit.models import OperationLog


DEMO_PROJECT_PREFIX = 'TEAM-DEMO-'
DEMO_IP_PREFIX = 'IP-TEAM-DEMO-'
DEMO_MARKER = '【团队演示】'
DEMO_IMPORT_DIRNAME = 'seed_demo_data'
DEMO_TEAM_CODE = 'TEAM-DEMO-ORG'
DEMO_SQUAD_CODES = (
    'TEAM-DEMO-SQUAD-PRODUCT',
    'TEAM-DEMO-SQUAD-DATA',
    'TEAM-DEMO-SQUAD-OPERATIONS',
)
DEMO_ACCOUNT_EMAILS = (
    'admin@demo.com',
    'teacher1@demo.com',
    'teacher2@demo.com',
    'leader1@demo.com',
    'leader2@demo.com',
    'leader3@demo.com',
    'leader4@demo.com',
    'approver@demo.com',
    *(f'member{index}@demo.com' for index in range(1, 53)),
)
LEGACY_COMPETITION_ACCOUNT_EMAILS = (
    'leader5@demo.com',
    'leader6@demo.com',
)
LEGACY_COMPETITION_REPORT_NAMES = (
    '每日项目经营概览',
    '每周任务交付报告',
    '每月经费执行报告',
    '每周比赛推进简报',
)

FILE_SPECS = (
    (
        '项目概览',
        '.pdf',
        'application/pdf',
        FileAsset.Level.PUBLIC,
    ),
    (
        '工作计划',
        '.docx',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        FileAsset.Level.INTERNAL,
    ),
    (
        '数据简表',
        '.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        FileAsset.Level.INTERNAL,
    ),
    (
        '路演材料',
        '.pptx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        FileAsset.Level.INTERNAL,
    ),
)


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
    {
        'name': '校园能耗数字孪生平台',
        'intro': '汇总楼宇水电与设备运行数据，以数字孪生方式展示能耗趋势并给出节能建议。',
    },
    {
        'name': '非遗文化数字展示平台',
        'intro': '通过三维采集、互动故事和数字档案展示地方非遗项目，支持课程实践与公众传播。',
    },
    {
        'name': '实验室预约与安全巡检系统',
        'intro': '覆盖实验室预约、准入培训、设备台账和安全巡检闭环，降低日常管理成本。',
    },
    {
        'name': '社区志愿服务协同平台',
        'intro': '连接社区需求、志愿者排班和服务评价，形成可追踪的公益服务记录。',
    },
    {
        'name': '就业岗位智能匹配助手',
        'intro': '基于学生能力画像和岗位要求进行可解释匹配，并提供简历改进与学习建议。',
    },
    {
        'name': '智慧图书馆座位与资源导航',
        'intro': '提供座位预约、馆藏定位、学习空间热度分析和无障碍导航。',
    },
    {
        'name': '城市积水风险监测终端',
        'intro': '融合低功耗传感器与气象数据，对易涝点进行实时监测和分级预警。',
    },
    {
        'name': '校园食品安全追溯平台',
        'intro': '记录供应商、检验、入库和留样信息，为师生提供透明的食品安全查询。',
    },
    {
        'name': '面向老年人的反诈训练工具',
        'intro': '以情景化案例和语音交互开展反诈训练，帮助社区老人识别常见诈骗手法。',
    },
    {
        'name': '赛事材料智能核验助手',
        'intro': '按照比赛清单自动核验申报材料完整性、版本一致性和关键字段。',
    },
    {
        'name': '开源项目贡献成长地图',
        'intro': '聚合代码、文档、评审与社区协作记录，帮助成员形成可验证的成长档案。',
    },
    {
        'name': '乡村文旅路线共创平台',
        'intro': '支持村落资源采集、路线共创、游客反馈和运营数据复盘，服务乡村文旅实践。',
    },
    {
        'name': '多模态课堂互动分析系统',
        'intro': '在获得授权的前提下分析课堂互动数据，为教学改进提供聚合指标。',
    },
    {
        'name': '科研数据合规归档工具',
        'intro': '帮助项目团队完成数据分级、版本记录、授权确认和结项归档。',
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

        # 仅以本命令专属项目编号判断是否重复运行，避免与其他演示种子互相阻塞。
        if (
            not clean
            and Project.all_objects.filter(code__startswith=DEMO_PROJECT_PREFIX).exists()
        ):
            self.stdout.write(self.style.ERROR(
                '检测到数据库中已存在团队演示数据。'
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
                self.squads = []
                self.project_squad_by_leader_id = {}
                self.project_members = {}  # project -> [users]
                self.tasks_by_project = {}
                self.files_by_project = {}

                self.create_users()
                self.create_team_organization()
                self.create_projects()
                self.create_lifecycle_history()
                self.create_competitions()
                self.create_tasks()
                self.create_finance()
                self.create_demo_files()
                self.create_import_history()
                self.create_skills()
                self.create_work_schedules()
                self.create_contributions()
                self.create_rankings()
                self.create_scheduled_reports()
                self.create_ip_applications()
                self.create_portal_publications()
                self.create_sensitive_data()
                self.create_sensitive_requests()
                self.create_announcements()
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
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                'username': username,
                'name': name,
                'global_role': role,
                'grade': grade,
                'major': major,
                'is_student': is_student,
                'is_staff': is_staff,
                'is_superuser': is_superuser,
                'is_active': True,
                'phone': phone or gen_phone(),
                'membership_status': User.MembershipStatus.ACTIVE,
                'team_left_at': None,
                'exit_reason': '',
                'handover_to': None,
                'handover_notes': '',
            },
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
        self.users['leader4'] = self._make_user(
            'leader4@demo.com', 'leader4', 'leader123456', '陈雨桐',
            U.MEMBER, grade='研一', major='数据科学', phone='13800000007',
        )
        self.users['approver'] = self._make_user(
            'approver@demo.com', 'approver', 'approver123456', '审批员陈姐',
            U.SENS_APPROVER, is_student=False, is_staff=True,
            phone='13800000006',
        )

        self.leaders = [
            self.users['leader1'],
            self.users['leader2'],
            self.users['leader3'],
            self.users['leader4'],
        ]
        self.teachers = [self.users['teacher1'], self.users['teacher2']]

        used_names = {
            '系统管理员', '张老师', '李老师', '王明', '赵芳', '刘强',
            '陈雨桐', '审批员陈姐',
        }
        for i in range(1, 53):
            email = f'member{i}@demo.com'
            username = f'member{i}'
            name = gen_chinese_name(used_names)
            user = self._make_user(
                email, username, 'member123456', name, U.MEMBER,
                grade=random.choice(GRADES), major=random.choice(MAJORS),
            )
            self.members.append(user)
            self.users[f'member{i}'] = user

        preferred_themes = {
            'admin': 'blue',
            'teacher1': 'purple',
            'teacher2': 'green',
            'leader1': 'green',
            'leader2': 'blue',
            'leader3': 'purple',
            'leader4': 'orange',
            'leader5': 'green',
            'leader6': 'blue',
            'approver': 'orange',
        }
        theme_cycle = ('blue', 'green', 'purple', 'orange')
        notification_categories = (
            'system',
            'task',
            'project',
            'competition',
            'finance',
            'contribution',
            'schedule',
            'approval',
            'report',
        )
        for key, user in self.users.items():
            suffix = ''.join(character for character in key if character.isdigit())
            cycle_index = int(suffix) - 1 if suffix else user.pk
            theme = preferred_themes.get(
                key, theme_cycle[cycle_index % len(theme_cycle)]
            )
            member_number = int(suffix) if key.startswith('member') else 0
            if key == 'admin':
                profile = 'admin'
                default_landing = 'dashboard'
                sidebar_order = [
                    'workspace', 'execution', 'resources',
                    'outcomes', 'administration',
                ]
                favorite_routes = [
                    '/team', '/projects', '/finance', '/reports',
                ]
                saved_filters = {
                    'projects': {'status': ['active'], 'priority': ['high', 'urgent']},
                    'approvals': {'status': ['pending']},
                    'reports': {'period': 'this_month'},
                }
                digest = 'instant'
                channels = {'in_app': True, 'email': True}
                quiet_hours = {'enabled': False, 'start': '22:00', 'end': '07:30'}
                default_scope = 'team'
            elif member_number >= 49:
                profile = 'external'
                default_landing = 'tasks'
                sidebar_order = [
                    'workspace', 'execution', 'outcomes',
                    'resources', 'administration',
                ]
                favorite_routes = ['/tasks', '/files']
                saved_filters = {
                    'tasks': {'status': ['doing', 'need_help'], 'scope': 'mine'},
                    'projects': {'status': ['active'], 'scope': 'mine'},
                }
                digest = 'weekly'
                channels = {'in_app': True, 'email': False}
                quiet_hours = {'enabled': True, 'start': '21:30', 'end': '08:30'}
                default_scope = 'mine'
            elif key in {'teacher1', 'teacher2', 'approver'}:
                profile = 'teacher'
                default_landing = 'projects'
                sidebar_order = [
                    'workspace', 'outcomes', 'execution',
                    'resources', 'administration',
                ]
                favorite_routes = [
                    '/projects', '/competitions',
                    '/intellectual-property', '/reports',
                ]
                saved_filters = {
                    'projects': {'status': ['active', 'paused']},
                    'competitions': {'status': ['preparing', 'ongoing']},
                    'approvals': {'status': ['pending']},
                }
                digest = 'daily'
                channels = {'in_app': True, 'email': True}
                quiet_hours = {'enabled': True, 'start': '22:00', 'end': '07:00'}
                default_scope = 'team'
            else:
                profile = 'member'
                default_landing = (
                    'projects' if key.startswith('leader') else 'tasks'
                )
                sidebar_order = [
                    'workspace', 'execution', 'resources',
                    'outcomes', 'administration',
                ]
                favorite_routes = ['/tasks', '/projects', '/contributions']
                saved_filters = {
                    'tasks': {'status': ['todo', 'doing'], 'scope': 'mine'},
                    'projects': {'status': ['active'], 'scope': 'mine'},
                    'contributions': {'status': ['pending', 'approved']},
                }
                digest = 'daily' if cycle_index % 2 else 'instant'
                channels = {
                    'in_app': True,
                    'email': cycle_index % 3 == 0,
                }
                quiet_hours = {
                    'enabled': True,
                    'start': '22:30',
                    'end': '07:30',
                }
                default_scope = 'mine'

            categories = {
                category: not (
                    profile == 'external'
                    and category in {'finance', 'approval', 'report'}
                )
                for category in notification_categories
            }
            UserPreference.objects.update_or_create(
                user=user,
                defaults={
                    'theme_color': theme,
                    'primary_color': UserPreference.primary_color_for_theme(theme),
                    'theme_mode': UserPreference.DEFAULT_THEME_MODE,
                    'schedule_start': UserPreference.DEFAULT_SCHEDULE_START,
                    'schedule_end': UserPreference.DEFAULT_SCHEDULE_END,
                    'dashboard_layout': {
                        'profile': profile,
                        'cards': {
                            'admin': [
                                'business', 'signals', 'priority', 'delivery',
                            ],
                            'teacher': [
                                'signals', 'business', 'delivery', 'priority',
                            ],
                            'external': [
                                'delivery', 'priority', 'signals', 'business',
                            ],
                            'member': [
                                'priority', 'delivery', 'signals', 'business',
                            ],
                        }[profile],
                    },
                    'default_landing': default_landing,
                    'sidebar_collapsed': cycle_index % 3 == 0,
                    'notification_sound': cycle_index % 4 != 0,
                    'items_per_page': (10, 20, 50)[cycle_index % 3],
                    'default_scope': default_scope,
                    'sidebar_order': sidebar_order,
                    'favorite_routes': favorite_routes,
                    'saved_filters': saved_filters,
                    'notification_preferences': {
                        'categories': categories,
                        'channels': channels,
                        'quiet_hours': quiet_hours,
                        'digest': digest,
                    },
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'   账号创建完成：8 个固定账号 + {len(self.members)} 个普通成员'
        ))

    def create_team_organization(self):
        """创建一支完整团队，并为所有演示账户生成可追溯成员关系。"""
        self.stdout.write('-> 创建团队组织与成员关系...')
        owner = self.users['leader1']
        self.team, _ = Team.objects.update_or_create(
            code=DEMO_TEAM_CODE,
            defaults={
                'name': '数智创新实践团队',
                'description': (
                    '由指导老师、项目负责人、学生成员、顾问和外部协作者'
                    '共同组成的跨专业实践团队。'
                ),
                'contact_email': 'teacher1@demo.com',
                'join_message': (
                    '欢迎愿意持续投入真实项目、遵守协作规范并主动复盘的成员加入。'
                ),
                'is_active': True,
                'owner': owner,
            },
        )
        team_created_at = timezone.make_aware(
            datetime.combine(date(2022, 1, 10), time(9, 0))
        )
        Team.objects.filter(pk=self.team.pk).update(created_at=team_created_at)

        memberships = {}
        ordered_users = list(self.users.items())
        for index, (key, user) in enumerate(ordered_users):
            member_number = (
                int(key.removeprefix('member'))
                if key.startswith('member')
                else 0
            )
            if key == 'leader1':
                role = TeamMember.Role.OWNER
            elif key == 'admin':
                role = TeamMember.Role.ADMIN
            elif key in {'teacher1', 'teacher2'}:
                role = TeamMember.Role.TEACHER
            elif key == 'approver':
                role = TeamMember.Role.ADVISOR
            elif member_number >= 49:
                role = TeamMember.Role.EXTERNAL
            else:
                role = TeamMember.Role.MEMBER

            if 41 <= member_number <= 44:
                status = TeamMember.Status.ON_LEAVE
            elif 45 <= member_number <= 48:
                status = TeamMember.Status.EXITED
            else:
                status = TeamMember.Status.ACTIVE

            joined_at = team_created_at + timedelta(days=index * 11)
            membership = TeamMember.objects.create(
                team=self.team,
                user=user,
                role=role,
                status=status,
                left_at=(
                    joined_at + timedelta(days=760)
                    if status == TeamMember.Status.EXITED
                    else None
                ),
                exit_reason=(
                    f'{DEMO_MARKER}完成阶段性学习与项目交接'
                    if status == TeamMember.Status.EXITED
                    else ''
                ),
                handover_notes=(
                    f'{DEMO_MARKER}任务、文件与项目进展已完成交接'
                    if status == TeamMember.Status.EXITED
                    else ''
                ),
            )
            TeamMember.objects.filter(pk=membership.pk).update(joined_at=joined_at)
            membership.joined_at = joined_at
            memberships[key] = membership

            event = TeamMembershipEvent.objects.create(
                membership=membership,
                event_type='joined',
                to_role=role,
                to_status=TeamMember.Status.ACTIVE,
                reason=f'{DEMO_MARKER}加入数智创新实践团队',
                operator=owner,
            )
            TeamMembershipEvent.objects.filter(pk=event.pk).update(
                created_at=joined_at
            )

        handover_target = memberships['leader2']
        for member_number in range(41, 49):
            key = f'member{member_number}'
            membership = memberships[key]
            change_at = membership.joined_at + timedelta(days=700)
            event_type = (
                'status_changed'
                if membership.status == TeamMember.Status.ON_LEAVE
                else 'exited'
            )
            event = TeamMembershipEvent.objects.create(
                membership=membership,
                event_type=event_type,
                from_status=TeamMember.Status.ACTIVE,
                to_status=membership.status,
                reason=(
                    f'{DEMO_MARKER}学业安排暂离'
                    if membership.status == TeamMember.Status.ON_LEAVE
                    else f'{DEMO_MARKER}完成阶段性学习并离队'
                ),
                operator=owner,
            )
            TeamMembershipEvent.objects.filter(pk=event.pk).update(
                created_at=change_at
            )

            if membership.status == TeamMember.Status.EXITED:
                membership.handover_to = handover_target
                membership.save(update_fields=['handover_to'])
                handover_event = TeamMembershipEvent.objects.create(
                    membership=membership,
                    event_type='handover',
                    from_status=TeamMember.Status.ACTIVE,
                    to_status=TeamMember.Status.EXITED,
                    reason=f'{DEMO_MARKER}离队交接',
                    handover_to=handover_target,
                    handover_notes=membership.handover_notes,
                    operator=owner,
                )
                TeamMembershipEvent.objects.filter(
                    pk=handover_event.pk
                ).update(created_at=change_at + timedelta(minutes=5))

        # 二级小团队只增加额外归属关系，不改变根团队的 60 名成员及
        # 72 条根级事件。这样演示账号既能保留完整团队历史，也能真实
        # 展示“小团队负责人—共同负责人—执行成员”的日常协作结构。
        squad_specs = (
            {
                'code': DEMO_SQUAD_CODES[0],
                'name': '智能产品与软件组',
                'description': '负责产品设计、前后端开发、移动端与系统集成。',
                'owner_key': 'leader2',
                'co_lead_keys': ('leader1',),
                'teacher_keys': ('teacher1',),
                'member_keys': tuple(
                    f'member{number}' for number in range(1, 15)
                ),
            },
            {
                'code': DEMO_SQUAD_CODES[1],
                'name': '数据智能与视觉组',
                'description': '负责数据治理、算法模型、视觉分析与实验评估。',
                'owner_key': 'leader3',
                'co_lead_keys': ('member15',),
                'teacher_keys': ('teacher2',),
                'member_keys': tuple(
                    f'member{number}' for number in range(16, 29)
                ),
            },
            {
                'code': DEMO_SQUAD_CODES[2],
                'name': '赛事材料与运营组',
                'description': '负责比赛统筹、材料编制、答辩演练与成果运营。',
                'owner_key': 'leader4',
                'co_lead_keys': ('member29',),
                'teacher_keys': ('teacher1',),
                'member_keys': tuple(
                    f'member{number}' for number in range(30, 41)
                ),
            },
        )
        for squad_index, spec in enumerate(squad_specs):
            owner = self.users[spec['owner_key']]
            squad = Team.objects.create(
                code=spec['code'],
                name=spec['name'],
                description=spec['description'],
                contact_email=owner.email,
                join_message='由总团队统筹，根据项目和比赛需要开展跨组协作。',
                is_active=True,
                owner=owner,
                parent=self.team,
                team_type=Team.TeamType.SQUAD,
            )
            squad_created_at = team_created_at + timedelta(
                days=90 + squad_index * 30
            )
            Team.objects.filter(pk=squad.pk).update(
                created_at=squad_created_at
            )
            self.squads.append(squad)

            role_keys = (
                ((spec['owner_key'],), TeamMember.Role.OWNER),
                (spec['co_lead_keys'], TeamMember.Role.CO_LEAD),
                (spec['teacher_keys'], TeamMember.Role.TEACHER),
                (spec['member_keys'], TeamMember.Role.MEMBER),
            )
            membership_index = 0
            for user_keys, role in role_keys:
                for user_key in user_keys:
                    user = self.users[user_key]
                    joined_at = squad_created_at + timedelta(
                        days=membership_index * 3
                    )
                    squad_membership = TeamMember.objects.create(
                        team=squad,
                        user=user,
                        role=role,
                        status=TeamMember.Status.ACTIVE,
                    )
                    TeamMember.objects.filter(
                        pk=squad_membership.pk
                    ).update(joined_at=joined_at)
                    joined_event = TeamMembershipEvent.objects.create(
                        membership=squad_membership,
                        event_type='joined',
                        to_role=role,
                        to_status=TeamMember.Status.ACTIVE,
                        reason=f'{DEMO_MARKER}加入{spec["name"]}',
                        operator=owner,
                    )
                    TeamMembershipEvent.objects.filter(
                        pk=joined_event.pk
                    ).update(created_at=joined_at)
                    membership_index += 1

        self.project_squad_by_leader_id = {
            self.users['leader1'].id: self.squads[0],
            self.users['leader2'].id: self.squads[0],
            self.users['leader3'].id: self.squads[1],
            self.users['leader4'].id: self.squads[2],
        }

        self.stdout.write(self.style.SUCCESS(
            '   团队创建完成：成员 60 人，成员关系事件 72 条'
        ))
        self.stdout.write(self.style.SUCCESS(
            '   二级小团队创建完成：3 个，均已配置负责人、共同负责人和执行成员'
        ))

    # ------------------------------------------------------------------
    # 项目
    # ------------------------------------------------------------------
    def create_projects(self):
        self.stdout.write('-> 创建项目...')
        now = timezone.now()
        today = timezone.localdate()
        all_pool = self.members + self.leaders
        years = list(range(2022, today.year + 1))
        per_year_sequence = Counter()

        for idx, pdata in enumerate(PROJECT_DATA):
            year_index = min(
                (idx * len(years)) // len(PROJECT_DATA),
                len(years) - 1,
            )
            project_year = years[year_index]
            per_year_sequence[project_year] += 1
            code = (
                f'{DEMO_PROJECT_PREFIX}{project_year}-'
                f'{per_year_sequence[project_year]:02d}'
            )
            leader = self.leaders[idx % len(self.leaders)]
            month = 2 + (idx * 2) % 10
            start_date = date(project_year, month, 5 + idx % 18)
            if start_date >= today:
                start_date = today - timedelta(days=20 + idx)
            planned_end = start_date + timedelta(days=420 + (idx % 4) * 45)

            if (
                project_year <= today.year - 3
                or (project_year == today.year - 2 and idx % 2 == 0)
            ):
                status = Project.Status.CLOSED
                actual_end = min(
                    planned_end,
                    today - timedelta(days=30 + idx),
                )
                current_stage = Project.Stage.CLOSED
            elif idx in (17, 22):
                status = Project.Status.PAUSED
                actual_end = None
                current_stage = Project.Stage.PAUSED
            else:
                status = Project.Status.ACTIVE
                actual_end = None
                current_stage = min(
                    Project.Stage.AWARDED,
                    4 + max(0, today.year - project_year) * 2 + idx % 4,
                )

            priority = random.choice([
                Project.Priority.NORMAL, Project.Priority.NORMAL,
                Project.Priority.HIGH, Project.Priority.URGENT,
            ])

            if status == Project.Status.CLOSED:
                last_update = timezone.make_aware(
                    datetime.combine(actual_end, time(17, 30))
                )
            elif idx in (2, 6, 19):
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
            created_at = timezone.make_aware(
                datetime.combine(start_date, time(9, 0))
            )
            update_fields = {'created_at': created_at, 'updated_at': created_at}
            if actual_end:
                update_fields['archived_at'] = timezone.make_aware(
                    datetime.combine(actual_end, time(18, 0))
                )
            Project.all_objects.filter(pk=project.pk).update(**update_fields)
            self.projects.append(project)

            primary_squad = self.project_squad_by_leader_id[leader.id]
            linked_squads = [primary_squad]
            if idx % 5 == 0:
                primary_index = self.squads.index(primary_squad)
                linked_squads.append(
                    self.squads[(primary_index + 1) % len(self.squads)]
                )
            project.teams.set(linked_squads)

            # 每个项目 6~9 人，既有固定核心成员，也有跨项目协作者。
            member_count = 5 + idx % 4
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

    def create_lifecycle_history(self):
        """生成团队成员、项目成员和项目阶段的真实时间跨度记录。"""
        self.stdout.write('-> 创建成员与项目生命周期...')
        today = timezone.localdate()
        lifecycle_users = self.leaders + self.members
        years = list(range(2022, today.year + 1))

        for index, user in enumerate(lifecycle_users):
            joined_year = years[index % len(years)]
            joined_date = date(joined_year, 1 + index % 10, 3 + index % 20)
            status = User.MembershipStatus.ACTIVE
            team_left_at = None
            exit_reason = ''
            handover_to = None
            handover_notes = ''

            if index >= len(lifecycle_users) - 12:
                offset = index - (len(lifecycle_users) - 12)
                if offset < 4:
                    status = User.MembershipStatus.ON_LEAVE
                elif offset < 8:
                    status = User.MembershipStatus.EXITED
                    team_left_at = timezone.now() - timedelta(days=20 + offset)
                    exit_reason = '学业阶段变化，完成资料与任务交接后离队。'
                    handover_to = self.leaders[offset % len(self.leaders)]
                    handover_notes = '代码仓库、项目材料与未结任务均已完成清单式交接。'
                else:
                    status = User.MembershipStatus.EXTERNAL

            User.objects.filter(pk=user.pk).update(
                team_joined_at=joined_date,
                membership_status=status,
                is_active=status != User.MembershipStatus.EXITED,
                team_left_at=team_left_at,
                exit_reason=exit_reason,
                handover_to=handover_to,
                handover_notes=handover_notes,
            )
            user.team_joined_at = joined_date
            user.membership_status = status
            user.is_active = status != User.MembershipStatus.EXITED

            joined_event = UserLifecycleEvent.objects.create(
                user=user,
                event_type=UserLifecycleEvent.EventType.CREATED,
                to_status=User.MembershipStatus.ACTIVE,
                reason=f'{DEMO_MARKER}经面试与试做任务后加入团队。',
                operator=self.teachers[index % len(self.teachers)],
            )
            joined_at = timezone.make_aware(
                datetime.combine(joined_date, time(10, 0))
            )
            UserLifecycleEvent.objects.filter(pk=joined_event.pk).update(
                created_at=joined_at
            )

            if status != User.MembershipStatus.ACTIVE:
                change_event = UserLifecycleEvent.objects.create(
                    user=user,
                    event_type=UserLifecycleEvent.EventType.STATUS_CHANGED,
                    from_status=User.MembershipStatus.ACTIVE,
                    to_status=status,
                    reason=f'{DEMO_MARKER}{exit_reason or "根据学习安排调整团队参与状态。"}',
                    handover_to=handover_to,
                    handover_notes=handover_notes,
                    operator=self.teachers[index % len(self.teachers)],
                )
                event_time = team_left_at or (timezone.now() - timedelta(days=7 + index))
                UserLifecycleEvent.objects.filter(pk=change_event.pk).update(
                    created_at=event_time
                )

        stage_flow = [
            Project.Stage.CONCEIVING,
            Project.Stage.APPROVED,
            Project.Stage.MATERIAL_PREP,
            Project.Stage.DEV_EXPERIMENT,
            Project.Stage.MATERIAL_SUBMIT,
            Project.Stage.DEFENSE_PREP,
            Project.Stage.SCHOOL_COMP,
            Project.Stage.PROVINCE_COMP,
            Project.Stage.NATIONAL_COMP,
            Project.Stage.AWARDED,
            Project.Stage.CLOSED,
        ]
        membership_event_count = 0
        stage_log_count = 0

        for project_index, project in enumerate(self.projects):
            project_start = timezone.make_aware(
                datetime.combine(project.start_date, time(9, 0))
            )
            if project.status == Project.Status.PAUSED:
                stages = stage_flow[:4] + [Project.Stage.PAUSED]
            else:
                stages = [
                    stage for stage in stage_flow
                    if stage <= project.current_stage
                ]
            previous_stage = None
            for stage_index, stage in enumerate(stages):
                log = ProjectStageLog.objects.create(
                    project=project,
                    from_stage=previous_stage,
                    to_stage=stage,
                    operator=project.leader,
                    note=f'{DEMO_MARKER}{project.code} 完成“{Project.Stage(stage).label}”节点。',
                )
                ProjectStageLog.objects.filter(pk=log.pk).update(
                    created_at=project_start + timedelta(days=stage_index * 35)
                )
                previous_stage = stage
                stage_log_count += 1

            memberships = list(
                ProjectMember.objects.filter(project=project).order_by('id')
            )
            for member_index, membership in enumerate(memberships):
                joined_at = project_start + timedelta(days=member_index * 3)
                ProjectMember.objects.filter(pk=membership.pk).update(
                    joined_at=joined_at
                )
                joined = ProjectMembershipEvent.objects.create(
                    membership=membership,
                    event_type=ProjectMembershipEvent.EventType.JOINED,
                    to_role=membership.role_in_project,
                    to_status=ProjectMember.Status.ACTIVE,
                    reason=f'{DEMO_MARKER}按项目阶段需要加入团队。',
                    operator=project.leader,
                )
                ProjectMembershipEvent.objects.filter(pk=joined.pk).update(
                    created_at=joined_at
                )
                membership_event_count += 1

            candidates = [m for m in memberships if m.user_id != project.leader_id]
            if not candidates:
                continue
            target = candidates[-1]
            handover = candidates[0] if candidates[0].pk != target.pk else memberships[0]
            if project_index % 3 == 0:
                exited_at = min(
                    timezone.now() - timedelta(days=10 + project_index),
                    project_start + timedelta(days=180),
                )
                ProjectMember.objects.filter(pk=target.pk).update(
                    status=ProjectMember.Status.EXITED,
                    exited_at=exited_at,
                    exit_reason='课程与实习安排变化，退出当前项目。',
                    handover_to=handover,
                    handover_notes='已交接材料目录、任务进度和后续联系人。',
                )
                event = ProjectMembershipEvent.objects.create(
                    membership=target,
                    event_type=ProjectMembershipEvent.EventType.EXITED,
                    from_status=ProjectMember.Status.ACTIVE,
                    to_status=ProjectMember.Status.EXITED,
                    reason=f'{DEMO_MARKER}课程与实习安排变化，退出当前项目。',
                    handover_to=handover,
                    handover_notes='已交接材料目录、任务进度和后续联系人。',
                    operator=project.leader,
                )
                ProjectMembershipEvent.objects.filter(pk=event.pk).update(
                    created_at=exited_at
                )
                membership_event_count += 1
            elif project_index % 3 == 1:
                ProjectMember.objects.filter(pk=target.pk).update(
                    status=ProjectMember.Status.ON_LEAVE,
                    exit_reason='考试周期间暂离项目。',
                )
                event = ProjectMembershipEvent.objects.create(
                    membership=target,
                    event_type=ProjectMembershipEvent.EventType.STATUS_CHANGED,
                    from_status=ProjectMember.Status.ACTIVE,
                    to_status=ProjectMember.Status.ON_LEAVE,
                    reason=f'{DEMO_MARKER}考试周期间暂离项目，结束后恢复参与。',
                    operator=project.leader,
                )
                ProjectMembershipEvent.objects.filter(pk=event.pk).update(
                    created_at=timezone.now() - timedelta(days=5 + project_index)
                )
                membership_event_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'   生命周期创建完成：成员事件 {UserLifecycleEvent.objects.filter(reason__startswith=DEMO_MARKER).count()} 条，'
            f'项目成员事件 {membership_event_count} 条，阶段日志 {stage_log_count} 条'
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
        task_titles = [
            '需求调研与整理', '原型设计', '数据库表结构设计', '接口文档编写',
            '前端页面开发', '后端接口开发', '核心算法实现', '单元测试编写',
            '系统集成联调', '用户手册撰写', '答辩PPT制作', '比赛报名材料准备',
            '软件说明书撰写', '源代码文档整理', '性能优化', '部署上线',
            'Bug 修复与回归', '数据采集与清洗', '模型训练与调优', 'UI 视觉规范制定',
        ]
        active_statuses = [
            Task.Status.TODO,
            Task.Status.DOING,
            Task.Status.PENDING_REVIEW,
            Task.Status.DONE,
            Task.Status.OVERDUE,
            Task.Status.NEED_HELP,
        ]
        total = 0
        for pidx, project in enumerate(self.projects):
            members = self.project_members[project.id]
            leader = project.leader
            project_tasks = []
            project_started_at = timezone.make_aware(
                datetime.combine(project.start_date, time(9, 0))
            )
            for task_index in range(5):
                if project.status == Project.Status.CLOSED:
                    status = (
                        Task.Status.CANCELLED
                        if task_index == 4 and pidx % 2
                        else Task.Status.DONE
                    )
                elif project.status == Project.Status.PAUSED:
                    status = (
                        Task.Status.PAUSED if task_index >= 3 else Task.Status.DONE
                    )
                else:
                    status = active_statuses[
                        (pidx + task_index) % len(active_statuses)
                    ]

                assignee = members[(pidx + task_index) % len(members)]
                title = task_titles[
                    (pidx * 5 + task_index) % len(task_titles)
                ]
                title = f'{title}（{project.code}）'
                deadline = None
                completed_at = None
                overdue_reminded = False
                task_created_at = min(
                    now - timedelta(days=1),
                    project_started_at + timedelta(days=20 + task_index * 28),
                )
                started_at = task_created_at + timedelta(days=1)

                if status in (
                    Task.Status.TODO,
                    Task.Status.DOING,
                    Task.Status.NEED_HELP,
                ):
                    deadline = now + timedelta(days=random.randint(2, 14))
                elif status == Task.Status.PENDING_REVIEW:
                    deadline = now - timedelta(days=1)
                elif status == Task.Status.DONE:
                    completed_at = min(
                        now - timedelta(days=1),
                        task_created_at + timedelta(days=12),
                    )
                    deadline = completed_at + timedelta(days=2)
                elif status == Task.Status.OVERDUE:
                    deadline = now - timedelta(days=3 + task_index)
                    overdue_reminded = True
                elif status == Task.Status.PAUSED:
                    deadline = now + timedelta(days=30)
                elif status == Task.Status.CANCELLED:
                    deadline = task_created_at + timedelta(days=10)

                reviewer = (
                    leader
                    if status in (Task.Status.PENDING_REVIEW, Task.Status.DONE)
                    else None
                )
                completion_note = ''
                if status == Task.Status.PENDING_REVIEW:
                    completion_note = (
                        '本轮交付物与说明已上传，关键检查项已自测通过，'
                        '现提交负责人复核。'
                    )
                elif status == Task.Status.DONE:
                    completion_note = (
                        '交付物已完成并通过负责人验收，相关文件已归入项目档案。'
                    )
                task = Task.objects.create(
                    project=project,
                    title=title,
                    assignee=assignee,
                    creator=leader,
                    status=status,
                    priority=(
                        Task.Priority.HIGH
                        if task_index in (1, 4)
                        else Task.Priority.MEDIUM
                    ),
                    start_date=started_at,
                    deadline=deadline,
                    completed_at=completed_at,
                    overdue_reminded=overdue_reminded,
                    reviewer=reviewer,
                    description=f'本项目「{project.name}」的{title}任务，由{assignee.name}负责。',
                    delay_reason=(
                        '等待外部数据确认，已同步负责人。'
                        if status in (Task.Status.OVERDUE, Task.Status.NEED_HELP)
                        else ''
                    ),
                    completion_note=completion_note,
                )
                Task.all_objects.filter(pk=task.pk).update(
                    created_at=task_created_at,
                    updated_at=completed_at or task_created_at,
                )
                collaborator = members[
                    (pidx + task_index + 1) % len(members)
                ]
                if collaborator.pk != assignee.pk:
                    task.collaborators.add(collaborator)
                project_tasks.append(task)
                total += 1
            self.tasks_by_project[project.id] = project_tasks

        self.stdout.write(self.style.SUCCESS(f'   任务创建完成：{total} 个'))

    # ------------------------------------------------------------------
    # 经费
    # ------------------------------------------------------------------
    @staticmethod
    def _build_receipt_png(project, expense, receipt_index):
        """生成可被 Pillow 与 OCR 校验的简洁英文票据图片。"""
        image = PILImage.new('RGB', (960, 420), color='#ffffff')
        draw = ImageDraw.Draw(image)
        font_candidates = (
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        )
        font_path = next((path for path in font_candidates if path.exists()), None)
        font = (
            ImageFont.truetype(str(font_path), 38)
            if font_path
            else ImageFont.load_default()
        )
        small_font = (
            ImageFont.truetype(str(font_path), 28)
            if font_path
            else ImageFont.load_default()
        )
        draw.rounded_rectangle(
            (28, 28, 932, 392),
            radius=18,
            outline='#176b73',
            width=4,
            fill='#f8fbfb',
        )
        draw.text((72, 72), 'DEMO SUPPLY STORE', fill='#17353a', font=font)
        draw.text(
            (72, 165),
            f'DATE: {expense.expense_date.isoformat()}    '
            f'NO: {project.code[-10:]}-{expense.pk}-{receipt_index}',
            fill='#334e52',
            font=small_font,
        )
        draw.text(
            (72, 260),
            f'TOTAL: {expense.amount:.2f}',
            fill='#176b73',
            font=font,
        )
        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()

    def create_finance(self):
        self.stdout.write('-> 创建经费数据...')
        now = timezone.now()
        budget_count = 0
        income_count = 0
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
            FinanceIncome.objects.create(
                project=project,
                title='比赛奖金入账',
                amount=bonus,
                income_type=FinanceIncome.IncomeType.BONUS,
                income_date=(now - timedelta(days=random.randint(30, 90))).date(),
                source='赛事主办方',
                reference_number=f'DEMO-BONUS-{project.id:04d}',
                recorded_by=project.leader,
            )
            income_count += 1
            if other_income:
                FinanceIncome.objects.create(
                    project=project,
                    title='项目配套经费',
                    amount=other_income,
                    income_type=FinanceIncome.IncomeType.GRANT,
                    income_date=(now - timedelta(days=random.randint(10, 45))).date(),
                    source='团队项目经费',
                    reference_number=f'DEMO-GRANT-{project.id:04d}',
                    recorded_by=project.leader,
                )
                income_count += 1

            # 生成 2~3 条支出，覆盖草稿、待审核、已审核、已付款状态。
            expense_num = random.randint(2, 3)
            workflow_statuses = [
                FinanceExpense.ReimbursementStatus.PAID,
                FinanceExpense.ReimbursementStatus.PENDING,
                FinanceExpense.ReimbursementStatus.APPROVED,
            ]
            for expense_index in range(expense_num):
                category = random.choice(list(expense_titles.keys()))
                amount = Decimal(random.randint(100, 5000))
                spender = random.choice(members)
                expense_date = (now - timedelta(days=random.randint(1, 60))).date()
                reimbursement_status = workflow_statuses[expense_index % len(workflow_statuses)]
                expense = FinanceExpense.objects.create(
                    project=project,
                    title=expense_titles[category],
                    amount=amount,
                    spender=spender,
                    expense_date=expense_date,
                    category=category,
                    purpose=f'{project.name} - {expense_titles[category]}，用于项目推进所需。',
                    reimbursement_status=reimbursement_status,
                    applied_by=spender,
                    applied_at=now - timedelta(days=max(1, 8 - expense_index)),
                    reviewer=project.leader if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else None,
                    reviewed_at=now - timedelta(days=max(1, 6 - expense_index)) if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else None,
                    review_opinion='票据与用途核验通过。' if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else '',
                    paid_by=project.leader if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else None,
                    paid_at=now - timedelta(days=2) if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else None,
                    payment_method='银行转账' if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else '',
                    payment_reference=f'DEMO-PAY-{project.id:04d}-{expense_index + 1}' if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else '',
                )
                expense_count += 1

                # 为每条支出创建 1~2 张模拟票据
                for _r in range(random.randint(1, 2)):
                    receipt = FinanceReceipt(
                        expense=expense,
                        uploaded_by=spender,
                    )
                    receipt_data = self._build_receipt_png(
                        project,
                        expense,
                        _r + 1,
                    )
                    receipt.file.save(
                        f'receipt_{project.id}_{expense.id}_{_r+1}.png',
                        ContentFile(receipt_data),
                        save=True,
                    )
                    receipt_count += 1

            budget = FinanceBudget.objects.filter(project=project).order_by('-updated_at').first()
            budget.period = now.strftime('%Y-%m')
            budget.save(update_fields=['period', 'updated_at'])
            budget_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'   经费创建完成：收入 {income_count} 条，预算 {budget_count} 条，'
            f'支出 {expense_count} 条，票据 {receipt_count} 条'
        ))

    def backend_dir(self):
        return Path(__file__).resolve().parents[4]

    def assets_dir(self):
        return self.backend_dir() / 'seed_assets' / 'competition_demo_files'

    def _project_document_lines(self, project):
        return [
            f'项目名称：{project.name}',
            f'项目编号：{project.code}',
            f'项目负责人：{project.leader.name}',
            f'项目摘要：{project.intro[:90]}',
            '说明：本文件由团队演示数据命令按当前项目动态生成。',
        ]

    @staticmethod
    def _pdf_font_name():
        """注册能嵌入中文并保留文本映射的 PDF 字体。"""
        font_name = 'SeedDemoCJK'
        if font_name in pdfmetrics.getRegisteredFontNames():
            return font_name
        candidates = (
            Path('C:/Windows/Fonts/simhei.ttf'),
            Path('C:/Windows/Fonts/simsunb.ttf'),
            Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
            Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
            Path('/usr/share/fonts/truetype/arphic/uming.ttc'),
        )
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
                return font_name
            except Exception:
                continue

        # 最后使用 ReportLab 内置中文字体，保证最小环境仍能生成合法 PDF。
        fallback_name = 'STSong-Light'
        if fallback_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont(fallback_name))
        return fallback_name

    def _build_project_pdf(self, project):
        buffer = BytesIO()
        document = canvas.Canvas(buffer, pagesize=A4)
        document.setTitle(f'{project.code} {project.name}')
        document.setAuthor(project.leader.name)
        font_name = self._pdf_font_name()
        document.setFont(font_name, 20)
        document.drawString(54, 790, '团队项目概览')
        document.setFont(font_name, 12)
        y = 744
        for line in self._project_document_lines(project):
            for segment_start in range(0, len(line), 38):
                document.drawString(
                    54,
                    y,
                    line[segment_start:segment_start + 38],
                )
                y -= 25
            y -= 8
        document.save()
        return buffer.getvalue()

    def _build_project_docx(self, project):
        document = Document()
        document.add_heading('团队项目工作计划', level=1)
        for line in self._project_document_lines(project):
            document.add_paragraph(line)
        document.add_paragraph('下一步：完成当前阶段任务并更新项目进展。')
        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _build_project_xlsx(self, project):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = '项目简表'
        worksheet.append(['字段', '内容'])
        worksheet.append(['项目名称', project.name])
        worksheet.append(['项目编号', project.code])
        worksheet.append(['项目负责人', project.leader.name])
        worksheet.append(['项目摘要', project.intro[:90]])
        worksheet.append(['数据说明', '本工作簿由团队演示数据命令动态生成'])
        worksheet.column_dimensions['A'].width = 18
        worksheet.column_dimensions['B'].width = 72
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def _build_project_pptx(self, project):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = project.name
        body = slide.placeholders[1].text_frame
        body.clear()
        for index, line in enumerate(self._project_document_lines(project)[1:]):
            paragraph = body.paragraphs[0] if index == 0 else body.add_paragraph()
            paragraph.text = line
        buffer = BytesIO()
        presentation.save(buffer)
        return buffer.getvalue()

    def _build_project_file(self, project, suffix):
        builders = {
            '.pdf': self._build_project_pdf,
            '.docx': self._build_project_docx,
            '.xlsx': self._build_project_xlsx,
            '.pptx': self._build_project_pptx,
        }
        try:
            return builders[suffix](project)
        except KeyError as exc:
            raise CommandError(f'不支持的演示文件类型：{suffix}') from exc

    def create_demo_files(self):
        """按当前项目内容动态创建四种文件，并关联版本和任务附件。"""
        self.stdout.write('-> 创建项目文件、版本与任务附件...')

        created_files = []
        version_count = 0
        for project in self.projects:
            project_files = []
            for label, suffix, content_type, level in FILE_SPECS:
                data = self._build_project_file(project, suffix)
                version = 2 if suffix == '.docx' else 1
                asset = FileAsset(
                    project=project,
                    name=f'{project.code} {label}{suffix}',
                    level=level,
                    size=len(data),
                    content_type=content_type,
                    uploader=project.leader,
                    version=version,
                    watermark_text=(
                        f'{DEMO_MARKER}{project.code}'
                        if level == FileAsset.Level.PUBLIC
                        else ''
                    ),
                )
                storage_name = (
                    f'{DEMO_IMPORT_DIRNAME}/{project.code}_'
                    f'{suffix.lstrip(".")}{suffix}'
                )
                asset.file.save(storage_name, ContentFile(data), save=True)
                project_files.append(asset)
                created_files.append(asset)

                if suffix == '.docx':
                    historical = FileVersion(
                        file_asset=asset,
                        version=1,
                        uploader=project.leader,
                    )
                    historical.file.save(
                        f'{DEMO_IMPORT_DIRNAME}/{project.code}_work_plan_v1.docx',
                        ContentFile(data),
                        save=True,
                    )
                    version_count += 1

            self.files_by_project[project.id] = project_files
            tasks = self.tasks_by_project.get(project.id, [])
            if tasks:
                tasks[0].attachment_files.add(project_files[0], project_files[1])
            if len(tasks) > 1:
                tasks[1].attachment_files.add(project_files[2])
            if len(tasks) > 2:
                tasks[2].attachment_files.add(project_files[3])

        extension_counts = Counter(
            Path(asset.file.name).suffix.lower() for asset in created_files
        )
        self.stdout.write(self.style.SUCCESS(
            f'   文件创建完成：{len(created_files)} 个，历史版本 {version_count} 个，'
            f'PDF/DOCX/XLSX/PPTX = '
            f'{extension_counts[".pdf"]}/{extension_counts[".docx"]}/'
            f'{extension_counts[".xlsx"]}/{extension_counts[".pptx"]}'
        ))

    def create_import_history(self):
        """创建所有可导入模块的历史记录，并保留可读取的演示源文件。"""
        self.stdout.write('-> 创建导入历史...')
        source_files = sorted(self.assets_dir().rglob('*.xlsx'))
        if not source_files:
            raise CommandError('缺少 XLSX 演示模板，无法创建导入历史')

        import_dir = (
            Path(settings.MEDIA_ROOT)
            / 'imports'
            / DEMO_IMPORT_DIRNAME
        )
        import_dir.mkdir(parents=True, exist_ok=True)
        project = self.projects[0]
        member = self.members[0]
        definitions = [
            {
                'module': ImportTask.Module.PROJECTS,
                'status': ImportTask.Status.CONFIRMED,
                'mapping': {'项目名称': 'name', '项目编号': 'code', '负责人邮箱': 'leader_email'},
                'rows': [{'项目名称': project.name, '项目编号': project.code, '负责人邮箱': project.leader.email}],
            },
            {
                'module': ImportTask.Module.HISTORY_PROJECTS,
                'status': ImportTask.Status.ROLLED_BACK,
                'mapping': {'项目名称': 'name', '项目编号': 'code', '实际结束日期': 'actual_end_date'},
                'rows': [{'项目名称': self.projects[1].name, '项目编号': self.projects[1].code, '实际结束日期': str(self.projects[1].actual_end_date or '')}],
            },
            {
                'module': ImportTask.Module.MEMBERS,
                'status': ImportTask.Status.CONFIRMED,
                'mapping': {'姓名': 'name', '邮箱': 'email', '成员状态': 'membership_status'},
                'rows': [{'姓名': member.name, '邮箱': member.email, '成员状态': member.membership_status}],
            },
            {
                'module': ImportTask.Module.COMPETITIONS,
                'status': ImportTask.Status.PREVIEWED,
                'mapping': {'比赛名称': 'name', '项目编号': 'project_code', '级别': 'level'},
                'rows': [{'比赛名称': COMPETITION_DATA[0]['name'], '项目编号': project.code, '级别': 'national'}],
            },
            {
                'module': ImportTask.Module.TASKS,
                'status': ImportTask.Status.CONFIRMED,
                'mapping': {'任务标题': 'title', '项目编号': 'project_code', '负责人邮箱': 'assignee_email'},
                'rows': [{'任务标题': self.tasks_by_project[project.id][0].title, '项目编号': project.code, '负责人邮箱': member.email}],
            },
            {
                'module': ImportTask.Module.FINANCE,
                'status': ImportTask.Status.FAILED,
                'mapping': {'支出标题': 'title', '金额': 'amount', '项目编号': 'project_code', '支出日期': 'expense_date'},
                'rows': [{'支出标题': '调研交通费', '金额': '待确认', '项目编号': project.code, '支出日期': str(timezone.localdate())}],
                'errors': {'1': ['金额格式不正确，请填写数字。']},
            },
            {
                'module': ImportTask.Module.IP_APPLICATIONS,
                'status': ImportTask.Status.PREVIEWED,
                'mapping': {'成果名称': 'title', '内部编号': 'application_code', '关联项目编号': 'related_project_code'},
                'rows': [{'成果名称': '校园导览软件', '内部编号': f'{DEMO_IP_PREFIX}PREVIEW', '关联项目编号': project.code}],
            },
        ]

        for index, definition in enumerate(definitions):
            source = source_files[index % len(source_files)]
            destination = import_dir / f'{index + 1:02d}_{definition["module"]}.xlsx'
            destination.write_bytes(source.read_bytes())
            rows = definition['rows']
            errors = definition.get('errors', {})
            headers = list(rows[0].keys()) if rows else []
            import_task = ImportTask.objects.create(
                module=definition['module'],
                file_path=str(destination),
                status=definition['status'],
                field_mapping=definition['mapping'],
                preview_data={
                    'headers': headers,
                    'rows': rows,
                    'total_preview': len(rows),
                },
                snapshot=[],
                total_rows=len(rows),
                valid_rows=len(rows) - len(errors),
                error_rows=len(errors),
                error_details=errors,
                created_by=self.users['admin'],
            )
            ImportTask.objects.filter(pk=import_task.pk).update(
                created_at=timezone.now() - timedelta(days=21 - index * 3),
                updated_at=timezone.now() - timedelta(days=20 - index * 3),
            )

        self.stdout.write(self.style.SUCCESS(
            f'   导入历史创建完成：{len(definitions)} 条，覆盖全部模块'
        ))

    # ------------------------------------------------------------------
    # 技能标签与成员技能
    # ------------------------------------------------------------------
    def create_skills(self):
        self.stdout.write('-> 创建技能标签与成员技能...')
        skills = []
        for name in SKILL_NAMES:
            skill, _ = SkillTag.objects.get_or_create(name=name)
            skills.append(skill)

        all_members = self.members + self.leaders
        # 为约 20 个成员分配 2~3 个技能
        chosen_members = random.sample(all_members, min(20, len(all_members)))
        count = 0
        for user in chosen_members:
            num = random.randint(2, 3)
            picked = random.sample(skills, num)
            for skill in picked:
                MemberSkill.objects.update_or_create(
                    user=user,
                    skill=skill,
                    defaults={'proficiency': random.randint(1, 5)},
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
            FlexibleWorkSchedule.objects.update_or_create(
                user=user,
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'work_hours': work_hours,
                    'detail': detail,
                    'can_offline': random.choice([True, False]),
                    'can_urgent': random.choice([True, False]),
                    'is_saturated': random.choice([True, False, False]),
                    'notes': (
                        f'{DEMO_MARKER}'
                        + random.choice([
                            '本周期安排稳定',
                            '近期有考试，工时偏少',
                            '可接受紧急任务',
                            '已满负荷',
                        ])
                    ),
                },
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
            contribution_summary = random.choice(contents)
            content = (
                f'{user.name}在「{project.name}」中'
                f'{contribution_summary}'
            )
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
    # 定时报表
    # ------------------------------------------------------------------
    def create_scheduled_reports(self):
        """创建可直接下载、也可继续按计划运行的三种格式演示报表。"""
        self.stdout.write('-> 创建定时报表与成功执行记录...')
        now = timezone.now()
        definitions = [
            {
                'name': '每日项目执行概览',
                'description': '每天汇总进行中、暂停及已结项项目。',
                'report_type': CustomReport.ReportType.SUMMARY,
                'config': {
                    'data_source': 'project',
                    'group_by': 'status',
                    'chart_type': 'table',
                    'filters': {},
                },
                'creator': self.users['admin'],
                'recipients': [
                    self.users['admin'],
                    self.users['teacher1'],
                ],
                'frequency': ScheduledReport.Frequency.DAILY,
                'execution_time': time(8, 30),
                'file_format': ScheduledReport.FileFormat.XLSX,
                'project': self.projects[0],
                'schedule_cron': '30 8 * * *',
            },
            {
                'name': '每周任务交付简报',
                'description': '每周汇总任务完成、审核及延期情况。',
                'report_type': CustomReport.ReportType.TREND,
                'config': {
                    'data_source': 'task',
                    'group_by': 'project',
                    'chart_type': 'table',
                    'filters': {},
                },
                'creator': self.users['teacher1'],
                'recipients': [
                    self.users['teacher1'],
                    self.users['leader1'],
                ],
                'frequency': ScheduledReport.Frequency.WEEKLY,
                'execution_time': time(9, 0),
                'weekday': 0,
                'file_format': ScheduledReport.FileFormat.DOCX,
                'project': self.projects[1],
                'schedule_cron': '0 9 * * 1',
            },
            {
                'name': '每月经费执行报告',
                'description': '每月汇总项目支出和经费使用结构。',
                'report_type': CustomReport.ReportType.COMPARISON,
                'config': {
                    'data_source': 'finance',
                    'group_by': 'project',
                    'chart_type': 'table',
                    'filters': {},
                },
                'creator': self.users['leader1'],
                'recipients': [
                    self.users['leader1'],
                    self.users['teacher2'],
                ],
                'frequency': ScheduledReport.Frequency.MONTHLY,
                'execution_time': time(10, 0),
                'day_of_month': 5,
                'file_format': ScheduledReport.FileFormat.PDF,
                'project': self.projects[2],
                'schedule_cron': '0 10 5 * *',
            },
        ]
        builders = {
            ScheduledReport.FileFormat.XLSX: self._build_project_xlsx,
            ScheduledReport.FileFormat.DOCX: self._build_project_docx,
            ScheduledReport.FileFormat.PDF: self._build_project_pdf,
        }

        for index, definition in enumerate(definitions, start=1):
            report = CustomReport.objects.create(
                name=f'{DEMO_MARKER}{definition["name"]}',
                description=definition['description'],
                report_type=definition['report_type'],
                config=definition['config'],
                created_by=definition['creator'],
                is_scheduled=True,
                schedule_cron=definition['schedule_cron'],
            )
            schedule = ScheduledReport.objects.create(
                report=report,
                created_by=definition['creator'],
                frequency=definition['frequency'],
                execution_time=definition['execution_time'],
                weekday=definition.get('weekday', 0),
                day_of_month=definition.get('day_of_month', 1),
                timezone='Asia/Shanghai',
                file_format=definition['file_format'],
                last_run=now,
                last_status=ScheduledReport.RunStatus.SUCCESS,
                is_active=True,
            )
            schedule.recipients.set(definition['recipients'])
            schedule.next_run = compute_next_run(schedule, base=now)
            schedule.save(update_fields=['next_run'])

            content = builders[definition['file_format']](
                definition['project']
            )
            file_name = (
                f'{definition["name"]}.{definition["file_format"]}'
            )
            execution = ScheduledReportExecution(
                schedule=schedule,
                trigger=ScheduledReportExecution.Trigger.SCHEDULED,
                status=ScheduledReport.RunStatus.SUCCESS,
                file_name=file_name,
                file_format=definition['file_format'],
                file_size=len(content),
                delivery_status=(
                    ScheduledReportExecution.DeliveryStatus.NOT_REQUESTED
                ),
                recipient_snapshot=[
                    {
                        'id': recipient.pk,
                        'name': recipient.name,
                        'email': recipient.email,
                    }
                    for recipient in definition['recipients']
                ],
                message='演示报表已生成并保留站内文件，未实际发送邮件。',
                finished_at=now,
                generated_by=definition['creator'],
            )
            execution.file.save(
                (
                    f'{DEMO_IMPORT_DIRNAME}/scheduled_report_{index}.'
                    f'{definition["file_format"]}'
                ),
                ContentFile(content),
                save=False,
            )
            execution.save()

        self.stdout.write(self.style.SUCCESS(
            '   定时报表创建完成：3 个计划、3 个成功执行文件'
        ))

    # ------------------------------------------------------------------
    # 知识产权申请
    # ------------------------------------------------------------------
    def _build_ip_certificate_pdf(
        self,
        project,
        application_code,
        title,
        authorized_date,
    ):
        """生成可核验、内容明确的小型演示授权登记证书 PDF。"""
        buffer = BytesIO()
        document = canvas.Canvas(buffer, pagesize=A4)
        document.setTitle(f'{application_code} 授权登记证书')
        document.setAuthor('团队管理软件演示数据')
        font_name = self._pdf_font_name()
        document.setFont(font_name, 20)
        document.drawCentredString(297, 775, '知识产权授权登记证书（演示）')
        document.setFont(font_name, 12)
        lines = (
            f'申请编号：{application_code}',
            f'成果名称：{title}',
            f'关联项目：{project.code} {project.name}',
            f'项目负责人：{project.leader.name}',
            f'授权登记日期：{authorized_date.isoformat()}',
            '证书状态：授权登记完成，可进入成果归档流程。',
            '说明：本证书由 seed_demo_data 生成，仅用于系统功能演示。',
        )
        y = 710
        for line in lines:
            document.drawString(72, y, line)
            y -= 38
        document.rect(54, 440, 487, 320)
        document.save()
        return buffer.getvalue()

    def _create_ip_certificate_asset(
        self,
        project,
        application_code,
        title,
        authorized_date,
    ):
        """创建独立内部证书文件，避免把普通项目文档冒充授权证书。"""
        content = self._build_ip_certificate_pdf(
            project,
            application_code,
            title,
            authorized_date,
        )
        certificate = FileAsset(
            project=project,
            name=f'{application_code} 最终授权登记证书.pdf',
            level=FileAsset.Level.INTERNAL,
            size=len(content),
            content_type='application/pdf',
            uploader=project.leader,
        )
        certificate.file.save(
            f'{DEMO_IMPORT_DIRNAME}/{application_code}_certificate.pdf',
            ContentFile(content),
            save=True,
        )
        return certificate

    def create_ip_applications(self):
        self.stdout.write('-> 创建知识产权申请...')
        now = timezone.now()

        def pick_members(project, n):
            members = self.project_members[project.id]
            return random.sample(members, min(n, len(members)))

        # --- 1. 智能校园导览系统 软著 - 已授权 ---
        p1 = self.projects[0]
        writer1 = p1.leader
        ip1_code = f'{DEMO_IP_PREFIX}001'
        ip1_title = '智能校园导览系统'
        ip1_authorized_date = (now - timedelta(days=30)).date()
        certificate_file = self._create_ip_certificate_asset(
            p1,
            ip1_code,
            ip1_title,
            ip1_authorized_date,
        )
        ip1 = IntellectualPropertyApplication.objects.create(
            title=ip1_title,
            application_code=ip1_code,
            ip_type=IntellectualPropertyApplication.IPType.SOFTWARE_COPYRIGHT,
            related_project=p1,
            status=IntellectualPropertyApplication.Status.AUTHORIZED,
            main_writer=writer1,
            applicant_executor=writer1,
            material_manager=pick_members(p1, 1)[0],
            project_reviewer=p1.leader,
            teacher_confirmer=self.teachers[0],
            start_date=(now - timedelta(days=180)).date(),
            submit_date=(now - timedelta(days=150)).date(),
            accepted_date=(now - timedelta(days=90)).date(),
            authorized_date=ip1_authorized_date,
            return_count=0,
            final_certificate_file=certificate_file,
            intro='基于移动端定位与AR技术的校园导览系统软件著作权，'
                  '包含室内外导航、景点讲解与活动指引等核心模块。',
            created_by=writer1,
        )
        self._add_ip_contributors(ip1, writer1, p1, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.EXECUTOR,
            IPApplicationContributor.ContributorRole.MATERIAL_MANAGER,
            IPApplicationContributor.ContributorRole.REVIEWER,
        ])

        # --- 2. 医学影像辅助诊断算法 发明专利 - 科研处退回 ---
        p2 = self.projects[1]
        writer2 = p2.leader
        ip2 = IntellectualPropertyApplication.objects.create(
            title='医学影像辅助诊断算法',
            application_code=f'{DEMO_IP_PREFIX}002',
            ip_type=IntellectualPropertyApplication.IPType.INVENTION_PATENT,
            related_project=p2,
            status=IntellectualPropertyApplication.Status.RETURNED,
            main_writer=writer2,
            applicant_executor=writer2,
            material_manager=pick_members(p2, 1)[0],
            project_reviewer=p2.leader,
            teacher_confirmer=self.teachers[0],
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
            IPApplicationContributor.ContributorRole.REVIEWER,
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
        writer3 = p4.leader
        ip3 = IntellectualPropertyApplication.objects.create(
            title='农产品溯源链码生成方法',
            application_code=f'{DEMO_IP_PREFIX}003',
            ip_type=IntellectualPropertyApplication.IPType.INVENTION_PATENT,
            related_project=p4,
            status=IntellectualPropertyApplication.Status.RESEARCH_OFFICE_REVIEW,
            main_writer=writer3,
            applicant_executor=writer3,
            material_manager=pick_members(p4, 1)[0],
            project_reviewer=p4.leader,
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
            IPApplicationContributor.ContributorRole.REVIEWER,
        ])

        # --- 4. 校园二手交易小程序 软著 - 材料撰写中 ---
        p3 = self.projects[2]
        writer4 = p3.leader
        ip4 = IntellectualPropertyApplication.objects.create(
            title='校园二手交易小程序',
            application_code=f'{DEMO_IP_PREFIX}004',
            ip_type=IntellectualPropertyApplication.IPType.SOFTWARE_COPYRIGHT,
            related_project=p3,
            status=IntellectualPropertyApplication.Status.WRITING,
            main_writer=writer4,
            applicant_executor=writer4,
            material_manager=pick_members(p3, 1)[0],
            project_reviewer=p3.leader,
            teacher_confirmer=self.teachers[0],
            start_date=(now - timedelta(days=30)).date(),
            return_count=0,
            current_problem='软件说明书撰写中，源代码文档待整理。',
            intro='面向在校学生的二手物品交易小程序软件著作权。',
            created_by=writer4,
        )
        self._add_ip_contributors(ip4, writer4, p3, [
            IPApplicationContributor.ContributorRole.MAIN_WRITER,
            IPApplicationContributor.ContributorRole.DOCUMENT_WRITER,
            IPApplicationContributor.ContributorRole.REVIEWER,
        ])

        # --- 5. 环境监测数据异常检测方法 实用新型专利 - 科研处退回 ---
        p9 = self.projects[8]
        writer5 = p9.leader
        ip5 = IntellectualPropertyApplication.objects.create(
            title='环境监测数据异常检测方法',
            application_code=f'{DEMO_IP_PREFIX}005',
            ip_type=IntellectualPropertyApplication.IPType.UTILITY_MODEL,
            related_project=p9,
            status=IntellectualPropertyApplication.Status.RETURNED,
            main_writer=writer5,
            applicant_executor=writer5,
            material_manager=pick_members(p9, 1)[0],
            project_reviewer=p9.leader,
            teacher_confirmer=self.teachers[0],
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
            IPApplicationContributor.ContributorRole.REVIEWER,
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
            leader_reviewer=p1.leader,
            leader_reviewed_at=now - timedelta(days=5),
            teacher_confirmer=self.teachers[0],
            teacher_confirmed_at=now - timedelta(days=3),
            final_result='维持原贡献认定，排序微调。',
        )

        material_specs = [
            (
                ip1,
                self.files_by_project[p1.id][0],
                IPMaterialVersion.MaterialType.ARCHIVE,
                'v1',
                True,
                '成果归档材料已核验，并与最终授权登记证书分别留存。',
            ),
            (
                ip2,
                self.files_by_project[p2.id][1],
                IPMaterialVersion.MaterialType.SPECIFICATION,
                'v2',
                False,
                '根据科研处退回意见补充实施例与技术效果。',
            ),
            (
                ip3,
                self.files_by_project[p4.id][1],
                IPMaterialVersion.MaterialType.DISCLOSURE,
                'v1',
                False,
                '科研处审核使用的技术交底书。',
            ),
            (
                ip4,
                self.files_by_project[p3.id][1],
                IPMaterialVersion.MaterialType.MANUAL,
                'v1',
                False,
                '软件说明书初稿，等待代码文档补充。',
            ),
            (
                ip5,
                self.files_by_project[p9.id][1],
                IPMaterialVersion.MaterialType.DRAWING,
                'v2',
                False,
                '已重新核对附图标记，待责任人确认。',
            ),
        ]
        for application, file_asset, material_type, version, is_final, note in material_specs:
            IPMaterialVersion.objects.create(
                application=application,
                file_asset=file_asset,
                material_type=material_type,
                version=version,
                uploaded_by=application.material_manager or application.main_writer,
                change_note=note,
                is_final=is_final,
            )

        self.stdout.write(self.style.SUCCESS(
            '   知识产权创建完成：申请 5 个，材料版本 5 条，退回记录 2 条，异议 2 条'
        ))

    def _add_ip_contributors(self, application, main_writer, project, roles):
        """按档案中的实际职责为 IP 申请建立一致、可确认的责任分工。"""
        members = [u for u in self.project_members[project.id] if u != main_writer]
        random.shuffle(members)
        direct_responsibilities = {
            IPApplicationContributor.ContributorRole.MAIN_WRITER: application.main_writer,
            IPApplicationContributor.ContributorRole.EXECUTOR: application.applicant_executor,
            IPApplicationContributor.ContributorRole.MATERIAL_MANAGER: application.material_manager,
            IPApplicationContributor.ContributorRole.REVIEWER: application.project_reviewer,
        }
        application_contributors = []
        for role in roles:
            user = direct_responsibilities.get(role)
            if user is None:
                user = members.pop() if members else main_writer
            application_contributors.append((user, role))
        for user, role in application_contributors:
            role_label = IPApplicationContributor.ContributorRole(role).label
            is_confirmed = (
                application.status
                in {
                    IntellectualPropertyApplication.Status.AUTHORIZED,
                    IntellectualPropertyApplication.Status.ARCHIVED,
                }
            )
            IPApplicationContributor.objects.create(
                application=application,
                user=user,
                role=role,
                contribution_description=(
                    f'{user.name}在「{application.title}」中担任'
                    f'{role_label}。'
                ),
                responsibility_description=(
                    f'{user.name}负责「{application.title}」对应环节的'
                    '材料质量、节点反馈与留痕，'
                    '如发生退回需参与原因说明和修订闭环。'
                ),
                is_confirmed=is_confirmed,
                confirmed_by=application.project_reviewer if is_confirmed else None,
                confirmed_at=timezone.now() - timedelta(days=25) if is_confirmed else None,
            )

    def create_portal_publications(self):
        """为演示项目、成果和已授权成员建立逐项公开决策。"""
        self.stdout.write('-> 创建受治理的公开门户内容...')
        teacher = self.users['teacher1']
        portal_defaults = {
            'team_name': '数智创新实践团队',
            'tagline': '真实项目 · 持续协作 · 成果沉淀',
            'summary': '团队自 2022 年起持续开展跨专业项目实践，所有公开内容均经过逐项确认。',
            'about_title': '让每一段协作过程都可追踪、可复盘',
            'about_text': '我们围绕校园、社区、乡村和产业真实需求开展项目，并沉淀任务、文件、赛事与知识产权成果。',
            'contact_email': 'teacher1@demo.com',
            'join_title': '加入数智创新实践团队',
            'join_message': '欢迎愿意持续投入、尊重协作规范并主动承担任务的同学联系我们。',
            'join_url': '/join-us',
            'updated_by': teacher,
        }
        portal_settings, created = PortalSettings.objects.get_or_create(
            singleton_key='default',
            defaults=portal_defaults,
        )
        if (
            not created
            and portal_settings.updated_by_id
            and portal_settings.updated_by.email.endswith('@demo.com')
        ):
            for field, value in portal_defaults.items():
                setattr(portal_settings, field, value)
            portal_settings.save(update_fields=[
                *portal_defaults.keys(),
                'updated_at',
            ])

        for index, project in enumerate(self.projects):
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.PROJECT,
                object_id=project.id,
                defaults={
                    'is_public': index < 16,
                    'is_featured': index < 4,
                    'member_consent': False,
                    'display_order': index,
                    'custom_title': project.name,
                    'custom_summary': project.intro,
                    'updated_by': teacher,
                },
            )

        ip_applications = list(
            IntellectualPropertyApplication.objects.filter(
                application_code__startswith=DEMO_IP_PREFIX
            ).order_by('id')
        )
        for index, application in enumerate(ip_applications):
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.IP_APPLICATION,
                object_id=application.id,
                defaults={
                    'is_public': application.status in {
                        IntellectualPropertyApplication.Status.AUTHORIZED,
                        IntellectualPropertyApplication.Status.ARCHIVED,
                    },
                    'is_featured': index == 0,
                    'member_consent': False,
                    'display_order': index,
                    'custom_title': application.title,
                    'custom_summary': application.intro,
                    'updated_by': teacher,
                },
            )

        governed_members = self.leaders + self.members[:12]
        for index, member in enumerate(governed_members):
            has_consent = index < 12
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.MEMBER,
                object_id=member.id,
                defaults={
                    'is_public': has_consent,
                    'is_featured': index < 4,
                    'member_consent': has_consent,
                    'display_order': index,
                    'custom_title': member.name,
                    'custom_summary': (
                        f'{DEMO_MARKER}{member.major} · {member.grade}，'
                        '参与团队项目协作与成果整理。'
                    ),
                    'updated_by': member if has_consent else teacher,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'   门户治理创建完成：项目 {len(self.projects)} 项，'
            f'知识产权 {len(ip_applications)} 项，成员 {len(governed_members)} 人'
        ))

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
        for index, (owner, fake_id) in enumerate(zip(owners, fake_ids)):
            sd = SensitiveData(
                data_type=SensitiveData.DataType.ID_CARD,
                title=f'{DEMO_MARKER}{owner.name}的身份证号码',
                display_name='身份证号码',
                key_version=1,
                project=self.projects[index],
                file_attachment=(
                    self.files_by_project[self.projects[0].id][2]
                    if index == 0
                    else None
                ),
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

        # 1. member5 申请下载 leader1 的附件 - 已通过，仍在有效期内
        sd_leader1 = self.sensitive_data_map[self.users['leader1'].email]
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd_leader1,
            applicant=self.users['member5'],
            reason='办理比赛获奖奖金发放，需下载核验负责人证明附件。',
            usage_scenario='奖金发放附件核验',
            project=self.projects[0],
            expected_use_time=now + timedelta(hours=2),
            is_download=True,
            status=SensitiveAccessRequest.Status.APPROVED,
            approver=approver,
            approval_opinion='情况属实，同意在有效期内下载一次。',
            approved_at=now - timedelta(minutes=10),
            access_expires_at=now + timedelta(hours=2),
        )

        # 2. member8 只查看 leader2 的资料 - 已通过、不可下载
        sd_leader2 = self.sensitive_data_map[self.users['leader2'].email]
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd_leader2,
            applicant=self.users['member8'],
            reason='赛前报名材料复核，仅需查看脱敏资料。',
            usage_scenario='报名材料线上复核',
            project=self.projects[1],
            expected_use_time=now + timedelta(hours=1),
            is_download=False,
            status=SensitiveAccessRequest.Status.APPROVED,
            approver=approver,
            approval_opinion='仅授权在线查看，不允许下载。',
            approved_at=now - timedelta(minutes=25),
            access_expires_at=now + timedelta(minutes=45),
            viewed_at=now - timedelta(minutes=5),
        )

        # 3. member10 的下载申请 - 待审批
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

        # 4. 历史查看授权已过期，用于演示审批与有效期过滤
        SensitiveAccessRequest.objects.create(
            sensitive_data=sd_leader2,
            applicant=self.users['member12'],
            reason='历史归档材料核验。',
            usage_scenario='结项归档复核',
            project=self.projects[1],
            expected_use_time=now - timedelta(days=2),
            is_download=False,
            status=SensitiveAccessRequest.Status.EXPIRED,
            approver=approver,
            approval_opinion='历史授权已超过有效期。',
            approved_at=now - timedelta(days=3),
            access_expires_at=now - timedelta(days=2),
            viewed_at=now - timedelta(days=2, hours=1),
        )

        self.stdout.write(self.style.SUCCESS('   敏感资料访问申请创建完成：4 条'))

    # ------------------------------------------------------------------
    # 公告
    # ------------------------------------------------------------------
    def create_announcements(self):
        self.stdout.write('-> 创建团队公告...')
        now = timezone.now()
        announcements = [
            {
                'title': '团队周例会与项目更新提醒',
                'content': (
                    '各项目负责人请在例会前完成项目进展更新；连续 11 天未更新'
                    '的项目将进入工作台提醒。'
                ),
                'category': Announcement.Category.PROJECT,
                'is_pinned': True,
                'is_public': False,
                'author': self.users['admin'],
            },
            {
                'title': '暑期项目路演安排',
                'content': (
                    '本周六下午进行阶段路演，请各项目准备一页进展摘要和'
                    '下一阶段计划。'
                ),
                'category': Announcement.Category.ACTIVITY,
                'is_pinned': False,
                'is_public': True,
                'author': self.users['teacher1'],
            },
            {
                'title': '报销票据 OCR 使用说明',
                'content': (
                    '上传清晰的票据图片后可自动识别日期、金额和票据号码，'
                    '提交前请人工核对识别结果。'
                ),
                'category': Announcement.Category.SYSTEM,
                'is_pinned': False,
                'is_public': False,
                'author': self.users['teacher2'],
            },
        ]
        for index, definition in enumerate(announcements):
            Announcement.objects.create(
                title=f'{DEMO_MARKER}{definition["title"]}',
                content=definition['content'],
                category=definition['category'],
                status=Announcement.Status.PUBLISHED,
                is_pinned=definition['is_pinned'],
                is_public=definition['is_public'],
                author=definition['author'],
                published_at=now - timedelta(days=index),
            )

        self.stdout.write(self.style.SUCCESS('   团队公告创建完成：3 条'))

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
                title=f'{DEMO_MARKER}{n["title"]}',
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
                description=f'{DEMO_MARKER}{desc}',
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
        self.stdout.write(self.style.WARNING('-> 精准清除本命令的演示数据...'))
        demo_projects = Project.all_objects.filter(
            code__startswith=DEMO_PROJECT_PREFIX
        )
        legacy_projects = Project.all_objects.filter(
            code__startswith='PROJ-',
            leader__email__endswith='@demo.com',
        )
        legacy_competition_projects = Project.all_objects.filter(
            code__startswith='DEMO-2026-',
        )
        project_ids = list(
            demo_projects.values_list('id', flat=True)
        ) + list(
            legacy_projects.values_list('id', flat=True)
        ) + list(
            legacy_competition_projects.values_list('id', flat=True)
        )
        project_ids = list(dict.fromkeys(project_ids))
        ip_applications = IntellectualPropertyApplication.objects.filter(
            application_code__startswith=DEMO_IP_PREFIX
        )
        if project_ids:
            ip_applications = (
                ip_applications
                | IntellectualPropertyApplication.objects.filter(
                    related_project_id__in=project_ids
                )
            )
        ip_ids = list(
            ip_applications.values_list('id', flat=True).distinct()
        )

        total = 0

        def delete_queryset(queryset):
            nonlocal total
            count, _ = queryset.delete()
            total += count

        # 二级团队的 parent 使用 PROTECT，需先按本命令专属编号精确删除；
        # 随后再清除根团队及其根级成员历史。
        delete_queryset(Team.objects.filter(code__in=DEMO_SQUAD_CODES))
        # 团队编号是本命令的唯一所有权边界；只清除该团队及其级联成员历史。
        delete_queryset(Team.objects.filter(code=DEMO_TEAM_CODE))

        # 删除数据库记录前先清除本命令写入的物理文件。
        receipt_queryset = FinanceReceipt.objects.filter(
            expense__project_id__in=project_ids
        )
        for receipt in receipt_queryset.exclude(file='').iterator():
            receipt.file.delete(save=False)

        version_queryset = FileVersion.objects.filter(
            file_asset__project_id__in=project_ids
        )
        for version in version_queryset.exclude(file='').iterator():
            version.file.delete(save=False)
        file_queryset = FileAsset.objects.filter(project_id__in=project_ids)
        for asset in file_queryset.exclude(file='').iterator():
            asset.file.delete(save=False)

        demo_report_queryset = CustomReport.objects.filter(
            Q(name__startswith=DEMO_MARKER)
            | Q(
                name__in=LEGACY_COMPETITION_REPORT_NAMES,
                created_by__email__endswith='@demo.com',
            )
        )
        report_execution_queryset = ScheduledReportExecution.objects.filter(
            schedule__report__in=demo_report_queryset
        )
        for execution in report_execution_queryset.exclude(file='').iterator():
            execution.file.delete(save=False)

        import_queryset = ImportTask.objects.filter(
            file_path__contains=str(
                Path('imports') / DEMO_IMPORT_DIRNAME
            )
        )
        safe_import_root = (
            Path(settings.MEDIA_ROOT)
            / 'imports'
            / DEMO_IMPORT_DIRNAME
        ).resolve()
        for file_path in import_queryset.values_list('file_path', flat=True):
            try:
                candidate = Path(file_path).resolve()
                if candidate.is_relative_to(safe_import_root):
                    candidate.unlink(missing_ok=True)
            except (OSError, RuntimeError):
                pass
        delete_queryset(import_queryset)

        if project_ids:
            delete_queryset(PortalPublication.objects.filter(
                content_type=PortalPublication.ContentType.PROJECT,
                object_id__in=project_ids,
            ))
        if ip_ids:
            delete_queryset(PortalPublication.objects.filter(
                content_type=PortalPublication.ContentType.IP_APPLICATION,
                object_id__in=ip_ids,
            ))
        delete_queryset(PortalPublication.objects.filter(
            content_type=PortalPublication.ContentType.MEMBER,
            custom_summary__startswith=DEMO_MARKER,
        ))
        delete_queryset(PortalSettings.objects.filter(
            singleton_key='default',
            team_name='数智创新实践团队',
            updated_by__email__endswith='@demo.com',
        ))

        delete_queryset(OperationLog.objects.filter(
            description__startswith=DEMO_MARKER
        ))
        delete_queryset(OperationLog.objects.filter(
            request_data__source='seed_demo_data'
        ))
        delete_queryset(Notification.objects.filter(
            title__startswith=DEMO_MARKER
        ))
        delete_queryset(Announcement.objects.filter(
            title__startswith=DEMO_MARKER
        ))
        delete_queryset(demo_report_queryset)
        delete_queryset(UserLifecycleEvent.objects.filter(
            reason__startswith=DEMO_MARKER
        ))
        # 演示账号会被其他旧演示脚本复用；完整重建时清除其技能关系，
        # 避免旧脚本的随机技能被并入本命令的确定性演示包。
        # SkillTag 仍作为共享字典保留，真实账号的技能关系不受影响。
        delete_queryset(MemberSkill.objects.filter(
            user__email__in=DEMO_ACCOUNT_EMAILS
        ))
        delete_queryset(FlexibleWorkSchedule.objects.filter(
            notes__startswith=DEMO_MARKER
        ))

        if project_ids:
            delete_queryset(SensitiveAccessRequest.objects.filter(
                project_id__in=project_ids
            ))
        delete_queryset(SensitiveData.objects.filter(
            title__startswith=DEMO_MARKER
        ))

        if ip_ids:
            delete_queryset(IPObjection.objects.filter(
                application_id__in=ip_ids
            ))
            delete_queryset(IPReturnRecord.objects.filter(
                application_id__in=ip_ids
            ))
            delete_queryset(IPApplicationContributor.objects.filter(
                application_id__in=ip_ids
            ))
            delete_queryset(
                IntellectualPropertyApplication.objects.filter(id__in=ip_ids)
            )

        if project_ids:
            delete_queryset(RankingObjection.objects.filter(
                ranking__project_id__in=project_ids
            ))
            delete_queryset(MemberRanking.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(Contribution.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(receipt_queryset)
            delete_queryset(FinanceExpense.all_objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(FinanceIncome.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(FinanceBudget.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(Task.all_objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(version_queryset)
            delete_queryset(file_queryset)
            delete_queryset(Competition.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(ProjectMembershipEvent.objects.filter(
                membership__project_id__in=project_ids
            ))
            delete_queryset(ProjectStageLog.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(ProjectMember.objects.filter(
                project_id__in=project_ids
            ))
            delete_queryset(Project.all_objects.filter(id__in=project_ids))

        # 旧版比赛种子比完整团队种子多创建了两个负责人账号。它们不属于
        # 当前固定的 60 账号集合；仅按精确邮箱清理，避免扩大到其他测试账号。
        delete_queryset(User.objects.filter(
            email__in=LEGACY_COMPETITION_ACCOUNT_EMAILS
        ))

        # 账号和共享技能标签可被其他演示场景复用，不做删除；创建阶段使用
        # update_or_create 保证重复运行稳定。所有真实账号和非演示业务记录均不触碰。
        self.stdout.write(self.style.SUCCESS(
            f'   已精准清除 {total} 条团队演示记录；真实数据与共享演示账号均保留'
        ))

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
        self.stdout.write('  负责人4:   leader4@demo.com / leader123456')
        self.stdout.write('  敏感审批:  approver@demo.com / approver123456')
        self.stdout.write('  普通成员:  member1~52@demo.com / member123456')
