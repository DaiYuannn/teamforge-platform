"""受保护媒体文件的限时签名访问入口。"""

from django.core import signing
from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.storage import load_protected_media_token, protected_media_response


class ProtectedMediaView(APIView):
    """
    通过签名 URL 读取非公开媒体。

    签名 URL 只会在已通过各业务接口权限检查的序列化响应中生成；访问时再
    校验签名和有效期。这样 img 等原生浏览器请求无需暴露 JWT，也不能通过
    猜测 /media/ 路径绕过权限。
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        if not token:
            raise Http404('媒体文件不存在')

        try:
            media_name = load_protected_media_token(token)
        except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
            raise Http404('媒体文件不存在')

        as_attachment = request.query_params.get('download') in {'1', 'true', 'yes'}
        return protected_media_response(media_name, as_attachment=as_attachment)
