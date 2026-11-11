from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.activity_logs,
        name='activity_logs'
    ),
    path(
        'staff-archived-records/',
        views.staff_archived_records,
        name='staff_archived_records'
    ),

]