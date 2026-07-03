"""
分页配置
统一使用 PageNumberPagination
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    标准分页器
    - 默认每页 20 条
    - 支持前端通过 page_size 参数自定义每页条数
    - 最大每页 100 条
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        自定义分页响应格式，保持与统一响应格式一致
        返回: {"code": 0, "message": "success", "data": {"count": N, "next": url, "previous": url, "results": [...]}}
        """
        from rest_framework.response import Response
        return Response({
            'code': 0,
            'message': 'success',
            'data': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size,
                'results': data,
            }
        })
