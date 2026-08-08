import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .channels.email import UNSUBSCRIBE_SALT
from .forms import NotificationPreferencesForm
from .models import NotificationUserPreference
from .registry import NOTIFICATIONS

logger = logging.getLogger(__name__)


class NotificationPreferencesView(LoginRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            'notifications/preferences_fields.html',
            {'form': NotificationPreferencesForm(user=request.user)},
        )


class UnsubscribeView(View):
    template_name = 'notifications/unsubscribe.html'

    def _get_payload(self, token):
        try:
            return signing.loads(token, salt=UNSUBSCRIBE_SALT)
        except signing.BadSignature:
            raise Http404('Tampered or malformed unsubscribe token.')

    def _get_notification(self, event):
        notification = NOTIFICATIONS.get(event)

        if notification is None or not notification.optional:
            return None

        return notification

    def get(self, request, token):
        payload = self._get_payload(token)
        notification = self._get_notification(payload['event'])

        if notification is None:
            return redirect('tasks:board')

        return render(request, self.template_name, {'notification': notification})

    def post(self, request, token):
        payload = self._get_payload(token)
        notification = self._get_notification(payload['event'])

        if notification is None:
            return redirect('tasks:board')

        user = get_object_or_404(get_user_model(), pk=payload['user'])

        NotificationUserPreference.objects.update_or_create(
            user=user,
            event=payload['event'],
            channel=payload['channel'],
            defaults={'enabled': False},
        )
        logger.info(
            'Unsubscribed user %s from %s on %s',
            user.pk,
            payload['event'],
            payload['channel'],
        )

        return render(
            request,
            self.template_name,
            {'notification': notification, 'done': True},
        )
