from datetime import timedelta

from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.notifications.due_reminders import DueReminderNotification
from tasks.tests.factories import GroupFactory, TaskFactory

from ..models import NotificationEvent
from .base import PREVIEW_EMAIL, PREVIEW_USERNAME, BaseEmailPreview


class TaskDueReminderPreview(BaseEmailPreview):
    event = NotificationEvent.TASK_DUE_REMINDER.value
    user = None

    def _seed(self):
        today = timezone.localdate()
        self.user = UserFactory(username=PREVIEW_USERNAME, email=PREVIEW_EMAIL)
        group = GroupFactory(user=self.user)

        overdue = TaskFactory(
            user=self.user, due_date=today - timedelta(days=2), weight=4, group=group
        )
        TaskFactory(user=self.user, parent=overdue, completed=True)
        TaskFactory(user=self.user, parent=overdue)
        TaskFactory(user=self.user, due_date=today)

    def _get_notification_context(self):
        return {**DueReminderNotification().context(self.user), "user": self.user}
