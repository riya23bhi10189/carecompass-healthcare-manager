from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Appointment, DoctorProfile


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["doctor", "start_at", "symptoms"]

        widgets = {
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M"
            ),

            "symptoms": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Example: Fever for two days, sore throat, fatigue..."
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["doctor"].queryset = DoctorProfile.objects.select_related(
            "user"
        ).order_by("specialization")

class RescheduleForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["doctor", "start_at"]

        widgets = {
            "start_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["doctor"].queryset = DoctorProfile.objects.select_related(
            "user"
        ).order_by("specialization")