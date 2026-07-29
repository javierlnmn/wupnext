from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.base import BaseBulkNotification
from notifications.models import Channel
from notifications.registry import register

from ..models import Task


@register
class DueReminderNotification(BaseBulkNotification):
    event = 'task_due_reminder'
    label = 'Deadline reminders'
    description = 'Daily digest of tasks that are due or overdue.'
    channels = (Channel.EMAIL,)

    def _is_applicable_for_user(self, user, context):
        return bool(context['overdue'] or context['due_today'])

    def _dedup_key(self, user, context):
        return str(context['date'])

    def _recipients(self):
        return get_user_model().objects.filter(
            is_active=True,
            pk__in=self._due_tasks(timezone.localdate()).values('user_id'),
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
            .select_related('group')
            .prefetch_related('subtasks')
            .order_by('due_date')
        )

        return {
            'date': today,
            'overdue': [task for task in tasks if task.due_date < today],
            'due_today': [task for task in tasks if task.due_date == today],
        }
