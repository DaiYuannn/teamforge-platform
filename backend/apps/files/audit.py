"""文件下载的显式审计工具。"""

from __future__ import annotations

from ipaddress import ip_address

from apps.audit.models import OperationLog


DOWNLOAD_DESCRIPTIONS = {
    'direct': '通过受保护文件接口下载',
    'version': '通过受保护文件接口下载历史版本',
    'watermarked': '通过受保护文件接口下载水印版本',
    'share': '通过公开分享接口下载',
    'sensitive_request': '通过已批准申请下载敏感附件',
    'sensitive_audit': '通过审计入口下载敏感附件',
}


def _get_client_ip(request):
    """仅保存合法 IP，避免代理头中的非 IP 内容污染审计记录。"""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    candidate = forwarded.split(',', 1)[0].strip() if forwarded else ''
    candidate = candidate or request.META.get('REMOTE_ADDR', '')
    try:
        return str(ip_address(candidate)) if candidate else None
    except ValueError:
        return None


def record_download_audit(
    request,
    *,
    module,
    object_type,
    object_id,
    channel,
    is_success=True,
    response_status=200,
):
    """
    写入不含查询参数、分享令牌、文件名或敏感值的下载审计日志。

    `request.path` 明确不包含 query string；描述只从固定白名单选择。
    """
    user = getattr(request, 'user', None)
    operator = user if user and user.is_authenticated else None
    OperationLog.objects.create(
        operator=operator,
        operation_type=OperationLog.OperationType.DOWNLOAD,
        module=module,
        object_type=object_type,
        object_id=str(object_id or ''),
        description=DOWNLOAD_DESCRIPTIONS.get(channel, '通过受保护接口下载文件'),
        request_method='GET',
        request_path=str(getattr(request, 'path', '') or '')[:500],
        request_ip=_get_client_ip(request),
        response_status=response_status,
        is_success=is_success,
    )
