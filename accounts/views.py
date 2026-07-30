from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from notifications.forms import NotificationPreferencesForm

from .forms import PreferencesForm
from .models import UserPreferences


class PreferencesView(LoginRequiredMixin, View):
    def post(self, request):
        prefs = UserPreferences.for_user(request.user)
        form = PreferencesForm(request.POST, instance=prefs)
        notifications_form = NotificationPreferencesForm(
            request.POST, user=request.user
        )

        if all([form.is_valid(), notifications_form.is_valid()]):
            form.save()
            notifications_form.save()
            return JsonResponse({'ok': True})

        return JsonResponse(
            {'ok': False, 'errors': {**form.errors, **notifications_form.errors}},
            status=400,
        )
