from django.utils import timezone

from common.models import SiteSettings
from notifications.base import Notification
from notifications.models import NotificationEvent

from ..models import Task


class DueReminderNotification(Notification):
    event = NotificationEvent.TASK_DUE_REMINDER

    def is_enabled(self):
        return SiteSettings.load().tasks_notification_due_reminders_enabled

    def context(self, user):
        today = timezone.localdate()
        tasks = list(
            Task.objects.filter_unarchived()
            .filter(
                user=user,
                parent__isnull=True,
                completed_at__isnull=True,
                due_date__isnull=False,
                due_date__lte=today,
            )
            .order_by("due_date")
        )

        if not tasks:
            return None

        return {
            "date": today,
            "overdue": [task for task in tasks if task.due_date < today],
            "due_today": [task for task in tasks if task.due_date == today],
        }

    def dedup_key(self, user, context):
        return str(context["date"])
