from openpyxl import Workbook
from openpyxl.styles import Font
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
)
from reportlab.lib.styles import getSampleStyleSheet

from nutrition.models import NutritionAssessment
from residents.models import Resident


def get_template(request, staff_template, admin_template):
    """
    Return the correct template depending on the logged-in user.
    """
    if request.user.is_superuser:
        return admin_template
    return staff_template


@login_required(login_url='login')
def report_dashboard(request):

    status = request.GET.get('status', '')
    resident_id = request.GET.get('resident', '')

    assessments = NutritionAssessment.objects.all().order_by(
        '-assessment_date'
    )

    # Filter by nutritional status
    if status:
        assessments = assessments.filter(
            nutritional_status=status
        )

    # Filter by resident
    if resident_id:
        assessments = assessments.filter(
            resident_id=resident_id
        )

    residents = Resident.objects.all()

    today = timezone.now()

    total_reports = NutritionAssessment.objects.count()

    monthly_reports = NutritionAssessment.objects.filter(
        assessment_date__month=today.month,
        assessment_date__year=today.year
    ).count()

    pdf_exports = 0
    excel_exports = 0

    context = {
        'assessments': assessments,
        'residents': residents,
        'status': status,
        'resident_id': resident_id,
        'total_reports': total_reports,
        'monthly_reports': monthly_reports,
        'pdf_exports': pdf_exports,
        'excel_exports': excel_exports,
    }

    return render(
        request,
        get_template(
            request,
            'reports/report_dashboard.html',
            'admin_reports/report_dashboard.html'
        ),
        context
    )


@login_required(login_url='login')
def monthly_report(request):

    today = timezone.now()

    assessments = NutritionAssessment.objects.filter(
        assessment_date__month=today.month,
        assessment_date__year=today.year
    ).select_related(
        'resident'
    ).order_by(
        '-assessment_date'
    )

    context = {
        'assessments': assessments,
        'current_month': today.strftime("%B %Y"),
    }

    return render(
        request,
        'admin_reports/monthly_report.html',
        context
    )


@login_required(login_url='login')
def annual_report(request):

    today = timezone.now()

    assessments = NutritionAssessment.objects.filter(
        assessment_date__year=today.year
    ).select_related(
        'resident'
    ).order_by(
        '-assessment_date'
    )

    context = {
        'assessments': assessments,
        'current_year': today.year,
    }

    return render(
        request,
        'admin_reports/annual_report.html',
        context
    )


@login_required(login_url='login')
def export_pdf(request):

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="Nutrition_Report.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "<b>Community-Based Nutritional Monitoring and Decision Support System</b>",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            "Nutrition Assessment Report",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            f"Generated on: {timezone.now().strftime('%B %d, %Y %I:%M %p')}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph("<br/>", styles["Normal"])
    )

    assessments = NutritionAssessment.objects.select_related(
        'resident'
    ).order_by(
        '-assessment_date'
    )

    data = [[
        "Date",
        "Resident",
        "Age",
        "Sex",
        "Height",
        "Weight",
        "BMI",
        "Status",
        "Remarks"
    ]]

    for assessment in assessments:

        data.append([

            str(assessment.assessment_date),

            f"{assessment.resident.first_name} {assessment.resident.last_name}",

            str(assessment.resident.age),

            assessment.resident.sex,

            f"{assessment.height} cm",

            f"{assessment.weight} kg",

            str(assessment.bmi),

            assessment.nutritional_status,

            assessment.remarks or ""

        ])

    table = Table(data)

    table.setStyle(

        TableStyle([

            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

            ('GRID', (0, 0), (-1, -1), 1, colors.black),

            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),

            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

        ])

    )

    elements.append(table)

    doc.build(elements)

    return response


@login_required(login_url='login')
def export_excel(request):

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response[
        'Content-Disposition'
    ] = 'attachment; filename="Nutrition_Report.xlsx"'

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Nutrition Report"

    worksheet['A1'] = "Community-Based Nutritional Monitoring and Decision Support System"
    worksheet['A2'] = "Nutrition Assessment Report"
    worksheet['A3'] = f"Generated: {timezone.now().strftime('%B %d, %Y %I:%M %p')}"

    headers = [
        "Date",
        "Resident",
        "Age",
        "Sex",
        "Height (cm)",
        "Weight (kg)",
        "BMI",
        "Nutritional Status",
        "Remarks",
    ]

    row = 5

    for col_num, header in enumerate(headers, 1):

        cell = worksheet.cell(
            row=row,
            column=col_num
        )

        cell.value = header
        cell.font = Font(bold=True)

    assessments = NutritionAssessment.objects.select_related(
        'resident'
    ).order_by(
        '-assessment_date'
    )

    row = 6

    for assessment in assessments:

        worksheet.cell(
            row=row,
            column=1
        ).value = str(assessment.assessment_date)

        worksheet.cell(
            row=row,
            column=2
        ).value = f"{assessment.resident.first_name} {assessment.resident.last_name}"

        worksheet.cell(
            row=row,
            column=3
        ).value = assessment.resident.age

        worksheet.cell(
            row=row,
            column=4
        ).value = assessment.resident.sex

        worksheet.cell(
            row=row,
            column=5
        ).value = float(assessment.height)

        worksheet.cell(
            row=row,
            column=6
        ).value = float(assessment.weight)

        worksheet.cell(
            row=row,
            column=7
        ).value = float(assessment.bmi)

        worksheet.cell(
            row=row,
            column=8
        ).value = assessment.nutritional_status

        worksheet.cell(
            row=row,
            column=9
        ).value = assessment.remarks

        row += 1

    # Adjust column widths
    column_widths = {
        'A': 15,
        'B': 28,
        'C': 8,
        'D': 12,
        'E': 15,
        'F': 15,
        'G': 10,
        'H': 20,
        'I': 45,
    }

    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    workbook.save(response)

    return response