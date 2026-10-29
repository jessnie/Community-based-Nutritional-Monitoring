from django import forms
from django.contrib.auth.models import User


class UserForm(forms.ModelForm):

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control"
            }
        )
    )

    class Meta:

        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "is_active",
        ]

        widgets = {

            "username": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control"
                }
            ),

        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        self._existing_password = (
            instance.password
            if instance is not None and instance.pk
            else None
        )
        super().__init__(*args, **kwargs)

    def save(self, commit=True):

        user = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:

            user.set_password(password)
        elif self._existing_password is not None:

            user.password = self._existing_password

        if commit:

            user.save()

        return user