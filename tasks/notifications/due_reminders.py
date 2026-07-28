from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserPreferences
from common.models import SiteSettings
from notifications.base import BaseNotification
from notifications.models import NotificationEvent

from ..models import Task


class DueReminderNotification(BaseNotification):
    event = NotificationEvent.TASK_DUE_REMINDER

    def _is_enabled_on_site(self):
        return SiteSettings.load().tasks_notification_due_reminders_enabled

    def _is_enabled_for_user(self, user):
        # TODO: Implement specific per-notification preference
        return UserPreferences.for_user(user).notification_channels_email_enabled

    def _dedup_key(self, user, context):
        return str(context["date"])

    def _recipients(self):
        return get_user_model().objects.filter(
            is_active=True,
            pk__in=self._due_tasks(timezone.localdate()).values("user_id"),
        )

    def _due_tasks(self, today):
        return Task.objects.filter_unarchived().filter(
            parent__isnull=True,
            completed_at__isnull=True,
            due_date__isnull=False,
            due_date__lte=today,
        )

    def context(self, user):
        today = timezone.localdate()
        tasks = list(
            self._due_tasks(today)
            .filter(user=user)
            .select_related("group")
            .prefetch_related("subtasks")
            .order_by("due_date")
        )

        return {
            "date": today,
            "overdue": [task for task in tasks if task.due_date < today],
            "due_today": [task for task in tasks if task.due_date == today],
        }
