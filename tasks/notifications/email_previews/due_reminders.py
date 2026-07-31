from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.email_previews import (
    PREVIEW_EMAIL,
    PREVIEW_USERNAME,
    BaseEmailPreview,
    register,
)

from ...models import Group, Task
from ..notifications.due_reminders import DueReminderNotification


@register
class TaskDueReminderPreview(BaseEmailPreview):
    event = DueReminderNotification.event
    user = None

    def _seed(self):
        today = timezone.localdate()

        self.user = get_user_model()(
            username=PREVIEW_USERNAME,
            email=PREVIEW_EMAIL,
        )
        self.user.set_unusable_password()
        self.user.save()

        group = Group.objects.create(user=self.user, name='Side project')

        overdue = Task.objects.create(
            user=self.user,
            name='Renew the domain',
            due_date=today - timedelta(days=2),
            weight=4,
            group=group,
        )
        Task.objects.create(
            user=self.user,
            name='Compare registrars',
            parent=overdue,
            completed_at=timezone.now(),
        )
        Task.objects.create(
            user=self.user, name='Update the DNS records', parent=overdue
        )
        Task.objects.create(
            user=self.user, name='Reply to the tax email', due_date=today
        )

    def _get_notification_context(self):
        return {**DueReminderNotification().context(self.user), 'user': self.user}
