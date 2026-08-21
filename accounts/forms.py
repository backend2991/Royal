from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import AdminUser

INPUT_CLASSES = "w-full rounded-lg border px-4 py-3 dark:bg-gray-800 dark:border-gray-600"


class AdminRegistrationForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150, label=_("Full name"),
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES}),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES}),
        min_length=8,
    )
    password_confirm = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES}),
    )

    class Meta:
        model = AdminUser
        fields = ["phone_number"]
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "+998901234567"}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        if AdminUser.objects.filter(phone_number=phone).exists():
            raise ValidationError(_("An account with this phone number already exists."))
        return phone

    def clean(self):
        cleaned_data = super().clean()
        pw, pw2 = cleaned_data.get("password"), cleaned_data.get("password_confirm")
        if pw and pw2 and pw != pw2:
            raise ValidationError(_("Passwords do not match."))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        # username must be unique & is required by AbstractUser; derive it
        # from the phone number since customers never see/use it.
        user.username = self.cleaned_data["phone_number"]
        user.set_password(self.cleaned_data["password"])
        user.is_active = False  # activated only via Telegram verification
        user.is_staff = True
        if commit:
            user.save()
        return user


class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Phone number"),
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "placeholder": "+998901234567", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES}),
    )
