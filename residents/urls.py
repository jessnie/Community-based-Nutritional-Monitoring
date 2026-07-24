from django.urls import path
from . import views

urlpatterns = [
    path('', views.resident_list, name='resident_list'),
    path('add/', views.add_resident, name='add_resident'),
    path('edit/<int:pk>/', views.edit_resident, name='edit_resident'),
    path('delete/<int:pk>/', views.delete_resident, name='delete_resident'),

    path('view/<int:pk>/',views.view_resident,name='view_resident'),
]