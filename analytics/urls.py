from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics'),
    path('live/', views.live_analytics_stats, name='live_analytics_stats'),
]