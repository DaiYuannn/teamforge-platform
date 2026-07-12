"""
OCR 票据识别视图
- OCRReceiptView: 上传票据图片，返回 OCR 识别结果（Stub）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import success_response, error_response
from .ocr_service import recognize_receipt, OCRError


class OCRReceiptView(APIView):
    """
    OCR 票据识别视图
    POST /api/v1/finance/ocr/recognize/
    - 上传票据图片，返回结构化识别结果（当前为 Stub）
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        upload_file = request.FILES.get('image') or request.FILES.get('file')
        if not upload_file:
            return error_response(message='请上传票据图片', code=2001)

        try:
            result = recognize_receipt(upload_file)
        except OCRError as e:
            return error_response(message=e.message, code=e.code)

        return success_response(result, message='OCR 识别完成')
