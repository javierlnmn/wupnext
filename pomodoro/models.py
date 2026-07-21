from django.conf import settings
from django.db import models


class Phase(models.TextChoices):
    FOCUS = "focus", "Focus"
    SHORT = "short", "Short break"
    LONG = "long", "Long break"


class PomodoroState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pomodoro_state",
    )
    phase = models.CharField(max_length=5, choices=Phase.choices, default=Phase.FOCUS)
    running = models.BooleanField(default=False)
    ends_at_ms = models.BigIntegerField(null=True, blank=True, default=None)
    remaining = models.PositiveIntegerField(null=True, blank=True, default=None)
    completed = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pomodoro state for {self.user}"

    @classmethod
    def for_user(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def state_dict(self):
        return {
            "phase": self.phase,
            "running": self.running,
            "endsAt": self.ends_at_ms,
            "remaining": self.remaining,
            "completed": self.completed,
            "updatedAt": int(self.updated_at.timestamp() * 1000),
        }
