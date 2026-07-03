"""
操作日志中间件
自动记录 POST/PUT/PATCH/DELETE 请求的操作日志
"""
import json
import logging

from .models import OperationLog

logger = logging.getLogger('apps.audit')

# 敏感字段不记录到请求摘要中
SENSITIVE_FIELDS = {
    'password', 'password_confirm', 'old_password', 'new_password',
    'token', 'access_token', 'refresh_token', 'secret', 'api_key',
    'encryption_key', 'private_key', 'credit_card', 'id_card',
}

# 请求方法到操作类型的映射
METHOD_TO_OPERATION = {
    'POST': OperationLog.OperationType.CREATE,
    'PUT': OperationLog.OperationType.UPDATE,
    'PATCH': OperationLog.OperationType.UPDATE,
    'DELETE': OperationLog.OperationType.DELETE,
}


class OperationLogMiddleware:
    """
    操作日志中间件，自动记录 POST/PUT/PATCH/DELETE 请求
    - 跳过特定路径（admin、auth、audit 自身）
    - 解析模块名（从 URL 路径）
    - 记录请求摘要（过滤敏感字段）
    - 写入 OperationLog
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # 不记录日志的路径前缀
        self.skip_paths = ['/admin/', '/api/v1/auth/', '/api/v1/audit/']

    def __call__(self, request):
        response = self.get_response(request)
        # 只记录写操作
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            try:
                self._log_operation(request, response)
            except Exception as e:
                # 日志记录失败不影响正常响应
                logger.exception('记录操作日志失败: %s', e)
        return response

    def _should_skip(self, path):
        """判断是否跳过该路径"""
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
        return False

    def _parse_module(self, path):
        """
        从 URL 路径解析模块名
        示例: /api/v1/projects/1/ -> projects
              /api/v1/intellectual-property/ -> intellectual_property
        """
        # 去掉 /api/v1/ 前缀
        prefix = '/api/v1/'
        if path.startswith(prefix):
            rest = path[len(prefix):]
        else:
            rest = path.strip('/')

        # 取第一段作为模块名
        parts = rest.split('/')
        if parts and parts[0]:
            return parts[0]
        return ''

    def _parse_object_id(self, path):
        """
        从 URL 路径解析目标对象 ID（路径中最后一段数字）
        示例: /api/v1/projects/1/ -> 1
        """
        parts = [p for p in path.strip('/').split('/') if p]
        # 从后往前找第一段纯数字
        for part in reversed(parts):
            if part.isdigit():
                return part
        return ''

    def _get_client_ip(self, request):
        """获取客户端真实 IP 地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # 取第一个 IP（最原始的客户端 IP）
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        return request.META.get('REMOTE_ADDR')

    def _get_request_summary(self, request):
        """
        获取请求摘要（过滤敏感字段）
        合并 query_params 和 body 数据
        """
        summary = {}

        # GET 查询参数
        try:
            query_dict = dict(request.GET)
            for key, value in query_dict.items():
                if key.lower() not in SENSITIVE_FIELDS:
                    summary[key] = value[0] if len(value) == 1 else value
        except Exception:
            pass

        # 请求体数据
        try:
            if request.body:
                content_type = request.content_type or ''
                if 'application/json' in content_type:
                    try:
                        body_data = json.loads(request.body)
                        if isinstance(body_data, dict):
                            for key, value in body_data.items():
                                if key.lower() not in SENSITIVE_FIELDS:
                                    summary[key] = value
                        else:
                            summary['_body'] = body_data
                    except (json.JSONDecodeError, ValueError):
                        pass
                elif 'multipart' in content_type or 'form' in content_type:
                    # 表单数据
                    try:
                        for key in request.POST:
                            if key.lower() not in SENSITIVE_FIELDS:
                                summary[key] = request.POST.get(key)
                    except Exception:
                        pass
        except Exception:
            pass

        # 文件上传信息（只记录文件名和大小，不记录内容）
        try:
            files_info = {}
            for key in request.FILES:
                file_obj = request.FILES[key]
                files_info[key] = {
                    'name': file_obj.name,
                    'size': file_obj.size,
                }
            if files_info:
                summary['_files'] = files_info
        except Exception:
            pass

        return summary

    def _log_operation(self, request, response):
        """记录操作日志"""
        path = request.path

        # 跳过特定路径
        if self._should_skip(path):
            return

        # 获取已认证用户
        user = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user

        # 解析模块名
        module = self._parse_module(path)

        # 解析目标对象 ID
        object_id = self._parse_object_id(path)

        # 根据路径推断目标对象类型（首字母大写）
        object_type = module.replace('_', ' ').title() if module else ''

        # 获取操作类型
        operation_type = METHOD_TO_OPERATION.get(
            request.method, OperationLog.OperationType.OTHER
        )

        # 特殊路径推断操作类型
        path_lower = path.lower()
        if 'login' in path_lower:
            operation_type = OperationLog.OperationType.LOGIN
        elif 'logout' in path_lower:
            operation_type = OperationLog.OperationType.LOGOUT
        elif 'export' in path_lower or 'download' in path_lower:
            operation_type = OperationLog.OperationType.DOWNLOAD
        elif 'import' in path_lower or 'upload' in path_lower:
            operation_type = OperationLog.OperationType.UPLOAD
        elif 'approve' in path_lower:
            operation_type = OperationLog.OperationType.APPROVE
        elif 'reject' in path_lower:
            operation_type = OperationLog.OperationType.REJECT
        elif 'review' in path_lower:
            operation_type = OperationLog.OperationType.REVIEW

        # 获取 IP 地址
        ip = self._get_client_ip(request)

        # 获取 User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        # 获取请求摘要
        request_summary = self._get_request_summary(request)

        # 响应状态码
        response_status = getattr(response, 'status_code', None)

        # 是否成功（2xx 为成功）
        is_success = True
        error_message = ''
        if response_status is not None:
            is_success = 200 <= response_status < 300
            if not is_success:
                # 尝试从响应中提取错误信息
                try:
                    if hasattr(response, 'data') and isinstance(response.data, dict):
                        error_message = str(response.data.get('message', ''))[:500]
                except Exception:
                    pass

        # 构建操作描述
        description = f'{request.method} {path}'

        # 写入 OperationLog
        OperationLog.objects.create(
            operator=user,
            operation_type=operation_type,
            module=module,
            object_type=object_type,
            object_id=object_id,
            description=description,
            request_method=request.method,
            request_path=path,
            request_ip=ip,
            user_agent=user_agent,
            request_data=request_summary if request_summary else None,
            response_status=response_status,
            is_success=is_success,
            error_message=error_message,
        )
