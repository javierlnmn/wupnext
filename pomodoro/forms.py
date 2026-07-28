from django import forms

from .models import PomodoroState


class PomodoroStateForm(forms.ModelForm):
    class Meta:
        model = PomodoroState
        fields = ['phase', 'running', 'ends_at_ms', 'remaining', 'completed']
