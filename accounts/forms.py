from django import forms

from .models import UserPreferences


class PomodoroSettingsForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            "pomodoro_focus",
            "pomodoro_short_break",
            "pomodoro_long_break",
            "pomodoro_long_every",
        ]
