"""国际化（i18n）与主题路由（N62）"""
from django.urls import path

from .i18n_views import TranslationView, ThemeView

urlpatterns = [
    path('translations/', TranslationView.as_view(), name='translations'),
    path('themes/', ThemeView.as_view(), name='themes'),
]
