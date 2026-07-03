"""
自定义异常处理器
统一所有异常的响应格式为 {"code": 非0, "message": "...", "data": null}
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    ValidationError,
    Throttled,
)
from rest_framework import status
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    自定义异常处理器
    将所有异常统一转换为 {"code": 非0, "message": "...", "data": null} 格式
    """
    # 先调用 DRF 默认异常处理器
    response = exception_handler(exc, context)

    # 处理 Django 原生异常
    if isinstance(exc, Http404):
        return _build_error_response('资源不存在', 1004, status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DjangoPermissionDenied):
        return _build_error_response('权限不足', 1003, status.HTTP_403_FORBIDDEN)

    if response is not None:
        # 根据异常类型设置不同的 message 和 code
        if isinstance(exc, NotAuthenticated):
            message = '请先登录'
            code = 1001
        elif isinstance(exc, AuthenticationFailed):
            message = '认证失败，请重新登录'
            code = 1001
        elif isinstance(exc, PermissionDenied):
            message = '权限不足'
            code = 1003
        elif isinstance(exc, NotFound):
            message = '资源不存在'
            code = 1004
        elif isinstance(exc, ValidationError):
            # 表单验证错误，提取详细错误信息
            message = '参数验证失败'
            code = 1005
            # 尝试提取具体字段错误
            if isinstance(response.data, dict):
                error_details = []
                for field, errors in response.data.items():
                    if isinstance(errors, list):
                        error_details.append(f'{field}: {", ".join(errors)}')
                    else:
                        error_details.append(f'{field}: {errors}')
                message = '; '.join(error_details) if error_details else message
        elif isinstance(exc, Throttled):
            message = f'请求过于频繁，请 {exc.wait} 秒后重试'
            code = 1006
        else:
            # 其他 DRF 异常
            message = str(response.data) if response.data else '请求错误'
            code = response.status_code

        # 统一响应格式
        response.data = {
            'code': code,
            'message': message,
            'data': None,
        }
        # 保持原始 HTTP 状态码
        # response.status_code 保持不变

    return response


def _build_error_response(message, code, http_status):
    """构建错误响应"""
    from rest_framework.response import Response
    return Response(
        {'code': code, 'message': message, 'data': None},
        status=http_status,
    )
