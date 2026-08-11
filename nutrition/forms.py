from django import forms

from .models import (
    NutritionAssessment,
    FollowUpRecord,
)


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
            'resident': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'assessment_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),

            'height': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': 'Height in centimeters',
                    'class': 'form-control'
                }
            ),

            'weight': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': 'Weight in kilograms',
                    'class': 'form-control'
                }
            ),
        }

        labels = {
            'resident': 'Resident',
            'assessment_date': 'Assessment Date',
            'height': 'Height (cm)',
            'weight': 'Weight (kg)',
        }


class AssessmentChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):

        return (
            f"{obj.resident.resident_id} - "
            f"{obj.resident.first_name} "
            f"{obj.resident.last_name} | "
            f"{obj.assessment_date} | "
            f"BMI: {obj.bmi} | "
            f"{obj.nutritional_status}"
        )


class FollowUpRecordForm(forms.ModelForm):

    assessment = AssessmentChoiceField(
        queryset=NutritionAssessment.objects.none(),
        label='Nutrition Assessment',
        widget=forms.Select(
            attrs={
                'class': 'form-select'
            }
        )
    )

    class Meta:

        model = FollowUpRecord

        fields = [
            'assessment',
            'follow_up_date',
            'status',
            'notes',
            'next_follow_up_date',
        ]

        widgets = {

            'follow_up_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),

            'status': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': (
                        'Enter observations, actions taken, '
                        'or other follow-up notes.'
                    )
                }
            ),

            'next_follow_up_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
        }

        labels = {
            'assessment': 'Nutrition Assessment',
            'follow_up_date': 'Follow-Up Date',
            'status': 'Follow-Up Status',
            'notes': 'Notes',
            'next_follow_up_date': 'Next Follow-Up Date',
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['assessment'].queryset = (
            NutritionAssessment.objects
            .select_related('resident')
            .order_by(
                '-assessment_date',
                '-created_at'
            )
        )