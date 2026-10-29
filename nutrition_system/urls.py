from django.urls import path, include
from django.shortcuts import redirect


def home(request):
    return redirect('login')


urlpatterns = [
    path('', home, name='home'),

    path('', include('accounts.urls')),

    path('dashboard/', include('dashboard.urls')),

    path('residents/', include('residents.urls')),

    path('nutrition/', include('nutrition.urls')),

    path('analytics/', include('analytics.urls')),

    path('admin-dashboard/', include('admin_dashboard.urls')),

    path('reports/', include('reports.urls')),

    path("users/",include("user_management.urls")),

    path('activity-logs/',include('activity_logs.urls')),
]