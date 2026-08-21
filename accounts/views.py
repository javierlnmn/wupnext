from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from mcp_server.djangomcp import global_mcp_server
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_grant_model,
    get_refresh_token_model,
)

from notifications.forms import NotificationPreferencesForm
from pomodoro.forms import PomodoroPreferencesForm
from pomodoro.models import PomodoroUserPreference

from .utils import get_oauth2_clients_for_user


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


class MCPPreferencesView(LoginRequiredMixin, View):
    def get(self, request):
        base_url = settings.MCP_BASE_URL.rstrip('/')
        endpoint_path = reverse('mcp_server_streamable_http_endpoint')

        return render(
            request,
            'accounts/mcp_preferences.html',
            {
                'endpoint': f'{base_url}{endpoint_path}',
                'tools': async_to_sync(global_mcp_server.list_tools)(),
                'clients': get_oauth2_clients_for_user(request.user),
            },
        )


class MCPClientRevokeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(
            get_application_model(), pk=pk, accesstoken__user=request.user
        )

        with transaction.atomic():
            for Model in (
                get_access_token_model(),
                get_refresh_token_model(),
                get_grant_model(),
            ):
                Model.objects.filter(
                    user=request.user, application=application
                ).delete()

        return render(
            request,
            'accounts/partials/mcp_clients.html',
            {'clients': get_oauth2_clients_for_user(request.user)},
        )
