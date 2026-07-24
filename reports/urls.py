from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.report_dashboard,
        name='report_dashboard'
    ),

    path(
        'monthly/',
        views.monthly_report,
        name='monthly_report'
    ),

    path(
        'annual/',
        views.annual_report,
        name='annual_report'
    ),

    path(
        'export/pdf/',
        views.export_pdf,
        name='export_pdf'
    ),

    path(
        'export/excel/',
        views.export_excel,
        name='export_excel'
    ),

]