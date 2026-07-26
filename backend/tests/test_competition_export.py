import io

import openpyxl
import pytest

from apps.competitions.models import Competition


@pytest.mark.api
@pytest.mark.django_db
class TestCompetitionExport:
    def test_excel_uses_current_filters_and_includes_full_workflow(
        self, member_client, make_project,
    ):
        matching_project = make_project(name='智慧农业项目', code='COMP-EXPORT-01')
        other_project = make_project(name='数字治理项目', code='COMP-EXPORT-02')
        Competition.objects.create(
            project=matching_project,
            name='挑战杯目标赛事',
            comp_type='创新创业',
            level='province',
            status='ongoing',
            organizer='省竞赛组委会',
            current_stage='省赛',
            register_date='2026-01-02',
            material_deadline='2026-01-20',
            review_date='2026-02-02',
            defense_date='2026-02-15',
            school_date='2026-02-20',
            city_date='2026-03-01',
            province_date='2026-03-20',
            is_promoted=True,
            is_awarded=False,
            review_summary='重点复盘内容',
            improvement_suggestion='补充真实用户数据',
        )
        Competition.objects.create(
            project=other_project,
            name='挑战杯不应导出赛事',
            level='national',
            status='completed',
        )

        response = member_client.get('/api/v1/exports/', {
            'type': 'competitions',
            'file_format': 'xlsx',
            'search': '挑战杯',
            'project_id': matching_project.id,
            'level': 'province',
            'status': 'ongoing',
        })

        assert response.status_code == 200
        workbook = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
        worksheet = workbook['比赛列表']
        headers = [cell.value for cell in worksheet[1]]
        rows = list(worksheet.iter_rows(min_row=2, values_only=True))

        assert len(rows) == 1
        exported = dict(zip(headers, rows[0]))
        assert exported['所属项目'] == '智慧农业项目'
        assert exported['项目编号'] == 'COMP-EXPORT-01'
        assert exported['比赛名称'] == '挑战杯目标赛事'
        assert exported['材料提交截止'] == '2026-01-20'
        assert exported['网评日期'] == '2026-02-02'
        assert exported['省赛日期'] == '2026-03-20'
        assert exported['评审/答辩复盘'] == '重点复盘内容'
        assert exported['改进建议'] == '补充真实用户数据'
