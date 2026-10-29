from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('live/', views.live_dashboard_stats, name='live_dashboard_stats'),
]