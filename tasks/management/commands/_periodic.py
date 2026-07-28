from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django_q.models import Schedule


class PeriodicScheduleCommand(BaseCommand):
    schedule_name = None
    func = None

    def schedule_defaults(self):
        raise NotImplementedError

    def handle(self, *args, **options):
        if self.schedule_name is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} must set 'schedule_name'."
            )
        if self.func is None:
            raise ImproperlyConfigured(f"{type(self).__name__} must set 'func'.")

        _, created = Schedule.objects.update_or_create(
            name=self.schedule_name,
            defaults={'func': self.func, **self.schedule_defaults()},
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(
            self.style.SUCCESS(f"{action} schedule '{self.schedule_name}': {self.func}")
        )
