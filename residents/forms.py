from django import forms
from .models import Resident


class ResidentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sex'].choices = [
            ('', 'Select Sex'),
            *Resident.GENDER_CHOICES,
        ]

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
            'first_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'middle_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'last_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'sex': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'birth_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),

            'address': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter Zone (e.g. Zone 1)'
                }
            ),
            'contact_number': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'guardian_name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),

        }