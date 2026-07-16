from django import forms

from .models import DEFAULT_GROUP_COLOR, GROUP_COLOR_VALUES, Group, Task


class TaskForm(forms.Form):
    task_id = forms.IntegerField(required=False)
    name = forms.CharField(max_length=255)
    weight = forms.IntegerField(required=False)
    group_id = forms.IntegerField(required=False)
    parent_id = forms.IntegerField(required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name

    def clean_weight(self):
        weight = self.cleaned_data.get("weight") or 0
        return min(max(weight, 0), 5)

    def clean(self):
        cleaned = super().clean()

        parent = None
        if cleaned.get("parent_id"):
            parent = Task.objects.filter(
                id=cleaned["parent_id"], user=self.user, parent__isnull=True
            ).first()
        cleaned["parent"] = parent

        group = None
        if not parent and cleaned.get("group_id"):
            group = Group.objects.filter(
                id=cleaned["group_id"], user=self.user
            ).first()
        cleaned["group"] = group

        return cleaned


class GroupForm(forms.Form):
    name = forms.CharField(max_length=100)
    color = forms.CharField(max_length=9, required=False)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name

    def clean_color(self):
        color = self.cleaned_data.get("color") or ""
        return color if color in GROUP_COLOR_VALUES else DEFAULT_GROUP_COLOR
