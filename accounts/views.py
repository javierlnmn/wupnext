from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .forms import PomodoroSettingsForm
from .models import UserPreferences


class PomodoroSettingsView(LoginRequiredMixin, View):
    def post(self, request):
        prefs = UserPreferences.for_user(request.user)
        data = {
            "pomodoro_focus": request.POST.get("focus"),
            "pomodoro_short_break": request.POST.get("short"),
            "pomodoro_long_break": request.POST.get("long"),
            "pomodoro_long_every": request.POST.get("every"),
        }
        form = PomodoroSettingsForm(data, instance=prefs)
        if form.is_valid():
            form.save()
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
