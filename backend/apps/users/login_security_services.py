"""
登录安全服务
- 记录登录尝试
- 检测 IP 是否被封禁
- 连续失败自动封禁（5 次/30 分钟 -> 封禁 1 小时）
"""
from datetime import timedelta

from django.utils import timezone

from .login_security_models import LoginAttempt, IPBlocklist

# 封禁策略
FAILED_THRESHOLD = 5  # 失败阈值
FAILED_WINDOW_MINUTES = 30  # 统计窗口（分钟）
BLOCK_DURATION_HOURS = 1  # 封禁时长（小时）


def get_client_ip(request):
    """获取客户端真实 IP（兼容反向代理）"""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or None


def get_user_agent(request):
    """获取 User-Agent"""
    return request.META.get('HTTP_USER_AGENT', '') or ''


def is_ip_blocked(ip_address):
    """判断 IP 是否处于封禁状态"""
    if not ip_address:
        return False
    try:
        block = IPBlocklist.objects.get(ip_address=ip_address)
    except IPBlocklist.DoesNotExist:
        return False
    # 无截止时间视为永久封禁
    if block.blocked_until is None:
        return True
    # 已过期则视为未封禁
    if block.blocked_until <= timezone.now():
        return False
    return True


def record_login_attempt(email, ip_address, user_agent, is_success, failure_reason=''):
    """记录一次登录尝试，并在达到阈值时自动封禁 IP"""
    LoginAttempt.objects.create(
        email=email,
        ip_address=ip_address,
        user_agent=user_agent or '',
        is_success=is_success,
        failure_reason=failure_reason or '',
    )
    # 成功登录不触发封禁逻辑
    if is_success or not ip_address:
        return None

    # 统计最近窗口内的失败次数
    window_start = timezone.now() - timedelta(minutes=FAILED_WINDOW_MINUTES)
    recent_failures = LoginAttempt.objects.filter(
        ip_address=ip_address,
        is_success=False,
        created_at__gte=window_start,
    ).count()

    if recent_failures >= FAILED_THRESHOLD:
        block_until = timezone.now() + timedelta(hours=BLOCK_DURATION_HOURS)
        block, created = IPBlocklist.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'reason': f'连续登录失败 {recent_failures} 次',
                'blocked_until': block_until,
            },
        )
        return block
    return None
