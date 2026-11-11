from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.admin_dashboard,
        name='admin_dashboard'
    ),
    path(
        'residents-without-assessment/',
        views.unassessed_residents,
        name='unassessed_residents',
    ),
    path(
        'archived-records/',
        views.archived_records,
        name='archived_records'
    ),

]