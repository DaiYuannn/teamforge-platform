"""OCR 票据识别视图。"""
import logging

from rest_framework import status
from rest_framework.views import APIView

from common.response import success_response, error_response
from common.permissions import IsInternalTeamMember
from .ocr_service import recognize_receipt, OCRError

logger = logging.getLogger('apps.finance')


class OCRReceiptView(APIView):
    """
    OCR 票据识别视图
    POST /api/v1/finance/ocr/recognize/
    - 上传票据图片，返回结构化识别结果、置信度及 OCR 原文
    """
    permission_classes = [IsInternalTeamMember]

    def post(self, request):
        upload_file = request.FILES.get('image') or request.FILES.get('file')
        if not upload_file:
            return error_response(message='请上传票据图片', code=2001)

        try:
            result = recognize_receipt(upload_file)
        except OCRError as e:
            return error_response(
                message=e.message,
                code=e.code,
                http_status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if e.code >= 2010
                    else status.HTTP_400_BAD_REQUEST
                ),
            )
        except Exception:
            logger.exception('票据 OCR 请求发生未预期错误')
            return error_response(
                message='OCR 服务暂不可用，请稍后重试',
                code=2014,
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return success_response(result, message='OCR 识别完成')
