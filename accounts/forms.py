from django import forms

from .models import UserPreferences


class PreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            "pomodoro_focus",
            "pomodoro_short_break",
            "pomodoro_long_break",
            "pomodoro_long_every",
            "notification_channels_email_enabled",
        ]
