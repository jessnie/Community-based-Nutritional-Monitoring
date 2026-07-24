from django.contrib import admin
from .models import Resident


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = (
        'resident_id',
        'first_name',
        'last_name',
        'sex',
        'birth_date',
        'age',
    )

    search_fields = (
        'resident_id',
        'first_name',
        'last_name',
    )

    list_filter = (
        'sex',
    )

    ordering = (
        'last_name',
        'first_name',
    )
