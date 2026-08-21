from django import forms

from .models import (
    DEFAULT_GROUP_COLOR,
    GROUP_COLOR_VALUES,
    MAX_TASK_WEIGHT,
    Group,
    Task,
)


class TaskForm(forms.Form):
    task_id = forms.IntegerField(required=False)
    name = forms.CharField(max_length=255)
    weight = forms.IntegerField(required=False)
    group_id = forms.IntegerField(required=False)
    parent_id = forms.IntegerField(required=False)
    due_date = forms.DateField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError('Name is required.')
        return name

    def clean_weight(self):
        weight = self.cleaned_data.get('weight') or 0
        return min(max(weight, 0), MAX_TASK_WEIGHT)

    def clean(self):
        cleaned = super().clean()

        if cleaned.get('parent_id'):
            parent = Task.objects.filter(
                id=cleaned['parent_id'], user=self.user, parent__isnull=True
            ).first()

            if parent:
                cleaned['parent'] = parent
                cleaned['group'] = None
                cleaned['due_date'] = None

                return cleaned

        cleaned['parent'] = None

        group = None
        if cleaned.get('group_id'):
            group = Group.objects.filter(id=cleaned['group_id'], user=self.user).first()

        cleaned['group'] = group

        return cleaned


class GroupForm(forms.Form):
    group_id = forms.IntegerField(required=False)
    name = forms.CharField(max_length=100)
    color = forms.CharField(max_length=9, required=False)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError('Name is required.')
        return name

    def clean_color(self):
        color = self.cleaned_data.get('color') or ''
        return color if color in GROUP_COLOR_VALUES else DEFAULT_GROUP_COLOR
