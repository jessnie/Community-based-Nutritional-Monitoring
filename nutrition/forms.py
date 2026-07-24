from django import forms
from .models import NutritionAssessment


class NutritionAssessmentForm(forms.ModelForm):

    class Meta:
        model = NutritionAssessment

        fields = [
            'resident',
            'assessment_date',
            'height',
            'weight',
        ]

        widgets = {
            'assessment_date': forms.DateInput(
                attrs={
                    'type': 'date'
                }
            ),
            'height': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': 'Height in centimeters'
                }
            ),
            'weight': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': 'Weight in kilograms'
                }
            ),
        }

        labels = {
            'resident': 'Resident',
            'assessment_date': 'Assessment Date',
            'height': 'Height (cm)',
            'weight': 'Weight (kg)',
        }