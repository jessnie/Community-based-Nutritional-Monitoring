from django.urls import path
from . import views


urlpatterns = [
    # Nutrition Assessment
    path(
        '',
        views.assessment_list,
        name='assessment_list'
    ),

    path(
        'add/',
        views.add_assessment,
        name='add_assessment'
    ),

    path(
        'edit/<int:pk>/',
        views.edit_assessment,
        name='edit_assessment'
    ),

    path(
        'delete/<int:pk>/',
        views.delete_assessment,
        name='delete_assessment'
    ),

    # Follow-Up Monitoring
    path(
        'follow-ups/',
        views.followup_list,
        name='followup_list'
    ),

    path(
        'follow-ups/add/',
        views.add_followup,
        name='add_followup'
    ),

    path(
        'follow-ups/edit/<int:pk>/',
        views.edit_followup,
        name='edit_followup'
    ),

    path(
        'follow-ups/delete/<int:pk>/',
        views.delete_followup,
        name='delete_followup'
    ),
]