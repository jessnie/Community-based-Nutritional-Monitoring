from django import forms

from .models import (
    NutritionAssessment,
    FollowUpRecord,
)


class NutritionAssessmentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resident'].empty_label = 'Select Resident'

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

    def clean(self):
        cleaned_data = super().clean()
        resident = cleaned_data.get('resident')
        assessment_date = cleaned_data.get('assessment_date')

        if (
            resident
            and assessment_date
            and assessment_date < resident.birth_date
        ):
            self.add_error(
                'assessment_date',
                "Assessment date cannot be before the resident's date of birth. "
                'Check the resident’s birth date or correct the assessment date.',
            )

        return cleaned_data


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
            'follow_up_method',
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

            'follow_up_method': forms.Select(
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
            'follow_up_method': 'Follow-Up Method',
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
        self.fields['assessment'].empty_label = (
            'Select Nutrition Assessment'
        )
        self.fields['follow_up_method'].choices = [
            ('', 'Select Follow-Up Method'),
            *FollowUpRecord.METHOD_CHOICES,
        ]