import openpyxl
import pytest

from apps.imports.models import ImportTask
from apps.imports.services import ImportService


def make_workbook(path, headers, rows):
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    return str(path)


@pytest.mark.integration
@pytest.mark.django_db
class TestStableIdentifierImports:
    def test_task_import_resolves_project_code_and_member_email(
        self, make_user, make_project, tmp_path
    ):
        from apps.tasks.models import Task

        creator = make_user(email='task-importer@test.com', global_role='teacher')
        assignee = make_user(email='task-owner@test.com')
        project = make_project(code='STABLE-PROJECT')
        path = make_workbook(
            tmp_path / 'tasks.xlsx',
            ['任务标题', '项目编号', '指派人邮箱', '截止时间'],
            [['稳定标识任务', project.code, assignee.email, '2026-12-31 18:00:00']],
        )
        mapping = ImportService.auto_map_fields(
            ['任务标题', '项目编号', '指派人邮箱', '截止时间'], 'tasks'
        )
        task = ImportTask.objects.create(
            module='tasks',
            file_path=path,
            status=ImportTask.Status.PREVIEWED,
            field_mapping=mapping,
            created_by=creator,
        )
        success, result = ImportService.confirm_import(task)
        assert success, result
        imported = Task.objects.get(title='稳定标识任务')
        assert imported.project_id == project.id
        assert imported.assignee_id == assignee.id

    def test_finance_import_resolves_project_and_spender_email(
        self, make_user, make_project, tmp_path
    ):
        from apps.finance.models import FinanceExpense

        creator = make_user(email='finance-importer@test.com', global_role='teacher')
        spender = make_user(email='spender-stable@test.com')
        project = make_project(code='FIN-STABLE')
        headers = ['支出标题', '金额', '项目编号', '支出日期', '经办人邮箱']
        path = make_workbook(
            tmp_path / 'finance.xlsx',
            headers,
            [['打印材料', '88.50', project.code, '2026-07-01', spender.email]],
        )
        import_task = ImportTask.objects.create(
            module='finance',
            file_path=path,
            status=ImportTask.Status.PREVIEWED,
            field_mapping=ImportService.auto_map_fields(headers, 'finance'),
            created_by=creator,
        )
        success, result = ImportService.confirm_import(import_task)
        assert success, result
        expense = FinanceExpense.objects.get(title='打印材料')
        assert expense.project_id == project.id
        assert expense.spender_id == spender.id

    def test_ip_import_resolves_related_project_and_writer_email(
        self, make_user, make_project, tmp_path
    ):
        from apps.intellectual_property.models import IntellectualPropertyApplication

        creator = make_user(email='ip-importer@test.com', global_role='teacher')
        writer = make_user(email='writer-stable@test.com')
        project = make_project(code='IP-STABLE')
        headers = ['成果名称', '内部编号', '关联项目编号', '主导撰写人邮箱', '成果类型']
        path = make_workbook(
            tmp_path / 'ip.xlsx',
            headers,
            [['稳定成果', 'IP-STABLE-001', project.code, writer.email, 'software_copyright']],
        )
        import_task = ImportTask.objects.create(
            module='ip_applications',
            file_path=path,
            status=ImportTask.Status.PREVIEWED,
            field_mapping=ImportService.auto_map_fields(headers, 'ip_applications'),
            created_by=creator,
        )
        success, result = ImportService.confirm_import(import_task)
        assert success, result
        application = IntellectualPropertyApplication.objects.get(
            application_code='IP-STABLE-001'
        )
        assert application.related_project_id == project.id
        assert application.main_writer_id == writer.id

    def test_member_import_generates_unique_username_and_unusable_password(
        self, make_user, tmp_path
    ):
        from apps.users.models import User

        creator = make_user(email='member-importer@test.com', global_role='teacher')
        headers = ['姓名', '邮箱', '专业']
        path = make_workbook(
            tmp_path / 'members.xlsx',
            headers,
            [['导入成员', 'new-member@example.com', '计算机']],
        )
        import_task = ImportTask.objects.create(
            module='members',
            file_path=path,
            status=ImportTask.Status.PREVIEWED,
            field_mapping=ImportService.auto_map_fields(headers, 'members'),
            created_by=creator,
        )
        success, result = ImportService.confirm_import(import_task)
        assert success, result
        user = User.objects.get(email='new-member@example.com')
        assert user.username
        assert not user.has_usable_password()
