from django.urls import path
from . import views

urlpatterns = [
    path('', views.resident_list, name='admin_resident_list'),
]