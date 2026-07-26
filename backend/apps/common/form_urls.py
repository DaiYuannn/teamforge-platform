"""
自定义表单路由
- /api/v1/common/forms/             表单 CRUD
- /api/v1/common/form-submissions/  提交记录 CRUD + my_submissions
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .form_views import CustomFormViewSet, FormSubmissionViewSet
from .media_views import ProtectedMediaView

form_router = DefaultRouter()
form_router.register(r'', CustomFormViewSet, basename='custom-form')

submission_router = DefaultRouter()
submission_router.register(r'', FormSubmissionViewSet, basename='form-submission')

urlpatterns = [
    path('media/', ProtectedMediaView.as_view(), name='protected-media'),
    path('forms/', include(form_router.urls)),
    path('form-submissions/', include(submission_router.urls)),
]
