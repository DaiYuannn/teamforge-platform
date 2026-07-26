from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_finance(apps, schema_editor):
    FinanceBudget = apps.get_model('finance', 'FinanceBudget')
    FinanceExpense = apps.get_model('finance', 'FinanceExpense')
    FinanceIncome = apps.get_model('finance', 'FinanceIncome')

    # 迁移前的支出都是既成台账，按已付款处理，避免升级后已用金额归零。
    for expense in FinanceExpense.objects.all().iterator():
        expense.reimbursement_status = 'paid'
        expense.applied_by_id = expense.spender_id
        expense.applied_at = expense.created_at
        expense.reviewed_at = expense.updated_at
        expense.paid_by_id = expense.reviewer_id or expense.spender_id
        expense.paid_at = expense.updated_at
        expense.payment_method = '历史台账迁移'
        expense.review_opinion = '系统升级前已登记的支出，按已完成台账迁移'
        expense.save(
            update_fields=[
                'reimbursement_status', 'applied_by', 'applied_at',
                'reviewed_at', 'paid_by', 'paid_at',
                'payment_method', 'review_opinion',
            ]
        )

    # 将预算中的汇总收入转换为可追溯的初始化流水。
    for budget in FinanceBudget.objects.all().iterator():
        income_date = budget.updated_at.date()
        if budget.bonus_amount:
            FinanceIncome.objects.create(
                project_id=budget.project_id,
                title='历史奖金收入初始化',
                amount=budget.bonus_amount,
                income_type='bonus',
                income_date=income_date,
                source='系统升级迁移',
                note='由原预算奖金汇总自动生成',
            )
        if budget.other_income:
            FinanceIncome.objects.create(
                project_id=budget.project_id,
                title='历史其他收入初始化',
                amount=budget.other_income,
                income_type='other',
                income_date=income_date,
                source='系统升级迁移',
                note='由原预算其他收入汇总自动生成',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_add_soft_delete'),
        ('projects', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FinanceIncome',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='收入标题')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='收入金额')),
                ('income_type', models.CharField(choices=[('bonus', '比赛奖金'), ('grant', '项目拨款'), ('sponsorship', '赞助收入'), ('refund', '退款入账'), ('other', '其他收入')], default='other', max_length=20, verbose_name='收入类型')),
                ('income_date', models.DateField(verbose_name='收入日期')),
                ('source', models.CharField(blank=True, default='', max_length=200, verbose_name='收入来源')),
                ('reference_number', models.CharField(blank=True, default='', max_length=100, verbose_name='入账凭证号')),
                ('note', models.TextField(blank=True, default='', verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_incomes', to='projects.project', verbose_name='所属项目')),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_finance_incomes', to=settings.AUTH_USER_MODEL, verbose_name='登记人')),
            ],
            options={
                'verbose_name': '收入流水',
                'verbose_name_plural': '收入流水',
                'db_table': 'finance_incomes',
                'ordering': ['-income_date', '-created_at'],
            },
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='applied_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='报销申请时间'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='applied_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_reimbursements', to=settings.AUTH_USER_MODEL, verbose_name='报销申请人'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='付款时间'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='paid_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paid_reimbursements', to=settings.AUTH_USER_MODEL, verbose_name='付款登记人'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='payment_method',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='付款方式'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='payment_reference',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='付款流水号'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='reimbursement_status',
            field=models.CharField(choices=[('draft', '草稿'), ('pending', '待审核'), ('approved', '已审核'), ('rejected', '已驳回'), ('paid', '已付款'), ('not_required', '无需报销')], db_index=True, default='draft', max_length=20, verbose_name='报销状态'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='review_opinion',
            field=models.TextField(blank=True, default='', verbose_name='报销审核意见'),
        ),
        migrations.AddField(
            model_name='financeexpense',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='报销审核时间'),
        ),
        migrations.RunPython(migrate_legacy_finance, migrations.RunPython.noop),
    ]
