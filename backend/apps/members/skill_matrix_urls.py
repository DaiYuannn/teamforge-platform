"""Dedicated routes for the read-only skill matrix feature."""

from django.urls import path

from .skill_matrix_views import (
    CompetitionSkillRecommendationView,
    TeamSkillMatrixView,
)


urlpatterns = [
    path(
        'matrix/',
        TeamSkillMatrixView.as_view(),
        name='team-skill-matrix',
    ),
    path(
        'recommendations/',
        CompetitionSkillRecommendationView.as_view(),
        name='competition-skill-recommendations',
    ),
]
