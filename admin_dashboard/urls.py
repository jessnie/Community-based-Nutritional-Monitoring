from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'archived-records/',
        views.archived_records,
        name='archived_records'
    ),

]