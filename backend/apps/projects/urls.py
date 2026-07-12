"""
项目路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, ProjectMemberViewSet
from .review_views import ProjectReviewViewSet
from .milestone_views import MilestoneViewSet
from .risk_views import ProjectRiskViewSet
from .template_views import ProjectTemplateViewSet
from .discussion_views import DiscussionTopicViewSet
from .knowledge_views import KnowledgeArticleViewSet
# N51-N55: 智能分析视图
from .risk_prediction_views import RiskPredictionView
from .health_score_views import ProjectHealthScoreView
from .smart_review_views import SmartReviewView
from .material_check_views import MaterialCheckView

# 创建路由器并注册 ViewSet
# 注意：带前缀的路由（members/reviews/milestones/risks/templates/discussions/knowledge）必须先注册，
# 否则空前缀 ProjectViewSet 的详情路由 (?P<pk>[^/.]+)/ 会先匹配到它们
router = DefaultRouter()
router.register(r'members', ProjectMemberViewSet, basename='project-member')
router.register(r'reviews', ProjectReviewViewSet, basename='project-review')
router.register(r'milestones', MilestoneViewSet, basename='milestone')
router.register(r'risks', ProjectRiskViewSet, basename='project-risk')
router.register(r'templates', ProjectTemplateViewSet, basename='project-template')
router.register(r'discussions', DiscussionTopicViewSet, basename='discussion')
router.register(r'knowledge', KnowledgeArticleViewSet, basename='knowledge-article')
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    # ============ N51-N55: 智能分析视图（需在 router include 之前，避免被空前缀详情路由匹配）============
    # N51: 风险预测
    path('risk-prediction/', RiskPredictionView.as_view(), name='risk-prediction'),
    # N52: 健康度评分
    path('health-score/', ProjectHealthScoreView.as_view(), name='health-score'),
    # N54: 智能复盘
    path('smart-review/', SmartReviewView.as_view(), name='smart-review'),
    # N55: 材料检查
    path('material-check/', MaterialCheckView.as_view(), name='material-check'),
    # ============ 资源 ViewSet ============
    path('', include(router.urls)),
]
