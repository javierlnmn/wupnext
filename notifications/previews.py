from contextlib import contextmanager
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from .exceptions import MissingPreview
from .models import NotificationEvent

PREVIEW_USERNAME = "preview"
PREVIEW_EMAIL = "preview@wupnext.invalid"


class EmailPreview:
    event = None
    user = None

    def seed(self):
        raise NotImplementedError

    def context(self):
        raise NotImplementedError


class TaskDueReminderPreview(EmailPreview):
    event = NotificationEvent.TASK_DUE_REMINDER.value

    def seed(self):
        from accounts.tests.factories import UserFactory
        from tasks.tests.factories import GroupFactory, TaskFactory

        today = timezone.localdate()
        self.user = UserFactory(username=PREVIEW_USERNAME, email=PREVIEW_EMAIL)
        group = GroupFactory(user=self.user)

        overdue = TaskFactory(
            user=self.user, due_date=today - timedelta(days=2), weight=4, group=group
        )
        TaskFactory(user=self.user, parent=overdue, completed=True)
        TaskFactory(user=self.user, parent=overdue)
        TaskFactory(user=self.user, due_date=today)

    def context(self):
        from tasks.notifications.due_reminders import DueReminderNotification

        return {**DueReminderNotification().context(self.user), "user": self.user}


def build_registry(*previews):
    registry = {}
    for preview in previews:
        if not preview.event:
            raise ImproperlyConfigured(f"{type(preview).__name__} must set 'event'.")
        registry[preview.event] = preview
    return registry


PREVIEWS = build_registry(TaskDueReminderPreview())


@contextmanager
def preview_context(event):
    preview = PREVIEWS.get(event)
    if preview is None:
        raise MissingPreview(
            f"No preview registered for '{event}'. "
            f"Available: {', '.join(sorted(PREVIEWS)) or 'none'}."
        )

    with transaction.atomic():
        preview.seed()
        yield preview.context()
        transaction.set_rollback(True)
