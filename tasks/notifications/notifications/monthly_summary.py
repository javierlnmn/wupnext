from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from notifications.base import BaseBulkNotification
from notifications.models import Channel
from notifications.registry import register

from ...models import Task


@register
class MonthlySummaryNotification(BaseBulkNotification):
    event = 'task_monthly_summary'
    label = 'Monthly summary'
    description = 'What you closed last month, and what is still open.'
    channels = (Channel.EMAIL,)
    schedule = '0 8 1 * *'

    def is_applicable_for(self, user, context):
        return bool(context['completed'] or context['pending'] or context['overdue'])

    def dedup_key(self, user, context):
        return f'{context["period_start"]:%Y-%m}'

    def recipients(self):
        return get_user_model().objects.filter(
            is_active=True,
            pk__in=self._get_reportable_tasks().values('user_id'),
        )

    def context(self, user):
        period_start, period_end = self._get_period()
        today = timezone.localdate()
        completed, pending, overdue = [], [], []

        for task in (
            self._get_reportable_tasks().filter(user=user).select_related('group')
        ):
            if task.completed_at:
                finished = timezone.localtime(task.completed_at).date()

                if period_start <= finished <= period_end:
                    completed.append(self._get_completion(task, finished))
            elif task.due_date and task.due_date < today:
                overdue.append(task)
            else:
                pending.append(task)

        return {
            'period_start': period_start,
            'period_end': period_end,
            'completed': sorted(completed, key=lambda entry: entry['finished']),
            'pending': sorted(pending, key=self._get_due_date_key),
            'overdue': sorted(overdue, key=self._get_due_date_key),
            'completed_weight': sum(entry['task'].weight for entry in completed),
        }

    def _get_period(self):
        period_end = timezone.localdate().replace(day=1) - timedelta(days=1)
        return period_end.replace(day=1), period_end

    def _get_reportable_tasks(self):
        period_start, period_end = self._get_period()

        return Task.objects.filter_unarchived().filter(
            Q(completed_at__date__range=(period_start, period_end))
            | Q(completed_at__isnull=True),
            parent__isnull=True,
        )

    def _get_completion(self, task, finished):
        target = task.due_date
        days = abs((finished - target).days) if target else None

        return {
            'task': task,
            'target': target,
            'finished': finished,
            'on_time': finished <= target if target else None,
            'days': days,
        }

    def _get_due_date_key(self, task):
        return (task.due_date is None, task.due_date)
