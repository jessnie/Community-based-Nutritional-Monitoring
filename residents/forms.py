from django import forms
from .models import Resident


class ResidentForm(forms.ModelForm):

    class Meta:
        model = Resident

        fields = [
            'resident_id',
            'first_name',
            'middle_name',
            'last_name',
            'sex',
            'birth_date',
            'address',
            'contact_number',
            'guardian_name',
        ]

        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }