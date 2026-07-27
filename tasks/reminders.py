import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import UserPreferences
from common.models import SiteSettings
from notifications.models import NotificationEvent
from notifications.service import notification_service

from .models import Task

logger = logging.getLogger(__name__)


def due_reminder_context(user):
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
    return {
        "date": today,
        "overdue": [task for task in tasks if task.due_date < today],
        "due_today": [task for task in tasks if task.due_date == today],
    }


def send_due_reminders():
    if not SiteSettings.load().tasks_notification_due_reminders_enabled:
        return

    for user in get_user_model().objects.filter(is_active=True):
        context = due_reminder_context(user)
        if not context["overdue"] and not context["due_today"]:
            continue

        prefs = UserPreferences.for_user(user)
        if not prefs.notification_channels_email_enabled:
            continue

        try:
            notification_service.notify(
                user,
                NotificationEvent.TASK_DUE_REMINDER,
                context=context,
                dedup_key=str(context["date"]),
            )
        except Exception:
            logger.exception("Failed to send due reminder to %s", user)
