from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .forms import NotificationPreferencesForm


class NotificationPreferencesView(LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            'notifications/preferences_fields.html',
            {'form': NotificationPreferencesForm(user=request.user)},
        )
