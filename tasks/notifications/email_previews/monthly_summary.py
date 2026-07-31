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
from ..notifications.monthly_summary import MonthlySummaryNotification


@register
class TaskMonthlySummaryPreview(BaseEmailPreview):
    event = MonthlySummaryNotification.event
    user = None

    def _seed(self):
        today = timezone.localdate()
        last_month_end = today.replace(day=1) - timedelta(days=1)

        self.user = get_user_model()(
            username=PREVIEW_USERNAME,
            email=PREVIEW_EMAIL,
        )
        self.user.set_unusable_password()
        self.user.save()

        group = Group.objects.create(user=self.user, name='Side project')

        self._complete(
            'Ship the landing page',
            weight=8,
            group=group,
            due_date=last_month_end,
            finished=last_month_end - timedelta(days=3),
        )
        self._complete(
            'Renew the domain',
            weight=3,
            due_date=last_month_end - timedelta(days=10),
            finished=last_month_end - timedelta(days=6),
        )
        self._complete('Tidy the backlog', weight=1, finished=last_month_end)

        Task.objects.create(
            user=self.user,
            name='Reply to the tax email',
            weight=5,
            due_date=today - timedelta(days=4),
        )
        Task.objects.create(
            user=self.user,
            name='Draft next quarter goals',
            weight=2,
            group=group,
            due_date=today + timedelta(days=12),
        )
        Task.objects.create(user=self.user, name='Read that paper', weight=1)

    def _complete(self, name, weight, finished, due_date=None, group=None):
        task = Task.objects.create(
            user=self.user,
            name=name,
            weight=weight,
            group=group,
            due_date=due_date,
        )
        task.completed_at = timezone.make_aware(
            timezone.datetime(finished.year, finished.month, finished.day, 12)
        )
        task.save(update_fields=['completed_at'])

    def _get_notification_context(self):
        return {
            **MonthlySummaryNotification().context(self.user),
            'user': self.user,
        }
