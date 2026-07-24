from django.urls import path
from . import views

urlpatterns = [

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

]