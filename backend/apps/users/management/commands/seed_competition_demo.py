"""
面向比赛项目管理平台的高质量演示数据种子命令。

放置位置：
    backend/apps/users/management/commands/seed_competition_demo.py

资产目录：
    backend/seed_assets/competition_demo_files/

运行：
    cd backend
    python manage.py seed_competition_demo --clean --force

特点：
    - 6 个核心成员，每人负责 1 个项目，同时交叉参与其他项目。
    - 6 个项目均为 5-8 人团队；每个项目至少同时参加 3 个比赛。小挑/大挑全项目覆盖，数字中国只安排 2 个项目。
    - 覆盖项目历程、人员变动、任务、经费、文件版本、贡献、排序、知识产权、敏感资料、通知、日志、导入记录。
    - 每个项目含真实 PDF/DOCX 项目计划书、精简 Excel 数据表和两行内容的 Word 路演稿；PPT 为合法占位文件。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.audit.models import OperationLog
from apps.competitions.models import Competition
from apps.contributions.models import Contribution, MemberRanking, RankingObjection
from apps.dashboard.portal_models import PortalPublication, PortalSettings
from apps.exports.custom_report_models import CustomReport
from apps.exports.scheduled_report_models import ScheduledReport
from apps.exports.scheduled_report_service import (
    compute_next_run,
    execute_scheduled_report,
)
from apps.files.models import FileAsset, FileVersion
from apps.finance.models import FinanceBudget, FinanceExpense, FinanceIncome, FinanceReceipt
from apps.imports.models import ImportTask
from apps.integrations.models import IntegrationConfig, IntegrationLog
from apps.intellectual_property.models import (
    IntellectualPropertyApplication,
    IPApplicationContributor,
    IPMaterialVersion,
    IPObjection,
    IPReturnRecord,
)
from apps.members.models import FlexibleWorkSchedule, MemberSkill, SkillTag
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember, ProjectStageLog
from apps.sensitive.models import SensitiveAccessRequest, SensitiveData
from apps.tasks.models import Task, TaskLog
from apps.users.models import User, UserPreference

PASSWORDS = {
    'admin': 'admin123456',
    'teacher': 'teacher123456',
    'approver': 'approver123456',
    'leader': 'leader123456',
    'member': 'member123456',
}

CORE_MEMBERS = [
    {'key': 'leader1', 'name': '陈思源', 'major': '信息管理与信息系统', 'grade': '2022级', 'phone': '13810000001', 'role': '商业模式与项目统筹'},
    {'key': 'leader2', 'name': '林雨桐', 'major': '电子商务', 'grade': '2022级', 'phone': '13810000002', 'role': '用户研究与材料主笔'},
    {'key': 'leader3', 'name': '周景行', 'major': '软件工程', 'grade': '2021级', 'phone': '13810000003', 'role': '后端架构与系统集成'},
    {'key': 'leader4', 'name': '许一诺', 'major': '人工智能', 'grade': '2022级', 'phone': '13810000004', 'role': '算法模型与数据分析'},
    {'key': 'leader5', 'name': '韩嘉禾', 'major': '数字媒体技术', 'grade': '2023级', 'phone': '13810000005', 'role': '视觉表达与路演呈现'},
    {'key': 'leader6', 'name': '罗明轩', 'major': '财务管理', 'grade': '2022级', 'phone': '13810000006', 'role': '经费预算与商务测算'},
]

ASSISTANTS = [
    ('member1', '赵若安', '软件工程', '2023级', '前端开发与测试'),
    ('member2', '王子涵', '数据科学与大数据技术', '2023级', '数据清洗与可视化'),
    ('member3', '刘泽宇', '市场营销', '2022级', '调研访谈与竞品分析'),
    ('member4', '孙语辰', '视觉传达设计', '2023级', '海报、展板与PPT美化'),
    ('member5', '李承浩', '物联网工程', '2021级', '硬件联调与设备测试'),
    ('member6', '钱嘉宁', '法学', '2022级', '知识产权与合规材料'),
    ('member7', '吴沐阳', '会计学', '2023级', '票据整理与报销台账'),
    ('member8', '郑可欣', '工商管理', '2022级', '运营推广与用户增长'),
]

PROJECTS = [
    {
        'code': 'DEMO-2026-001',
        'name': '智农云链：县域农产品品牌与溯源服务平台',
        'leader': 'leader1',
        'current_stage': Project.Stage.NATIONAL_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.URGENT,
        'intro': '围绕县域农产品标准化、品牌化与数字化溯源，连接农户、合作社、采购商和消费者。',
        # 7人组：1名负责人 + 2名强副手 + 4名执行成员
        'members': ['leader1', 'leader3', 'leader4', 'leader5', 'leader6', 'member2', 'member3'],
        'deputies': ['leader3', 'leader4'],
    },
    {
        'code': 'DEMO-2026-002',
        'name': '青碳校园：大学生低碳行为激励与碳积分平台',
        'leader': 'leader2',
        'current_stage': Project.Stage.PROVINCE_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.HIGH,
        'intro': '通过绿色消费、旧物回收、低碳出行和校园活动签到构建学生碳积分激励闭环。',
        # 7人组：1名负责人 + 2名强副手 + 4名执行成员
        'members': ['leader2', 'leader1', 'leader5', 'leader6', 'member1', 'member4', 'member8'],
        'deputies': ['leader1', 'leader5'],
    },
    {
        'code': 'DEMO-2026-003',
        'name': '银龄守护：社区智慧养老陪护与风险预警系统',
        'leader': 'leader3',
        'current_stage': Project.Stage.CITY_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.HIGH,
        'intro': '面向社区养老机构与独居老人，提供风险预警、陪护排班、家属协同和志愿服务闭环。',
        # 6人组：1名负责人 + 1名强副手 + 4名执行成员
        'members': ['leader3', 'leader1', 'leader2', 'leader4', 'member5', 'member6'],
        'deputies': ['leader1'],
    },
    {
        'code': 'DEMO-2026-004',
        'name': '慧田视界：农田病虫害多模态监测与决策系统',
        'leader': 'leader4',
        'current_stage': Project.Stage.NATIONAL_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.URGENT,
        'intro': '融合田间图像、气象、农事记录和专家规则，实现病虫害识别、趋势预警和防治建议。',
        # 7人组：1名负责人 + 2名强副手 + 4名执行成员
        'members': ['leader4', 'leader3', 'leader5', 'leader6', 'member1', 'member2', 'member5'],
        'deputies': ['leader3', 'leader5'],
    },
    {
        'code': 'DEMO-2026-005',
        'name': '政务听诊器：热线工单智能分派与质效分析平台',
        'leader': 'leader5',
        'current_stage': Project.Stage.PROVINCE_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.HIGH,
        'intro': '面向政务热线服务外包场景，做工单分类、智能分派、质检分析和知识库复用。',
        # 8人组：1名负责人 + 2名强副手 + 5名执行成员
        'members': ['leader5', 'leader2', 'leader3', 'leader4', 'member1', 'member6', 'member7', 'member8'],
        'deputies': ['leader2', 'leader3'],
    },
    {
        'code': 'DEMO-2026-006',
        'name': '数智赣图：城市公共数据治理与可视化平台',
        'leader': 'leader6',
        'current_stage': Project.Stage.CITY_COMP,
        'status': Project.Status.ACTIVE,
        'priority': Project.Priority.NORMAL,
        'intro': '围绕公共数据目录、指标治理、开放应用和可视化大屏，服务城市治理辅助决策。',
        # 6人组：1名负责人 + 1名强副手 + 4名执行成员
        'members': ['leader6', 'leader1', 'leader2', 'leader4', 'member2', 'member7'],
        'deputies': ['leader4'],
    },
]

# 赛事矩阵：每个项目至少同时参加 3 个比赛；小挑/大挑全项目参加；数字中国只安排 2 个项目参加。
# 时间根据 2025-2026 年公开赛程抽象为演示节点，不直接冒充官方精确时间。
COMPETITION_LIBRARY = {
    'big_challenge': {
        'name': '“挑战杯”全国大学生课外学术科技作品竞赛（大挑）',
        'comp_type': '学术科技作品',
        'organizer': '共青团中央、中国科协、教育部、中国社会科学院、全国学联等',
        'register_date': date(2025, 1, 20),
        'material_deadline': date(2025, 3, 3),
        'review_date': date(2025, 7, 20),
        'defense_date': date(2025, 10, 31),
        'school_date': date(2025, 3, 10),
        'city_date': date(2025, 5, 15),
        'province_date': date(2025, 7, 15),
        'national_date': date(2025, 10, 31),
        'result_date': date(2025, 11, 3),
    },
    'small_challenge': {
        'name': '“挑战杯”中国大学生创业计划竞赛（小挑）',
        'comp_type': '创业计划/公益创业',
        'organizer': '共青团中央、中国科协、教育部、中国社会科学院、全国学联等',
        'register_date': date(2026, 1, 23),
        'material_deadline': date(2026, 3, 20),
        'review_date': date(2026, 5, 20),
        'defense_date': date(2026, 6, 10),
        'school_date': date(2026, 3, 5),
        'city_date': date(2026, 5, 28),
        'province_date': date(2026, 6, 12),
        'national_date': date(2026, 10, 20),
        'result_date': date(2026, 11, 10),
    },
    'cxcy': {
        'name': '中国国际大学生创新大赛（国创赛）',
        'comp_type': '创新创业',
        'organizer': '教育部等',
        'register_date': date(2026, 4, 20),
        'material_deadline': date(2026, 6, 20),
        'review_date': date(2026, 7, 25),
        'defense_date': date(2026, 8, 5),
        'school_date': date(2026, 5, 25),
        'city_date': date(2026, 6, 25),
        'province_date': date(2026, 7, 28),
        'national_date': date(2026, 10, 18),
        'result_date': date(2026, 10, 30),
    },
    'sanchuang': {
        'name': '全国大学生电子商务“创新、创意及创业”挑战赛（三创赛）',
        'comp_type': '电子商务/商业创新',
        'organizer': '全国电子商务产教融合创新联盟等',
        'register_date': date(2025, 10, 20),
        'material_deadline': date(2026, 1, 20),
        'review_date': date(2026, 4, 20),
        'defense_date': date(2026, 6, 22),
        'school_date': date(2026, 4, 10),
        'city_date': date(2026, 5, 10),
        'province_date': date(2026, 6, 22),
        'national_date': date(2026, 7, 10),
        'result_date': date(2026, 8, 10),
    },
    'service_outsourcing': {
        'name': '中国大学生服务外包创新创业大赛（服创赛）',
        'comp_type': '服务外包/产业命题',
        'organizer': '中国大学生服务外包创新创业大赛组委会',
        'register_date': date(2026, 2, 11),
        'material_deadline': date(2026, 4, 15),
        'review_date': date(2026, 5, 6),
        'defense_date': date(2026, 6, 20),
        'school_date': date(2026, 3, 20),
        'city_date': date(2026, 5, 20),
        'province_date': date(2026, 6, 25),
        'national_date': date(2026, 8, 8),
        'result_date': date(2026, 8, 12),
    },
    'digital_china': {
        'name': '数字中国创新大赛·数字治理/AI应用赛道',
        'comp_type': '数字政府/AI应用/数据要素',
        'organizer': '数字中国创新大赛组委会',
        'register_date': date(2026, 3, 13),
        'material_deadline': date(2026, 4, 15),
        'review_date': date(2026, 4, 17),
        'defense_date': date(2026, 4, 25),
        'school_date': date(2026, 3, 25),
        'city_date': date(2026, 4, 16),
        'province_date': date(2026, 4, 25),
        'national_date': date(2026, 4, 27),
        'result_date': date(2026, 4, 30),
    },
}

PROJECT_COMPETITION_MATRIX = {
    # 全部项目：大挑 + 小挑；再按项目方向叠加 1-3 个差异化赛事
    'DEMO-2026-001': [
        ('big_challenge', Competition.Level.NATIONAL, True, True, '国家级三等奖入围材料归档', '国赛已完成'),
        ('small_challenge', Competition.Level.NATIONAL, True, False, '市赛金奖、省赛一等奖，国赛备赛中', '国赛备赛'),
        ('cxcy', Competition.Level.NATIONAL, True, False, '省赛金奖，拟推荐全国总决赛', '全国总决赛材料准备'),
        ('sanchuang', Competition.Level.PROVINCE, False, False, '省赛二等奖，未进入全国总决赛', '已结束'),
    ],
    'DEMO-2026-002': [
        ('big_challenge', Competition.Level.CITY, False, False, '校赛一等奖，市赛未出线', '市赛止步'),
        ('small_challenge', Competition.Level.PROVINCE, True, True, '省赛铜奖，成果转入孵化', '获奖归档'),
        ('sanchuang', Competition.Level.NATIONAL, True, False, '省赛一等奖，进入全国总决赛备赛', '全国总决赛备赛'),
    ],
    'DEMO-2026-003': [
        ('big_challenge', Competition.Level.CITY, False, False, '校赛二等奖，市赛未出线', '市赛止步'),
        ('small_challenge', Competition.Level.CITY, True, False, '校赛金奖，进入市赛答辩', '市赛答辩'),
        ('cxcy', Competition.Level.PROVINCE, True, False, '校赛一等奖，省赛网评中', '省赛网评'),
        ('service_outsourcing', Competition.Level.SCHOOL, False, False, '校内选拔未推荐', '已结束'),
    ],
    'DEMO-2026-004': [
        ('big_challenge', Competition.Level.NATIONAL, True, True, '省赛特等奖，国赛一等奖候选', '国赛终审'),
        ('small_challenge', Competition.Level.PROVINCE, True, False, '省赛银奖，未进国赛', '省赛已结束'),
        ('cxcy', Competition.Level.PROVINCE, True, False, '省赛网评中', '省赛网评'),
        ('digital_china', Competition.Level.NATIONAL, True, True, '决赛优胜奖，完成颁奖归档', '全国决赛已完成'),
    ],
    'DEMO-2026-005': [
        ('big_challenge', Competition.Level.PROVINCE, True, False, '省赛二等奖，未进国赛', '省赛已结束'),
        ('small_challenge', Competition.Level.PROVINCE, True, False, '市赛一等奖，省赛答辩准备中', '省赛答辩准备'),
        ('service_outsourcing', Competition.Level.NATIONAL, True, False, '区域赛入围，全国决赛备赛', '全国赛答辩准备'),
    ],
    'DEMO-2026-006': [
        ('big_challenge', Competition.Level.CITY, False, False, '校赛一等奖，市赛未出线', '市赛止步'),
        ('small_challenge', Competition.Level.CITY, True, False, '校赛金奖，进入市赛复评', '市赛复评'),
        ('sanchuang', Competition.Level.PROVINCE, True, False, '省赛三等奖，未进国赛', '省赛已结束'),
        ('digital_china', Competition.Level.PROVINCE, True, False, '线上初赛通过，线下决赛候补', '线下候补'),
    ],
}

TIMELINE_EVENT_TYPES = [
    'stage_change', 'member_change', 'file_change', 'direction_change', 'competition_node', 'finance_node', 'ip_node'
]

SKILLS = [
    '项目统筹', '商业计划书', '比赛申报', '路演答辩', '前端开发', '后端开发', '算法建模',
    '数据治理', 'UI设计', 'PPT制作', '财务预算', '用户调研', '知识产权', '文档归档', '视频剪辑',
]

STAGE_FLOW = [
    (Project.Stage.CONCEIVING, '完成选题头脑风暴和问题定义'),
    (Project.Stage.APPROVED, '指导老师确认方向并完成团队立项'),
    (Project.Stage.MATERIAL_PREP, '完成项目计划书、调研问卷、竞品分析和商业画布'),
    (Project.Stage.DEV_EXPERIMENT, '完成系统原型、核心功能联调和用户试用反馈'),
    (Project.Stage.REGISTER_PREP, '完成报名信息、团队信息和参赛承诺书'),
    (Project.Stage.MATERIAL_SUBMIT, '提交项目计划书、PPT、路演稿和证明材料'),
    (Project.Stage.REVIEW_AUDIT, '进入网评审核，按专家意见补充数据和案例'),
    (Project.Stage.DEFENSE_PREP, '组织模拟答辩，修订路演结构和时间控制'),
    (Project.Stage.SCHOOL_COMP, '完成校赛答辩，获得校内推荐资格'),
    (Project.Stage.PROVINCE_COMP, '进入省赛环节，完善数据支撑和落地证明'),
    (Project.Stage.NATIONAL_COMP, '进入国赛备赛/网评/答辩阶段'),
    (Project.Stage.AWARDED, '获奖后整理证书、新闻稿和成果归档材料'),
]


def aware(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime(year, month, day, hour, minute))


def money(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal('0.01'))


class Command(BaseCommand):
    help = '兼容入口：生成统一的完整团队演示数据。'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='先清除本命令生成的演示数据。')
        parser.add_argument('--force', action='store_true', help='跳过确认。')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'seed_competition_demo 已合并到 seed_demo_data；'
            '本命令将生成同一份完整演示数据。'
        ))
        call_command(
            'seed_demo_data',
            clean=options['clean'],
            force=options['force'],
            stdout=self.stdout,
            stderr=self.stderr,
            verbosity=options.get('verbosity', 1),
        )

    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parents[4]

    def assets_dir(self) -> Path:
        return self.backend_dir() / 'seed_assets' / 'competition_demo_files'

    def get_asset_bytes(self, subdir: str, code: str, suffix: str, fallback: bytes = b'') -> tuple[str, bytes]:
        root = self.assets_dir() / subdir
        if root.exists():
            for p in root.iterdir():
                if p.is_file() and p.name.startswith(code) and p.name.endswith(suffix):
                    return p.name, p.read_bytes()
        return f'{code}_{suffix}', fallback or f'DEMO PLACEHOLDER {code} {suffix}\n'.encode('utf-8')

    def save_asset(self, project: Project, kind: str, display_name: str, level: str, uploader: User,
                   subdir: str, suffix: str, content_type: str, version: int = 1) -> FileAsset:
        filename, data = self.get_asset_bytes(subdir, project.code, suffix)
        return self.save_generated_asset(
            project, kind, display_name, level, uploader,
            filename, data, content_type, version,
        )

    def save_generated_asset(self, project: Project, kind: str, display_name: str, level: str,
                             uploader: User, filename: str, data: bytes, content_type: str,
                             version: int = 1) -> FileAsset:
        """保存命令生成的真实附件，并登记到演示文件索引。"""
        asset = FileAsset.objects.create(
            project=project,
            name=display_name,
            level=level,
            size=len(data),
            content_type=content_type,
            uploader=uploader,
            version=version,
        )
        asset.file.save(filename, ContentFile(data), save=True)
        self.files[(project.code, kind)] = asset
        return asset

    @staticmethod
    def build_minimal_pdf(lines: list[str]) -> bytes:
        """生成仅含少量 ASCII 文本、无需系统 PDF 依赖的有效单页 PDF。"""
        def escape_pdf_text(value: str) -> str:
            return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

        text_commands = ['BT', '/F1 14 Tf', '72 760 Td']
        for index, line in enumerate(lines):
            if index:
                text_commands.append('0 -24 Td')
            text_commands.append(f'({escape_pdf_text(line)}) Tj')
        text_commands.append('ET')
        stream = '\n'.join(text_commands).encode('ascii', errors='replace')
        objects = [
            b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            (
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>'
            ),
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
            b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n'
            + stream + b'\nendstream',
        ]
        pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = [0]
        for number, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf.extend(f'{number} 0 obj\n'.encode('ascii'))
            pdf.extend(obj)
            pdf.extend(b'\nendobj\n')
        xref_offset = len(pdf)
        pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
        pdf.extend(b'0000000000 65535 f \n')
        for offset in offsets[1:]:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
        pdf.extend(
            f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
        )
        return bytes(pdf)

    def create_users(self):
        U = User.GlobalRole
        def make(email, username, password, name, role, **kwargs):
            user = User(email=email, username=username, name=name, global_role=role, **kwargs)
            user.set_password(password)
            user.save()
            return user
        self.users['admin'] = make('admin@demo.com', 'admin', PASSWORDS['admin'], '系统管理员', U.SYS_ADMIN,
                                   is_staff=True, is_superuser=True, is_student=False, phone='13800000000')
        self.users['teacher1'] = make('teacher1@demo.com', 'teacher1', PASSWORDS['teacher'], '张启航', U.TEACHER,
                                      is_staff=True, is_student=False, phone='13800000001', major='创新创业教育')
        self.users['teacher2'] = make('teacher2@demo.com', 'teacher2', PASSWORDS['teacher'], '李明澈', U.TEACHER,
                                      is_staff=True, is_student=False, phone='13800000002', major='软件工程')
        self.users['approver'] = make('approver@demo.com', 'approver', PASSWORDS['approver'], '秦若兰', U.SENS_APPROVER,
                                      is_staff=True, is_student=False, phone='13800000003', major='科研管理')
        for idx, m in enumerate(CORE_MEMBERS, 1):
            self.users[m['key']] = make(f'leader{idx}@demo.com', f'leader{idx}', PASSWORDS['leader'], m['name'], U.MEMBER,
                                        grade=m['grade'], major=m['major'], phone=m['phone'], is_student=True)
        for idx, (key, name, major, grade, role) in enumerate(ASSISTANTS, 1):
            self.users[key] = make(f'member{idx}@demo.com', f'member{idx}', PASSWORDS['member'], name, U.MEMBER,
                                   grade=grade, major=major, phone=f'1382000000{idx}', is_student=True)

    def create_projects_and_members(self):
        for item in PROJECTS:
            leader = self.users[item['leader']]
            project = Project.objects.create(
                name=item['name'], code=item['code'], leader=leader, current_stage=item['current_stage'],
                start_date=date(2025, 9, 10), planned_end_date=date(2026, 10, 30), status=item['status'],
                priority=item['priority'], intro=item['intro'], last_leader_update=aware(2026, 6, 28, 21, 30),
            )
            self.projects.append(project)
            self.project_by_code[project.code] = project
            self.project_members[project.code] = []
            for key in item['members']:
                if key == item['leader']:
                    role = ProjectMember.RoleInProject.LEADER
                elif key in item.get('deputies', []):
                    role = ProjectMember.RoleInProject.CORE
                else:
                    role = ProjectMember.RoleInProject.PARTICIPANT
                pm = ProjectMember.objects.create(project=project, user=self.users[key], role_in_project=role)
                self.project_members[project.code].append(pm.user)

    def create_project_histories(self):
        base_date = datetime(2025, 9, 12, 9, 0)
        for p in self.projects:
            max_stage = p.current_stage
            previous = None
            for idx, (stage, note) in enumerate(STAGE_FLOW):
                if stage > max_stage:
                    break
                log = ProjectStageLog.objects.create(
                    project=p, from_stage=previous, to_stage=stage, operator=p.leader,
                    note=f'{p.code}：{note}',
                )
                ProjectStageLog.objects.filter(pk=log.pk).update(created_at=timezone.make_aware(base_date + timedelta(days=idx * 24 + self.projects.index(p) * 3)))
                previous = stage
            # 人员变动没有独立模型，用操作日志保留变动痕迹。
            if p.code in ('DEMO-2026-002', 'DEMO-2026-005'):
                OperationLog.objects.create(
                    operator=p.leader, operation_type=OperationLog.OperationType.UPDATE, module='projects',
                    object_type='ProjectMember', object_id=str(p.id), request_method='PATCH', request_path=f'/api/projects/{p.id}/members/',
                    response_status=200, is_success=True,
                    description=f'【演示】{p.name} 进行人员变动：1 名调研成员退出，新增 {self.users["member8"].name if p.code == "DEMO-2026-002" else self.users["member7"].name} 负责运营/票据整理。',
                    request_data={'change_type': 'member_change', 'project_code': p.code},
                )

            OperationLog.objects.create(
                operator=p.leader, operation_type=OperationLog.OperationType.UPDATE, module='projects',
                object_type='ProjectDirection', object_id=str(p.id), request_method='PATCH', request_path=f'/api/projects/{p.id}/direction/',
                response_status=200, is_success=True,
                description=f'【演示】{p.name} 方向变化：根据多项比赛评审意见，将表达重点调整为“真实场景验证 + 可落地商业闭环 + 成果归档”。',
                request_data={'change_type': 'direction_change', 'project_code': p.code, 'timeline_event_type': 'direction_change'},
            )

    def create_competitions(self):
        """为每个项目生成多比赛并行记录：小挑/大挑全覆盖，数字中国仅 2 个项目。"""
        for code, rows in PROJECT_COMPETITION_MATRIX.items():
            p = self.project_by_code[code]
            for order, (comp_key, level, promoted, awarded, award_level, current_stage) in enumerate(rows, 1):
                tpl = COMPETITION_LIBRARY[comp_key]
                status = Competition.Status.COMPLETED if current_stage in ('已结束', '市赛止步', '省赛已结束', '国赛已完成', '全国决赛已完成', '获奖归档') else Competition.Status.ONGOING
                Competition.objects.create(
                    project=p,
                    name=tpl['name'],
                    comp_type=tpl['comp_type'],
                    level=level,
                    organizer=tpl['organizer'],
                    register_date=tpl['register_date'],
                    material_deadline=tpl['material_deadline'],
                    review_date=tpl['review_date'],
                    defense_date=tpl['defense_date'],
                    school_date=tpl['school_date'],
                    city_date=tpl['city_date'],
                    province_date=tpl['province_date'],
                    national_date=tpl['national_date'],
                    result_date=tpl['result_date'],
                    status=status,
                    is_promoted=promoted,
                    is_awarded=awarded,
                    award_level=award_level,
                    current_stage=current_stage,
                    not_promoted_reason='' if promoted else '演示数据：材料完整度和落地证明不足，止步当前层级。',
                    review_summary=(
                        f'{p.code} 同时参加多项赛事，本条记录用于展示“同一项目多线参赛、不同赛事阶段错位、'
                        f'部分赛事止步市/省赛、少数赛事进入国赛”的真实管理场景。'
                    ),
                    improvement_suggestion='补充真实用户数据、落地单位证明、财务测算、项目视频和答辩问答清单。',
                )
                OperationLog.objects.create(
                    operator=p.leader,
                    operation_type=OperationLog.OperationType.CREATE,
                    module='competitions',
                    object_type='Competition',
                    object_id=f'{p.code}-{comp_key}',
                    request_method='POST',
                    request_path=f'/api/competitions/demo/{p.id}/',
                    response_status=201,
                    is_success=True,
                    description=f'【演示】{p.name} 新增参赛线：{tpl["name"]}，当前阶段：{current_stage}。',
                    request_data={'project_code': p.code, 'competition_key': comp_key, 'timeline_event_type': 'competition_node'},
                )

    def create_tasks(self):
        task_templates = [
            ('完成需求调研与访谈纪要', Task.Status.DONE, -120, 1),
            ('项目计划书 v2.0 修订', Task.Status.DONE, -88, 1),
            ('核心原型开发与联调', Task.Status.DOING, 15, 2),
            ('网评材料提交与证明归档', Task.Status.PENDING_REVIEW, 4, 2),
            ('路演 PPT 初稿与讲稿校对', Task.Status.DOING, 10, 3),
            ('经费票据整理与公开台账', Task.Status.OVERDUE, -3, 4),
            ('知识产权申请材料初稿', Task.Status.TODO, 28, 5),
        ]
        for p in self.projects:
            members = self.project_members[p.code]
            for i, (title, status, delta, assignee_index) in enumerate(task_templates, 1):
                assignee = members[assignee_index % len(members)]
                task = Task.objects.create(
                    project=p, title=f'{p.code} {title}', assignee=assignee, creator=p.leader,
                    description=f'{p.name}：{title}。用于展示任务状态、协作者、逾期和审核流程。',
                    deadline=timezone.now() + timedelta(days=delta), status=status,
                    completed_at=timezone.now() - timedelta(days=abs(delta) // 2) if status == Task.Status.DONE else None,
                    reviewer=p.leader if status in (Task.Status.PENDING_REVIEW, Task.Status.DONE) else None,
                    delay_reason='票据还缺两张交通发票，等待经办人补传。' if status == Task.Status.OVERDUE else '',
                )
                task.collaborators.set([u for u in members[:4] if u != assignee])
                TaskLog.objects.create(task=task, from_status='', to_status=Task.Status.TODO, operator=p.leader)
                if status != Task.Status.TODO:
                    TaskLog.objects.create(task=task, from_status=Task.Status.TODO, to_status=status, operator=assignee)

    def create_finance(self):
        categories = [
            (FinanceExpense.Category.COMPETITION_FEE, '比赛报名与平台服务费'),
            (FinanceExpense.Category.PRINTING, '计划书与展板打印'),
            (FinanceExpense.Category.TRAVEL, '调研交通与省赛差旅'),
            (FinanceExpense.Category.SOFTWARE, '云服务与软件订阅'),
            (FinanceExpense.Category.PROMOTION, '宣传物料与路演展架'),
        ]
        for idx, p in enumerate(self.projects, 1):
            bonus = money(str(8000 + idx * 2500))
            other = money(str(2000 + idx * 700))
            amounts = [money(str(450 + idx * 90)), money(str(780 + idx * 120)), money(str(1260 + idx * 210)), money(str(1680 + idx * 180)), money(str(620 + idx * 75))]
            FinanceIncome.objects.create(
                project=p, title=f'{p.code} 比赛奖金', amount=bonus,
                income_type=FinanceIncome.IncomeType.BONUS,
                income_date=date(2026, 2, min(20, 5 + idx)),
                source='赛事奖金', reference_number=f'DEMO-BONUS-{p.code}',
                recorded_by=p.leader,
            )
            FinanceIncome.objects.create(
                project=p, title=f'{p.code} 项目配套经费', amount=other,
                income_type=FinanceIncome.IncomeType.GRANT,
                income_date=date(2026, 3, min(20, 5 + idx)),
                source='团队项目经费', reference_number=f'DEMO-GRANT-{p.code}',
                recorded_by=p.leader,
            )
            for j, ((cat, title), amount) in enumerate(zip(categories, amounts), 1):
                reimbursement_status = (
                    FinanceExpense.ReimbursementStatus.PAID if j <= 3
                    else FinanceExpense.ReimbursementStatus.APPROVED if j == 4
                    else FinanceExpense.ReimbursementStatus.PENDING
                )
                spender = self.project_members[p.code][j % len(self.project_members[p.code])]
                expense = FinanceExpense.objects.create(
                    project=p, title=f'{p.code} {title}', amount=amount, spender=spender,
                    expense_date=date(2026, min(6, 2 + j), min(27, 3 + idx + j)), category=cat,
                    purpose=f'{p.name} 参赛准备支出：{title}',
                    reimbursement_status=reimbursement_status,
                    applied_by=spender, applied_at=timezone.now() - timedelta(days=12 - j),
                    reviewer=self.users['teacher1'] if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else None,
                    reviewed_at=timezone.now() - timedelta(days=8 - j) if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else None,
                    review_opinion='用途与票据核验通过。' if reimbursement_status != FinanceExpense.ReimbursementStatus.PENDING else '',
                    paid_by=self.users['teacher1'] if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else None,
                    paid_at=timezone.now() - timedelta(days=4 - j) if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else None,
                    payment_method='银行转账' if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else '',
                    payment_reference=f'DEMO-PAY-{p.code}-{j}' if reimbursement_status == FinanceExpense.ReimbursementStatus.PAID else '',
                )
                self.expenses.append(expense)
                if j <= 2:
                    filename, data = self.get_asset_bytes('receipts', p.code, f'receipt_{j}.jpg')
                    rec = FinanceReceipt.objects.create(expense=expense, uploaded_by=expense.spender)
                    rec.file.save(filename, ContentFile(data), save=True)
            budget = FinanceBudget.objects.filter(project=p).order_by('-updated_at').first()
            budget.period = '2026春季'
            budget.save(update_fields=['period', 'updated_at'])

    def create_files_and_versions(self):
        for p in self.projects:
            leader = p.leader
            plan_docx = self.save_asset(p, 'plan_docx', f'{p.code} 项目计划书 DOCX v2.0', FileAsset.Level.INTERNAL, leader,
                                        'project_plans', '项目计划书.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', version=2)
            plan_pdf = self.save_asset(p, 'plan_pdf', f'{p.code} 项目计划书 PDF v2.0', FileAsset.Level.PUBLIC, leader,
                                       'project_plans', '项目计划书.pdf', 'application/pdf', version=2)
            summary_xlsx = self.save_asset(
                p, 'summary_xlsx', f'{p.code} 项目数据简表 XLSX',
                FileAsset.Level.INTERNAL, leader, 'project_tables',
                '项目数据简表.xlsx',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            ppt = self.save_asset(p, 'roadshow_ppt', f'{p.code} 路演 PPT 占位文件', FileAsset.Level.INTERNAL, leader,
                                  'roadshow_placeholders', '路演PPT_占位.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', version=1)
            script = self.save_asset(p, 'roadshow_script', f'{p.code} 路演稿 Word 演示文件', FileAsset.Level.INTERNAL, leader,
                                     'roadshow_placeholders', '路演稿_演示.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', version=1)
            for asset, suffix, note in [
                (plan_docx, '项目计划书.docx', '根据指导老师意见补充市场规模和竞品分析'),
                (plan_pdf, '项目计划书.pdf', '导出 PDF 版用于正式提交'),
            ]:
                filename, data = self.get_asset_bytes('project_plans', p.code, suffix)
                v1 = FileVersion.objects.create(file_asset=asset, version=1, uploader=leader)
                v1.file.save('v1_' + filename, ContentFile(data), save=True)
                v2 = FileVersion.objects.create(file_asset=asset, version=2, uploader=leader)
                v2.file.save('v2_' + filename, ContentFile(data), save=True)
            OperationLog.objects.create(operator=leader, operation_type=OperationLog.OperationType.UPDATE, module='files', object_type='FileAsset',
                                        object_id=str(plan_docx.id), request_method='PATCH', request_path=f'/api/files/{plan_docx.id}/', response_status=200,
                                        description=f'【演示】{p.name} 文件修改：项目计划书从 v1 修订为 v2，{note if "note" in locals() else "完成版本归档"}。',
                                        request_data={
                                            'file': plan_docx.name,
                                            'version': 2,
                                            'related_spreadsheet': summary_xlsx.name,
                                        })
            # 一份敏感级别的简版签名页，用于敏感资料附件流程演示。
            signature_pdf = self.build_minimal_pdf([
                'DEMO TEAM SIGNATURE PAGE',
                f'Project: {p.code}',
            ])
            signature = FileAsset.objects.create(project=p, name=f'{p.code} 团队成员签名页（敏感）', level=FileAsset.Level.SENSITIVE,
                                                 size=len(signature_pdf), content_type='application/pdf', uploader=leader, version=1)
            signature.file.save(f'{p.code}_signature_sensitive.pdf', ContentFile(signature_pdf), save=True)
            self.files[(p.code, 'signature')] = signature

    def create_scheduled_reports(self):
        """创建覆盖三种格式、三种频率和不同账户的报表演示计划。"""
        definitions = [
            {
                'name': '每日项目经营概览',
                'description': '每日汇总项目状态与阶段分布，供系统管理员查看。',
                'source': 'project',
                'group_by': 'status',
                'creator': 'admin',
                'recipients': ['admin', 'teacher1'],
                'frequency': ScheduledReport.Frequency.DAILY,
                'format': ScheduledReport.FileFormat.XLSX,
                'execution_time': time(8, 30),
                'run_demo': True,
            },
            {
                'name': '每周任务交付报告',
                'description': '每周一汇总任务进度、逾期项和项目分布。',
                'source': 'task',
                'group_by': 'project',
                'creator': 'teacher1',
                'recipients': ['teacher1', 'leader1', 'leader2'],
                'frequency': ScheduledReport.Frequency.WEEKLY,
                'format': ScheduledReport.FileFormat.DOCX,
                'execution_time': time(9, 0),
                'weekday': 0,
                'run_demo': True,
            },
            {
                'name': '每月经费执行报告',
                'description': '每月汇总各项目经费支出及类别结构。',
                'source': 'finance',
                'group_by': 'project',
                'creator': 'leader6',
                'recipients': ['leader6', 'teacher2'],
                'frequency': ScheduledReport.Frequency.MONTHLY,
                'format': ScheduledReport.FileFormat.PDF,
                'execution_time': time(10, 0),
                'day_of_month': 5,
                'run_demo': True,
            },
            {
                'name': '每周比赛推进简报',
                'description': '按比赛级别展示参赛、晋级和获奖进展。',
                'source': 'competition',
                'group_by': 'level',
                'creator': 'leader1',
                'recipients': ['leader1', 'teacher1'],
                'frequency': ScheduledReport.Frequency.WEEKLY,
                'format': ScheduledReport.FileFormat.XLSX,
                'execution_time': time(16, 30),
                'weekday': 4,
            },
        ]
        for definition in definitions:
            creator = self.users[definition['creator']]
            report = CustomReport.objects.create(
                name=definition['name'],
                description=definition['description'],
                report_type=definition['source'],
                config={
                    'data_source': definition['source'],
                    'group_by': definition['group_by'],
                    'chart_type': 'table',
                },
                created_by=creator,
                is_scheduled=True,
            )
            schedule = ScheduledReport.objects.create(
                report=report,
                created_by=creator,
                frequency=definition['frequency'],
                file_format=definition['format'],
                execution_time=definition['execution_time'],
                weekday=definition.get('weekday', 0),
                day_of_month=definition.get('day_of_month', 1),
                timezone='Asia/Shanghai',
                is_active=True,
            )
            schedule.recipients.set([
                self.users[key] for key in definition['recipients']
            ])
            schedule.next_run = compute_next_run(schedule)
            schedule.save(update_fields=['next_run'])
            if definition.get('run_demo'):
                execute_scheduled_report(schedule, user=creator)

    def create_skills_and_work_schedules(self):
        skill_objs = {name: SkillTag.objects.create(name=name) for name in SKILLS}
        assignments = {
            'leader1': ['项目统筹', '商业计划书', '比赛申报'], 'leader2': ['商业计划书', '用户调研', '路演答辩'],
            'leader3': ['后端开发', '数据治理', '知识产权'], 'leader4': ['算法建模', '数据治理', '文档归档'],
            'leader5': ['UI设计', 'PPT制作', '视频剪辑'], 'leader6': ['财务预算', '比赛申报', '路演答辩'],
        }
        for key, names in assignments.items():
            for i, s in enumerate(names, 3):
                MemberSkill.objects.create(user=self.users[key], skill=skill_objs[s], proficiency=min(i, 5))
        for i, key in enumerate([m['key'] for m in CORE_MEMBERS] + [a[0] for a in ASSISTANTS], 1):
            FlexibleWorkSchedule.objects.create(
                user=self.users[key], period_start=date(2026, 7, 1), period_end=date(2026, 7, 15),
                work_hours=Decimal(str(18 + (i % 5) * 4)), detail={'weekday_evening': '2h', 'weekend': f'{4 + i % 4}h'},
                can_offline=i % 2 == 0, can_urgent=i % 3 == 0, is_saturated=i in (4, 9, 13),
                notes='省赛/国赛冲刺期可临时加班。' if i % 3 == 0 else '按常规节奏推进。',
            )

    def create_contributions_and_rankings(self):
        contrib_types = [
            Contribution.ContributionType.PROJECT_LEADER, Contribution.ContributionType.STAGE_TASK,
            Contribution.ContributionType.COMPETITION, Contribution.ContributionType.FILE_UPLOAD,
            Contribution.ContributionType.FINANCE_MANAGE, Contribution.ContributionType.IP_MATERIAL,
        ]
        for p in self.projects:
            members = self.project_members[p.code]
            scores = []
            for rank_idx, u in enumerate(members, 1):
                score = Decimal(str(max(45, 96 - rank_idx * 7 + (len(p.code) % 3))))
                Contribution.objects.create(
                    user=u, project=p, contribution_type=contrib_types[rank_idx % len(contrib_types)],
                    description=f'{p.name}：完成阶段性任务并参与比赛材料迭代。',
                    content=f'{u.name} 在 {p.code} 中承担核心工作，包含材料、开发、答辩或经费归档。',
                    score=score, weight=score, status=Contribution.Status.APPROVED,
                    proof_file=self.files.get((p.code, 'plan_pdf')), filled_by=p.leader, reviewer=p.leader,
                    reviewed_at=timezone.now() - timedelta(days=rank_idx), review_opinion='贡献记录属实，纳入本期排序。', period='2026春季',
                )
                scores.append((u, score, rank_idx))
            # 一条待审核和一条退出成员贡献，测试列表状态。
            Contribution.objects.create(user=members[-1], project=p, contribution_type=Contribution.ContributionType.EXITED_CONTRIBUTION,
                                        content='前期参与问卷整理，后因实习退出，仅保留已完成贡献。', score=Decimal('12'), weight=Decimal('12'),
                                        status=Contribution.Status.PENDING, filled_by=p.leader, period='2026春季')
            for u, score, r in scores:
                MemberRanking.objects.create(user=u, project=p, period='2026春季', status=MemberRanking.Status.CONFIRMED,
                                             total_score=score, rank=r, task_completed_count=max(1, 7 - r), project_count=2,
                                             competition_count=len(PROJECT_COMPETITION_MATRIX.get(p.code, [])), ip_contribution_count=1 if r <= 3 else 0, is_published=True, is_public=True)
        # 排名异议：一个负责人初审，一个老师最终驳回/通过。
        for p in self.projects[:3]:
            ranking = MemberRanking.objects.filter(project=p).order_by('-rank').first()
            RankingObjection.objects.create(
                ranking=ranking, objector=ranking.user,
                content='认为调研访谈和现场答辩彩排未充分计入贡献分。', status=RankingObjection.Status.LEADER_REVIEWED,
                leader_opinion='已复核任务记录，建议补充一条调研证明后微调分值。', leader_reviewer=p.leader,
                leader_reviewed_at=timezone.now() - timedelta(days=2), handler=p.leader,
            )

    def create_ip_flow(self):
        roles = [IPApplicationContributor.ContributorRole.MAIN_WRITER, IPApplicationContributor.ContributorRole.CODE_PROVIDER,
                 IPApplicationContributor.ContributorRole.DOCUMENT_WRITER, IPApplicationContributor.ContributorRole.EXECUTOR]
        for idx, p in enumerate(self.projects, 1):
            ip_type = IntellectualPropertyApplication.IPType.SOFTWARE_COPYRIGHT if idx in (1, 2, 5, 6) else IntellectualPropertyApplication.IPType.INVENTION_PATENT
            status = [IntellectualPropertyApplication.Status.WRITING, IntellectualPropertyApplication.Status.TEACHER_CONFIRM,
                      IntellectualPropertyApplication.Status.ACCEPTED, IntellectualPropertyApplication.Status.RETURNED,
                      IntellectualPropertyApplication.Status.RESUBMITTED, IntellectualPropertyApplication.Status.AUTHORIZED][idx - 1]
            app = IntellectualPropertyApplication.objects.create(
                title=f'{p.name} 核心系统软件/算法成果', application_code=f'IP-DEMO-2026-{idx:03d}', ip_type=ip_type,
                related_project=p, status=status, main_writer=self.project_members[p.code][1], applicant_executor=self.users['leader6'],
                material_manager=self.users['member6'], project_reviewer=p.leader, teacher_confirmer=self.users['teacher2'],
                start_date=date(2026, 4, 1), submit_date=date(2026, 6, 5) if idx >= 3 else None,
                accepted_date=date(2026, 6, 18) if idx in (3, 6) else None,
                authorized_date=date(2026, 6, 28) if idx == 6 else None, return_count=1 if idx in (4, 5) else 0,
                current_problem='交底书中技术效果描述不够充分，需补充流程图。' if idx in (4, 5) else '',
                intro='用于展示知识产权申请、责任分工、退回修改、材料版本和异议处理流程。', created_by=p.leader,
            )
            self.ip_apps.append(app)
            for j, u in enumerate(self.project_members[p.code][:4]):
                IPApplicationContributor.objects.create(application=app, user=u, role=roles[j],
                                                        contribution_description=f'{u.name} 负责 {roles[j].label} 相关材料。',
                                                        responsibility_description='按时间节点提交可复核版本，并对退回意见负责。',
                                                        is_confirmed=True, confirmed_by=p.leader, confirmed_at=timezone.now() - timedelta(days=j + 1))
            IPMaterialVersion.objects.create(application=app, file_asset=self.files[(p.code, 'plan_docx')], material_type=IPMaterialVersion.MaterialType.MANUAL,
                                             version='v1', uploaded_by=self.project_members[p.code][1], change_note='根据项目计划书整理软件说明书初稿。')
            IPMaterialVersion.objects.create(application=app, file_asset=self.files[(p.code, 'plan_pdf')], material_type=IPMaterialVersion.MaterialType.ARCHIVE,
                                             version='v2', uploaded_by=p.leader, change_note='形成归档版材料。', is_final=idx in (3, 6))
            if idx in (4, 5):
                ret = IPReturnRecord.objects.create(application=app, return_time=aware(2026, 6, 20, 16, 30), return_source=IPReturnRecord.ReturnSource.RESEARCH_OFFICE,
                                                    return_reason='说明书中系统架构图与权利要求对应关系不清晰。',
                                                    responsibility_type=IPReturnRecord.ResponsibilityType.WRITING_PROBLEM,
                                                    responsible_user=self.project_members[p.code][1], assigned_by=p.leader,
                                                    modify_deadline=aware(2026, 6, 27, 18, 0), actual_modifier=self.project_members[p.code][1],
                                                    modify_description='已补充模块流程图、关键算法说明和应用场景边界。',
                                                    result=IPReturnRecord.ReturnResult.RESUBMITTED, proof_file=self.files[(p.code, 'plan_docx')])
                IPMaterialVersion.objects.create(application=app, file_asset=self.files[(p.code, 'plan_docx')], material_type=IPMaterialVersion.MaterialType.FEEDBACK,
                                                 version='v2-return-fix', uploaded_by=self.project_members[p.code][1], related_return_record=ret,
                                                 change_note='针对科研处退回意见修订后的版本。')
            if idx in (2, 5):
                IPObjection.objects.create(application=app, objector=self.project_members[p.code][-1], objection_type=IPObjection.ObjectionType.MATERIAL_CREDIT,
                                           content='认为本人参与路演材料与说明书图表整理，应在贡献说明中体现。', proof_file=self.files[(p.code, 'roadshow_script')],
                                           status=IPObjection.ObjectionStatus.LEADER_REVIEWED, leader_opinion='同意补充为材料整理协助贡献，但不调整主导撰写人。',
                                           leader_reviewer=p.leader, leader_reviewed_at=timezone.now() - timedelta(days=1))

    def create_sensitive_flow(self):
        status_cycle = [SensitiveAccessRequest.Status.APPROVED, SensitiveAccessRequest.Status.PENDING, SensitiveAccessRequest.Status.REJECTED, SensitiveAccessRequest.Status.EXPIRED]
        for idx, p in enumerate(self.projects, 1):
            sd = SensitiveData.objects.create(data_type=SensitiveData.DataType.SIGNATURE, title=f'{p.code} 参赛承诺书签名页', display_name=f'{p.name} 签名页（已脱敏）',
                                             file_attachment=self.files[(p.code, 'signature')], project=p, uploader=p.leader, key_version=1)
            raw = f'演示敏感内容：{p.code} 团队签名页，成员身份证后四位 10{idx}8，仅用于本地演示。'
            try:
                sd.encrypt_content(raw)
            except Exception:
                sd.encrypted_content = f'ENCRYPTED-DEMO::{p.code}::{idx}'
                sd.is_encrypted = True
                sd.save(update_fields=['encrypted_content', 'is_encrypted'])
            status = status_cycle[(idx - 1) % len(status_cycle)]
            approved_at = timezone.now() - timedelta(hours=idx) if status in (SensitiveAccessRequest.Status.APPROVED, SensitiveAccessRequest.Status.EXPIRED) else None
            expires = timezone.now() + timedelta(hours=12) if status == SensitiveAccessRequest.Status.APPROVED else timezone.now() - timedelta(hours=2) if status == SensitiveAccessRequest.Status.EXPIRED else None
            SensitiveAccessRequest.objects.create(sensitive_data=sd, applicant=self.project_members[p.code][1], reason='用于核对正式报名系统中的团队承诺书签名页。',
                                                  usage_scenario='比赛报名材料复核/学院归档检查', project=p, expected_use_time=timezone.now() + timedelta(days=1),
                                                  request_note='只在线查看，不外传。' if idx % 2 else '需要下载后上传比赛系统。', is_download=idx % 2 == 0,
                                                  status=status, approver=self.users['approver'] if status != SensitiveAccessRequest.Status.PENDING else None,
                                                  approval_comment='同意限时查看，注意脱敏和日志留存。' if status == SensitiveAccessRequest.Status.APPROVED else '当前申请场景不充分，请补充用途。' if status == SensitiveAccessRequest.Status.REJECTED else '',
                                                  approval_opinion='同意限时查看，注意脱敏和日志留存。' if status == SensitiveAccessRequest.Status.APPROVED else '当前申请场景不充分，请补充用途。' if status == SensitiveAccessRequest.Status.REJECTED else '',
                                                  approved_at=approved_at, access_expires_at=expires,
                                                  viewed_at=timezone.now() - timedelta(minutes=20) if status == SensitiveAccessRequest.Status.APPROVED else None)

    def create_notifications(self):
        for p in self.projects:
            Notification.objects.create(notification_type=Notification.NotificationType.PROJECT, title=f'【演示】{p.code} 阶段推进提醒',
                                        content=f'{p.name} 已进入 {p.get_current_stage_display()}，请负责人更新阶段说明和材料清单。',
                                        priority=Notification.Priority.HIGH, recipient=p.leader, sender=self.users['teacher1'], related_object_type='Project', related_object_id=p.id)
            Notification.objects.create(notification_type=Notification.NotificationType.FINANCE, title=f'【演示】{p.code} 经费票据补传提醒',
                                        content='当前经费台账存在待报销金额，请经办人补齐票据并保持经费公开。',
                                        priority=Notification.Priority.NORMAL, recipient=self.project_members[p.code][-1], sender=p.leader, related_object_type='FinanceBudget', related_object_id=p.id)
        Notification.objects.create(notification_type=Notification.NotificationType.SYSTEM, title='【演示】P0 前端可用性回归已修复，请进行截图验收',
                                    content='请重点复核 Dashboard、项目、比赛、经费和移动端布局。', priority=Notification.Priority.URGENT,
                                    recipient=None, sender=self.users['admin'])

    def create_import_tasks(self):
        import_dir = self.assets_dir() / 'imports'
        projects_file = str(import_dir / 'projects_demo.xlsx')
        finance_file = str(import_dir / 'finance_demo_with_errors.xlsx')
        ImportTask.objects.create(module=ImportTask.Module.PROJECTS, file_path=projects_file,
                                  status=ImportTask.Status.CONFIRMED, field_mapping={'项目名称': 'name', '项目编号': 'code', '负责人邮箱': 'leader'},
                                  preview_data=[{'项目编号': p.code, '项目名称': p.name} for p in self.projects[:3]], snapshot=[p.id for p in self.projects],
                                  total_rows=6, valid_rows=6, error_rows=0, error_details={}, created_by=self.users['admin'])
        ImportTask.objects.create(module=ImportTask.Module.FINANCE, file_path=finance_file,
                                  status=ImportTask.Status.PREVIEWED, field_mapping={'支出标题': 'title', '金额': 'amount', '类别': 'category'},
                                  preview_data=[{'支出标题': '打印费', '金额': '480.00'}, {'支出标题': '差旅费', '金额': '待确认'}], snapshot=[],
                                  total_rows=2, valid_rows=1, error_rows=1, error_details={'2': '金额格式不正确'}, created_by=self.users['leader6'])

    def create_operation_logs(self):
        actions = [
            (OperationLog.OperationType.LOGIN, 'users', '登录系统并进入 Dashboard'),
            (OperationLog.OperationType.UPDATE, 'projects', '更新项目阶段和负责人说明'),
            (OperationLog.OperationType.UPLOAD, 'files', '上传项目计划书和路演演示文件'),
            (OperationLog.OperationType.APPROVE, 'contributions', '审核成员贡献记录'),
            (OperationLog.OperationType.EXPORT, 'finance', '导出经费公开台账'),
            (OperationLog.OperationType.VIEW_SENSITIVE, 'sensitive', '审批后限时查看敏感资料'),
        ]
        for p in self.projects:
            for idx, (op, module, desc) in enumerate(actions, 1):
                OperationLog.objects.create(operator=self.project_members[p.code][idx % len(self.project_members[p.code])], operation_type=op, module=module,
                                            object_type='Project', object_id=str(p.id), request_method='GET' if op in (OperationLog.OperationType.LOGIN, OperationLog.OperationType.EXPORT, OperationLog.OperationType.VIEW_SENSITIVE) else 'POST',
                                            request_path=f'/api/{module}/demo/{p.id}/', request_ip=f'192.168.10.{20 + idx}',
                                            user_agent='Mozilla/5.0 Demo Browser', request_data={'project_code': p.code, 'demo': True}, response_status=200, is_success=True,
                                            description=f'【演示】{p.name}：{desc}。')
        OperationLog.objects.create(operator=self.users['admin'], operation_type=OperationLog.OperationType.OTHER, module='qa', object_type='FrontendRegression',
                                    object_id='P3-P0-FIX', request_method='POST', request_path='/qa/frontend/p0-regression/', request_ip='127.0.0.1',
                                    response_status=200, is_success=True, description='【演示】Codex 完成 P0 前端可用性回归修复，进入截图验收和演示数据验证阶段。')

    # ==================================================================
    # v1.2 新增：集成配置、集成日志、用户偏好、协作成员技能、数据调整
    # ==================================================================

    def create_integration_configs(self):
        """创建第三方集成配置（企业微信/Webhook/邮件）"""
        IntegrationConfig.objects.create(
            name='团队通知-企业微信群机器人',
            provider=IntegrationConfig.Provider.WECOM,
            webhook_url='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo-wecom-key-0001',
            app_id='',
            encrypted_secret='',
            enabled=True,
            created_by=self.users['admin'],
        )
        IntegrationConfig.objects.create(
            name='外部系统对接-通用Webhook',
            provider=IntegrationConfig.Provider.WEBHOOK,
            webhook_url='https://hooks.demo.example.com/team-management/notify',
            app_id='',
            encrypted_secret='',
            enabled=True,
            created_by=self.users['admin'],
        )
        IntegrationConfig.objects.create(
            name='邮件通知渠道（备用）',
            provider=IntegrationConfig.Provider.EMAIL,
            webhook_url='',
            app_id='smtp.demo.edu.cn',
            encrypted_secret='',
            enabled=False,
            created_by=self.users['admin'],
        )

    def create_integration_logs(self):
        """创建集成调用历史日志，模拟推送记录"""
        log_entries = [
            ('wecom', 'task_overdue', '企业微信群机器人', 'success',
             {'title': '任务延期提醒: 经费票据整理与公开台账', 'content': '任务已逾期，请尽快处理。'},
             '{"errcode":0,"errmsg":"ok"}', ''),
            ('wecom', 'contribution_pending', '企业微信群机器人', 'success',
             {'title': '贡献记录待审核: 智农云链', 'content': '有1条贡献记录待审核。'},
             '{"errcode":0,"errmsg":"ok"}', ''),
            ('webhook', 'competition_milestone', '通用Webhook', 'success',
             {'title': '比赛节点提醒: 大挑国赛', 'content': 'DEMO-2026-001 大挑国赛答辩日临近。'},
             '{"status":"received"}', ''),
            ('wecom', 'sensitive_request', '企业微信群机器人', 'failed',
             {'title': '敏感资料审批提醒', 'content': '赵若安申请查看签名页。'},
             '{"errcode":93000,"errmsg":"invalid webhook url"}',
             '企业微信返回错误: invalid webhook url（演示数据，URL 为模拟值）'),
            ('webhook', 'test', '通用Webhook', 'success',
             {'title': '群机器人推送测试', 'content': '这是一条测试消息。'},
             '{"status":"received","code":0}', ''),
            ('wecom', 'task_overdue', '企业微信群机器人', 'failed',
             {'title': '任务延期提醒: 路演PPT初稿', 'content': '任务已逾期3天。'},
             '', 'Connection timeout: 连接超时（演示数据）'),
            ('wecom', 'custom', '企业微信群机器人', 'success',
             {'title': '周报提醒', 'content': '请各项目负责人本周五前提交进展。'},
             '{"errcode":0,"errmsg":"ok"}', ''),
            ('webhook', 'contribution_pending', '通用Webhook', 'failed',
             {'title': '贡献记录待审核: 青碳校园', 'content': '有1条贡献记录待审核。'},
             '', 'HTTP 500: Internal Server Error（演示数据）'),
        ]
        for provider, event_type, target, status, payload, response, error in log_entries:
            IntegrationLog.objects.create(
                provider=provider,
                event_type=event_type,
                target=target,
                payload=payload,
                status=status,
                response=response,
                error_message=error,
            )

    def create_user_preferences(self):
        """为部分用户创建个性化偏好设置"""
        UserPreference.objects.create(
            user=self.users['admin'],
            theme_color='blue',
            default_landing='dashboard',
            sidebar_collapsed=False,
            notification_sound=True,
            items_per_page=20,
            dashboard_layout={'cards': ['stats', 'timeline', 'gantt', 'finance']},
        )
        UserPreference.objects.create(
            user=self.users['leader1'],
            theme_color='green',
            default_landing='projects',
            sidebar_collapsed=False,
            notification_sound=True,
            items_per_page=20,
            dashboard_layout={'cards': ['stats', 'tasks', 'timeline']},
        )
        UserPreference.objects.create(
            user=self.users['teacher1'],
            theme_color='purple',
            default_landing='dashboard',
            sidebar_collapsed=True,
            notification_sound=False,
            items_per_page=50,
            dashboard_layout={'cards': ['stats', 'competitions', 'finance']},
        )
        UserPreference.objects.create(
            user=self.users['leader4'],
            theme_color='orange',
            default_landing='tasks',
            sidebar_collapsed=False,
            notification_sound=True,
            items_per_page=10,
            dashboard_layout={'cards': ['stats', 'tasks']},
        )

        configured_users = {'admin', 'leader1', 'teacher1', 'leader4'}
        preferred_themes = {
            'teacher2': 'green',
            'approver': 'orange',
            'leader2': 'blue',
            'leader3': 'purple',
            'leader5': 'green',
            'leader6': 'blue',
        }
        custom_primary_colors = {
            # 留一个非预设色账户，便于演示“任意主色 + 切换账户自动恢复”。
            'leader6': '#245c8a',
        }
        theme_cycle = ('blue', 'green', 'purple', 'orange')
        for key, user in self.users.items():
            if key in configured_users:
                continue
            suffix = ''.join(character for character in key if character.isdigit())
            cycle_index = int(suffix) - 1 if suffix else user.pk
            UserPreference.objects.create(
                user=user,
                theme_color=preferred_themes.get(
                    key, theme_cycle[cycle_index % len(theme_cycle)]
                ),
                primary_color=custom_primary_colors.get(
                    key, UserPreference.DEFAULT_PRIMARY_COLOR
                ),
            )

    def create_assistant_skills(self):
        """为 member1~8 分配技能标签（原脚本仅 leader 有技能）"""
        skill_objs = {s.name: s for s in SkillTag.objects.filter(name__in=SKILLS)}
        assignments = {
            'member1': ['前端开发', '文档归档'],
            'member2': ['数据治理', '文档归档'],
            'member3': ['用户调研', '商业计划书'],
            'member4': ['UI设计', 'PPT制作'],
            'member5': ['算法建模', '后端开发'],
            'member6': ['知识产权', '文档归档'],
            'member7': ['财务预算', 'PPT制作'],
            'member8': ['商业计划书', '路演答辩'],
        }
        for key, names in assignments.items():
            for i, s in enumerate(names, 3):
                MemberSkill.objects.create(
                    user=self.users[key],
                    skill=skill_objs[s],
                    proficiency=min(i, 5),
                )

    def post_adjust_data(self):
        """
        数据微调：
        1. 将 DEMO-2026-001（已有获奖比赛）项目阶段提升至 AWARDED
        2. 将前 2 个项目的逾期任务 overdue_reminded 标记为 True
        """
        # 1. 提升项目阶段为已获奖
        p001 = self.project_by_code.get('DEMO-2026-001')
        if p001:
            p001.current_stage = Project.Stage.AWARDED
            p001.save(update_fields=['current_stage'])
            # 补充阶段日志
            ProjectStageLog.objects.create(
                project=p001,
                from_stage=Project.Stage.NATIONAL_COMP,
                to_stage=Project.Stage.AWARDED,
                operator=p001.leader,
                note='DEMO-2026-001：大挑国赛获三等奖，进入成果归档阶段。',
            )

        # 2. 标记前2个项目的逾期任务已提醒
        for p in self.projects[:2]:
            overdue_task = Task.objects.filter(
                project=p, status=Task.Status.OVERDUE
            ).first()
            if overdue_task:
                overdue_task.overdue_reminded = True
                overdue_task.save(update_fields=['overdue_reminded'])

    def create_portal_publications(self):
        """为纯演示账号生成明确的逐项公开决策和成员授权。"""
        PortalSettings.objects.get_or_create(
            singleton_key='default',
            defaults={
                'team_name': '创新实践团队',
                'tagline': '项目实践 · 赛事成长 · 成果沉淀',
                'contact_email': 'teacher1@demo.com',
                'join_title': '加入创新实践团队',
                'join_message': '欢迎愿意持续参与项目、赛事和成果整理的同学联系我们。',
                'updated_by': self.users['teacher1'],
            },
        )
        for index, project in enumerate(self.projects):
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.PROJECT,
                object_id=project.id,
                defaults={
                    'is_public': True,
                    'is_featured': index < 3,
                    'display_order': index,
                    'updated_by': self.users['teacher1'],
                },
            )
        for index, application in enumerate(self.ip_apps):
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.IP_APPLICATION,
                object_id=application.id,
                defaults={
                    'is_public': application.status in ('authorized', 'archived'),
                    'is_featured': index == 0,
                    'display_order': index,
                    'updated_by': self.users['teacher1'],
                },
            )
        public_members = [
            self.users[key]
            for key in ('leader1', 'leader2', 'leader3', 'leader4', 'leader5', 'leader6')
        ]
        for index, member in enumerate(public_members):
            PortalPublication.objects.update_or_create(
                content_type=PortalPublication.ContentType.MEMBER,
                object_id=member.id,
                defaults={
                    'is_public': True,
                    'is_featured': index < 3,
                    'member_consent': True,
                    'display_order': index,
                    'updated_by': member,
                },
            )

    def clean_demo_data(self):
        self.stdout.write(self.style.WARNING('清理本命令生成的演示数据...'))
        # v1.2 新增数据清理
        IntegrationLog.objects.filter(provider__in=['wecom', 'webhook', 'email']).delete()
        IntegrationConfig.objects.filter(created_by__email__endswith='@demo.com').delete()
        demo_reports = CustomReport.objects.filter(created_by__email__endswith='@demo.com')
        for execution in (
            ScheduledReport.objects.filter(report__in=demo_reports)
            .prefetch_related('executions')
            .values_list('executions__file', flat=True)
        ):
            if execution:
                try:
                    (Path(settings.MEDIA_ROOT) / execution).unlink(missing_ok=True)
                except OSError:
                    pass
        demo_reports.delete()
        UserPreference.objects.filter(user__email__endswith='@demo.com').delete()
        demo_projects = Project.objects.filter(code__startswith='DEMO-2026-')
        legacy_demo_projects = Project.objects.filter(
            code__startswith='PROJ-',
            leader__email__endswith='@demo.com',
        )
        demo_projects = demo_projects | legacy_demo_projects
        demo_project_ids = list(demo_projects.values_list('id', flat=True))
        ip_apps = IntellectualPropertyApplication.objects.filter(application_code__startswith='IP-DEMO-')
        demo_user_ids = list(
            User.objects.filter(email__endswith='@demo.com').values_list('id', flat=True)
        )
        PortalPublication.objects.filter(
            content_type=PortalPublication.ContentType.PROJECT,
            object_id__in=demo_project_ids,
        ).delete()
        PortalPublication.objects.filter(
            content_type=PortalPublication.ContentType.IP_APPLICATION,
            object_id__in=ip_apps.values_list('id', flat=True),
        ).delete()
        PortalPublication.objects.filter(
            content_type=PortalPublication.ContentType.MEMBER,
            object_id__in=demo_user_ids,
        ).delete()
        OperationLog.objects.filter(description__contains='【演示】').delete()
        Notification.objects.filter(title__startswith='【演示】').delete()
        ImportTask.objects.filter(file_path__contains='competition_demo_files').delete()
        ImportTask.objects.filter(file_path__contains=str(Path('imports') / 'demo')).delete()
        IPObjection.objects.filter(application__in=ip_apps).delete()
        IPMaterialVersion.objects.filter(application__in=ip_apps).delete()
        IPReturnRecord.objects.filter(application__in=ip_apps).delete()
        IPApplicationContributor.objects.filter(application__in=ip_apps).delete()
        ip_apps.delete()
        RankingObjection.objects.filter(ranking__project_id__in=demo_project_ids).delete()
        MemberRanking.objects.filter(project_id__in=demo_project_ids).delete()
        Contribution.objects.filter(project_id__in=demo_project_ids).delete()
        SensitiveAccessRequest.objects.filter(project_id__in=demo_project_ids).delete()
        SensitiveData.objects.filter(project_id__in=demo_project_ids).delete()
        FinanceReceipt.objects.filter(expense__project_id__in=demo_project_ids).delete()
        FinanceExpense.objects.filter(project_id__in=demo_project_ids).delete()
        FinanceIncome.objects.filter(project_id__in=demo_project_ids).delete()
        FinanceBudget.objects.filter(project_id__in=demo_project_ids).delete()
        TaskLog.objects.filter(task__project_id__in=demo_project_ids).delete()
        Task.objects.filter(project_id__in=demo_project_ids).delete()
        FileVersion.objects.filter(file_asset__project_id__in=demo_project_ids).delete()
        FileAsset.objects.filter(project_id__in=demo_project_ids).delete()
        Competition.objects.filter(project_id__in=demo_project_ids).delete()
        ProjectStageLog.objects.filter(project_id__in=demo_project_ids).delete()
        ProjectMember.objects.filter(project_id__in=demo_project_ids).delete()
        demo_projects.delete()
        FlexibleWorkSchedule.objects.filter(user__email__endswith='@demo.com').delete()
        MemberSkill.objects.filter(user__email__endswith='@demo.com').delete()
        SkillTag.objects.filter(name__in=SKILLS).delete()
        User.objects.filter(email__endswith='@demo.com').delete()

    def print_summary(self):
        self.stdout.write(self.style.SUCCESS('\n========== 比赛型演示数据生成完成 =========='))
        self.stdout.write('账号：')
        self.stdout.write('  系统管理员：admin@demo.com / admin123456')
        self.stdout.write('  指导老师1：teacher1@demo.com / teacher123456')
        self.stdout.write('  指导老师2：teacher2@demo.com / teacher123456')
        self.stdout.write('  敏感审批：approver@demo.com / approver123456')
        self.stdout.write('  六个核心负责人：leader1~leader6@demo.com / leader123456')
        self.stdout.write('  普通协作成员：member1~member8@demo.com / member123456')
        self.stdout.write('数据覆盖：6 项目（001 已获奖阶段）、22 条参赛记录、小挑/大挑全覆盖、数字中国 2 组、项目历程、人员变动、方向变化、真实 Word/PDF/Excel 附件、文件版本、贡献排序、IP、敏感资料、通知、日志、导入记录。')
        self.stdout.write('v1.3 新增：4 个定时报表计划、Excel/Word/PDF 执行历史、实时通知演示、3 条集成配置、全部演示账号的账户级主题偏好，以及可下载的 PDF/Excel/Word 演示附件。')
        self.stdout.write(self.style.WARNING('下一步：重新跑 python manage.py check、登录前端，用 Dashboard/项目/比赛/经费/移动端截图验收。'))
