from django import forms
from .models import Resident


class ResidentForm(forms.ModelForm):

    class Meta:

        model = Resident

        fields = [

            'first_name',
            'middle_name',
            'last_name',
            'sex',
            'birth_date',
            'address',
            'contact_number',
            'guardian_name',

        ]

        labels = {

            'first_name': 'First Name',
            'middle_name': 'Middle Name',
            'last_name': 'Last Name',
            'sex': 'Sex',
            'birth_date': 'Birth Date',
            'address': 'Zone',
            'contact_number': 'Contact Number',
            'guardian_name': 'Guardian Name',

        }

        widgets = {

            'birth_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),

            'address': forms.TextInput(
                attrs={
                    'placeholder': 'Enter Zone (e.g. Zone 1)'
                }
            ),

        }