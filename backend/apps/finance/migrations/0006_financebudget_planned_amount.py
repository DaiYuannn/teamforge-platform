from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_finance_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='financebudget',
            name='planned_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=12,
                verbose_name='核定预算上限',
            ),
        ),
        migrations.AlterField(
            model_name='financeexpense',
            name='reimbursement_status',
            field=models.CharField(
                choices=[
                    ('draft', '草稿'),
                    ('pending', '待报销审核'),
                    ('approved', '审核通过·待打款'),
                    ('rejected', '已驳回'),
                    ('paid', '已打款·报销完成'),
                    ('not_required', '无需报销'),
                ],
                db_index=True,
                default='draft',
                max_length=20,
                verbose_name='报销状态',
            ),
        ),
    ]
