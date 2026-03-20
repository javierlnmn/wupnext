from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField(max_length=255)
    date = models.DateField()
    completed = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=None, null=True, blank=True)
    last_started = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_running(self):
        return self.last_started is not None

    @property
    def total_elapsed_seconds(self):
        total = self.elapsed_seconds
        if self.last_started:
            total += int((timezone.now() - self.last_started).total_seconds())
        return total

    @classmethod
    def get_user_tasks_for_date(cls, user, date):
        if date is None:
            date = timezone.now().date()
        return cls.objects.filter(user=user, date=date)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.position is None:
            if Task.objects.count() == 0:
                self.position = 1
            else:
                self.position = (
                    Task.objects.filter(user=self.user, date=self.date).last().position
                    + 1
                )
        super().save(*args, **kwargs)
