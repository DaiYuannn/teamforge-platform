"""
审批流程路由
- /api/v1/approvals/flows/      审批流程 CRUD
- /api/v1/approvals/requests/   审批申请 CRUD + approve/reject/cancel/my_requests
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .approval_views import ApprovalFlowViewSet, ApprovalRequestViewSet

flow_router = DefaultRouter()
flow_router.register(r'', ApprovalFlowViewSet, basename='approval-flow')

request_router = DefaultRouter()
request_router.register(r'', ApprovalRequestViewSet, basename='approval-request')

urlpatterns = [
    path('flows/', include(flow_router.urls)),
    path('requests/', include(request_router.urls)),
]
