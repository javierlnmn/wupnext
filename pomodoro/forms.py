from django import forms

from .models import PomodoroState, PomodoroUserPreference


class PomodoroStateForm(forms.ModelForm):
    class Meta:
        model = PomodoroState
        fields = ['phase', 'running', 'ends_at_ms', 'remaining', 'completed']


class PomodoroPreferencesForm(forms.ModelForm):
    class Meta:
        model = PomodoroUserPreference
        fields = ['focus', 'short_break', 'long_break', 'long_every']
