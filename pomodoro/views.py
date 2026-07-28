import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from .forms import PomodoroStateForm
from .models import PomodoroState


class PomodoroStateView(LoginRequiredMixin, View):
    def get(self, request):
        state = PomodoroState.for_user(request.user)
        return JsonResponse(state.state_dict())

    def post(self, request):
        state = PomodoroState.for_user(request.user)
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False}, status=400)
        form = PomodoroStateForm(data, instance=state)
        if form.is_valid():
            form.save()
            return JsonResponse(state.state_dict())
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
