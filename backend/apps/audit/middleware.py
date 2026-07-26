"""
操作日志中间件
自动记录 POST/PUT/PATCH/DELETE 请求的操作日志
"""
import json
import logging
import re

from .models import OperationLog

logger = logging.getLogger('apps.audit')

# 敏感字段不记录到请求摘要中。这里既包含认证密钥，也包含敏感资料、
# 身份信息和财务账户字段。字段名会先做标准化，因此 camelCase、
# kebab-case 和 snake_case 都能匹配。
SENSITIVE_FIELDS = {
    'password', 'password_confirm', 'old_password', 'new_password',
    'token', 'access_token', 'refresh_token', 'secret', 'api_key',
    'encryption_key', 'private_key', 'credit_card', 'id_card',
    'plaintext', 'plain_text', 'ciphertext', 'cipher_text',
    'encrypted_content', 'identity_number', 'identity_card',
    'id_number', 'passport_number', 'social_security_number',
    'bank_card', 'bank_account', 'account_number', 'debit_card',
    'payment_account', 'phone', 'mobile', 'mobile_phone',
    'address', 'home_address', 'residential_address',
    'signature', 'electronic_signature', 'seal',
}

# 对动态字段名（例如 applicant_bank_account、oauth_access_token）使用后缀
# 匹配，避免只维护一份永远不完整的精确名称清单。
SENSITIVE_FIELD_SUFFIXES = (
    '_password', '_password_confirm',
    '_token', '_secret', '_api_key', '_private_key', '_encryption_key',
    '_plaintext', '_plain_text', '_ciphertext', '_cipher_text',
    '_encrypted_content',
    '_identity_number', '_identity_card', '_id_card', '_id_number',
    '_passport_number', '_social_security_number',
    '_credit_card', '_debit_card', '_bank_card', '_bank_account',
    '_account_number', '_payment_account',
    '_phone', '_mobile', '_mobile_phone',
    '_address', '_home_address', '_residential_address',
    '_signature', '_electronic_signature', '_seal',
)
SENSITIVE_FIELD_FRAGMENTS = (
    'password', 'access_token', 'refresh_token', 'api_key',
    'private_key', 'encryption_key',
    'plaintext', 'plain_text', 'ciphertext', 'cipher_text',
    'encrypted_content',
    'identity_number', 'identity_card', 'id_card', 'id_number',
    'passport_number', 'social_security_number',
    'credit_card', 'debit_card', 'bank_card', 'bank_account',
    'account_number', 'payment_account',
    'phone', 'home_address', 'residential_address', 'address',
    'electronic_signature', 'signature',
)

REDACTED_VALUE = '[REDACTED]'
SENSITIVE_FIELD_TERMS = (
    '密码', '口令', '令牌', '密钥', '密文', '明文',
    '身份证', '护照号', '社保号',
    '银行卡', '银行账户', '支付账户', '信用卡',
    '手机号', '电话号码', '住址', '地址', '签名', '印章',
)


def _normalize_field_name(key):
    """把字段名规范成 snake_case，供敏感字段匹配使用。"""
    value = str(key).strip()
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', value)
    value = re.sub(r'[^a-zA-Z0-9]+', '_', value)
    return value.strip('_').lower()


def is_sensitive_field(key):
    """判断任意命名风格的字段是否包含不可写入审计日志的值。"""
    raw_value = str(key).strip().lower()
    normalized = _normalize_field_name(key)
    return (
        any(term in raw_value for term in SENSITIVE_FIELD_TERMS)
        or
        normalized in SENSITIVE_FIELDS
        or any(fragment in normalized for fragment in SENSITIVE_FIELD_FRAGMENTS)
        or any(normalized.endswith(suffix) for suffix in SENSITIVE_FIELD_SUFFIXES)
    )


def redact_sensitive_data(value):
    """
    递归脱敏 JSON 兼容数据。

    保留字段结构并用固定占位符替代敏感值，既方便排障，也保证嵌套对象、
    数组中的明文不会落入 OperationLog。
    """
    if isinstance(value, dict):
        return {
            key: REDACTED_VALUE if is_sensitive_field(key) else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive_data(item) for item in value]
    return value


def redact_parameter_value(value):
    """对查询参数/表单中以字符串承载的嵌套 JSON 同样递归脱敏。"""
    if not isinstance(value, str):
        return redact_sensitive_data(value)
    stripped = value.strip()
    if not stripped or stripped[0] not in '[{':
        return value
    try:
        return redact_sensitive_data(json.loads(stripped))
    except (json.JSONDecodeError, ValueError, TypeError):
        return value


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
        # DRF 解析请求体后再次读取 request.body 可能触发
        # RawPostDataException，因此必须在进入视图前先保存脱敏摘要。
        request_summary = None
        if (
            request.method in ('POST', 'PUT', 'PATCH', 'DELETE')
            and not self._should_skip(request.path)
        ):
            request_summary = self._get_request_summary(request)

        response = self.get_response(request)
        # 只记录写操作
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            try:
                self._log_operation(request, response, request_summary=request_summary)
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
                summary[key] = (
                    REDACTED_VALUE
                    if is_sensitive_field(key)
                    else (
                        redact_parameter_value(value[0])
                        if len(value) == 1
                        else [redact_parameter_value(item) for item in value]
                    )
                )
        except Exception:
            pass

        # 请求体数据
        try:
            content_type = request.content_type or ''
            media_type = content_type.split(';', 1)[0].strip().lower()
            if media_type == 'application/json' or media_type.endswith('+json'):
                if request.body:
                    try:
                        body_data = json.loads(request.body)
                        if isinstance(body_data, dict):
                            summary.update(redact_sensitive_data(body_data))
                        else:
                            summary['_body'] = redact_sensitive_data(body_data)
                    except (json.JSONDecodeError, ValueError):
                        pass
            elif 'multipart' in media_type or 'form' in media_type:
                # 直接访问 request.POST/FILES 让 Django 的上传处理器流式解析，
                # 不读取 request.body，避免大文件被整体载入内存。
                try:
                    for key in request.POST:
                        summary[key] = (
                            REDACTED_VALUE
                            if is_sensitive_field(key)
                            else redact_parameter_value(request.POST.get(key))
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # 文件上传信息。文件名本身可能包含姓名、证件号或银行账号，因此只
        # 记录排障所需的大小和 MIME 类型，不记录文件名或内容。
        try:
            files_info = {}
            for key in request.FILES:
                file_obj = request.FILES[key]
                if is_sensitive_field(key):
                    files_info[key] = REDACTED_VALUE
                else:
                    files_info[key] = {
                        'size': file_obj.size,
                        'content_type': getattr(file_obj, 'content_type', '') or '',
                    }
            if files_info:
                summary['_files'] = files_info
        except Exception:
            pass

        return summary

    def _log_operation(self, request, response, request_summary=None):
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

        # 获取请求摘要。正常由 __call__ 在视图消费请求流前传入；保留回退逻辑
        # 便于单元测试或其他代码直接调用此方法。
        if request_summary is None:
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
