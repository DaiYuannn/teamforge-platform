"""
敏感操作确认路由
- POST /api/v1/common/confirmations/generate/
- POST /api/v1/common/confirmations/verify/
"""
from django.urls import path

from .confirmation_views import (
    SensitiveConfirmationGenerateView, SensitiveConfirmationVerifyView,
)

urlpatterns = [
    path('generate/', SensitiveConfirmationGenerateView.as_view(), name='confirmation-generate'),
    path('verify/', SensitiveConfirmationVerifyView.as_view(), name='confirmation-verify'),
]
