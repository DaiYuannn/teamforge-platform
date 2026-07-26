"""灵活工时半月周期的统一日期规则。"""
import calendar


def get_half_month_period(target_date):
    """返回闭区间周期：每月 1-15 日、16 日-月末。"""
    if target_date.day <= 15:
        return target_date.replace(day=1), target_date.replace(day=15)
    last_day = calendar.monthrange(target_date.year, target_date.month)[1]
    return target_date.replace(day=16), target_date.replace(day=last_day)
