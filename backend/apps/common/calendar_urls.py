"""日历同步路由"""
from django.urls import path

from .calendar_views import CalendarFeedView

urlpatterns = [
    path('', CalendarFeedView.as_view(), name='calendar-feed'),
]
