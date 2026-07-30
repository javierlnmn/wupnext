from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.views import View

from notifications.forms import NotificationPreferencesForm
from pomodoro.forms import PomodoroPreferencesForm
from pomodoro.models import PomodoroUserPreference


class PreferencesView(LoginRequiredMixin, View):
    def post(self, request):
        forms = [
            PomodoroPreferencesForm(
                request.POST, instance=PomodoroUserPreference.for_user(request.user)
            ),
            NotificationPreferencesForm(request.POST, user=request.user),
        ]

        if not all([form.is_valid() for form in forms]):
            errors = {
                name: error for form in forms for name, error in form.errors.items()
            }
            return JsonResponse({'ok': False, 'errors': errors}, status=400)

        with transaction.atomic():
            for form in forms:
                form.save()

        return JsonResponse({'ok': True})
