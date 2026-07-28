import datetime

from django.utils import timezone
from django_q.models import Schedule

from ._periodic import PeriodicScheduleCommand

REMINDER_HOUR = 7


class Command(PeriodicScheduleCommand):
    help = "Register the daily due-reminder schedule (idempotent)."
    schedule_name = "due-reminders"
    func = "tasks.jobs.send_due_reminders"

    def schedule_defaults(self):
        return {
            "schedule_type": Schedule.DAILY,
            "next_run": self.calculate_next_run(),
        }

    def calculate_next_run(self):
        now = timezone.now()
        candidate = now.replace(hour=REMINDER_HOUR, minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += datetime.timedelta(days=1)
        return candidate
