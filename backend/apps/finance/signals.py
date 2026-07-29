"""保持预算汇总与收入/支出流水同步。"""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import FinanceExpense, FinanceIncome, FinancePayment
from .services import recalculate_project_budget, sync_expense_payment_status


def _remember_previous_project(instance, model):
    if not instance.pk:
        instance._previous_project_id = None
        return
    instance._previous_project_id = (
        model.all_objects.filter(pk=instance.pk)
        .values_list('project_id', flat=True)
        .first()
        if hasattr(model, 'all_objects')
        else model.objects.filter(pk=instance.pk)
        .values_list('project_id', flat=True)
        .first()
    )


@receiver(pre_save, sender=FinanceExpense)
def remember_expense_project(sender, instance, **kwargs):
    _remember_previous_project(instance, FinanceExpense)


@receiver(post_save, sender=FinanceExpense)
def sync_budget_after_expense_save(sender, instance, **kwargs):
    recalculate_project_budget(instance.project_id)
    if (
        getattr(instance, '_previous_project_id', None)
        and instance._previous_project_id != instance.project_id
    ):
        recalculate_project_budget(instance._previous_project_id)


@receiver(post_delete, sender=FinanceExpense)
def sync_budget_after_expense_delete(sender, instance, **kwargs):
    recalculate_project_budget(instance.project_id)


@receiver(post_save, sender=FinanceIncome)
def sync_budget_after_income_save(sender, instance, **kwargs):
    recalculate_project_budget(instance.project_id)
    if (
        getattr(instance, '_previous_project_id', None)
        and instance._previous_project_id != instance.project_id
    ):
        recalculate_project_budget(instance._previous_project_id)


@receiver(post_delete, sender=FinanceIncome)
def sync_budget_after_income_delete(sender, instance, **kwargs):
    recalculate_project_budget(instance.project_id)


@receiver(pre_save, sender=FinanceIncome)
def remember_income_project(sender, instance, **kwargs):
    _remember_previous_project(instance, FinanceIncome)


@receiver(post_save, sender=FinancePayment)
def sync_expense_after_payment_save(sender, instance, **kwargs):
    sync_expense_payment_status(instance.expense_id)


@receiver(post_delete, sender=FinancePayment)
def sync_expense_after_payment_delete(sender, instance, **kwargs):
    sync_expense_payment_status(instance.expense_id)
