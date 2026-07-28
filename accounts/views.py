from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .forms import PreferencesForm
from .models import UserPreferences


class PreferencesView(LoginRequiredMixin, View):
    def post(self, request):
        prefs = UserPreferences.for_user(request.user)
        form = PreferencesForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            return JsonResponse({'ok': True})

        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
