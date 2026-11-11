from django.urls import path
from . import views


urlpatterns = [
    path(
        'settings/',
        views.account_settings,
        name='account_settings',
    ),

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),

]