"""
统一响应工具
所有成功响应格式: {"code": 0, "message": "success", "data": ...}
所有错误响应格式: {"code": 非0, "message": "...", "data": null}
"""
from rest_framework.response import Response
from rest_framework import status as http_status


def success_response(data=None, message='success', http_status=http_status.HTTP_200_OK):
    """
    成功响应
    :param data: 响应数据
    :param message: 提示消息
    :param http_status: HTTP 状态码
    :return: Response {"code": 0, "message": "success", "data": ...}
    """
    return Response(
        {
            'code': 0,
            'message': message,
            'data': data,
        },
        status=http_status,
    )


def error_response(message='error', code=1, data=None, http_status=http_status.HTTP_400_BAD_REQUEST):
    """
    错误响应
    :param message: 错误消息
    :param code: 业务错误码（非0）
    :param data: 附加数据（通常为 None）
    :param http_status: HTTP 状态码
    :return: Response {"code": 非0, "message": "...", "data": null}
    """
    return Response(
        {
            'code': code,
            'message': message,
            'data': data,
        },
        status=http_status,
    )


def created_response(data=None, message='创建成功'):
    """创建成功响应（HTTP 201）"""
    return success_response(data, message, http_status.HTTP_201_CREATED)


def no_content_response(message='删除成功'):
    """无内容响应（HTTP 204）"""
    return success_response(None, message, http_status.HTTP_204_NO_CONTENT)
