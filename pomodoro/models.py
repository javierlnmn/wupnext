from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PomodoroUserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pomodoro_preference',
    )
    focus = models.PositiveSmallIntegerField(
        default=25,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    short_break = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    long_break = models.PositiveSmallIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    long_every = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    class Meta:
        verbose_name = 'user preference'
        verbose_name_plural = 'user preferences'

    def __str__(self):
        return f'Pomodoro preferences for {self.user}'

    @classmethod
    def for_user(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def settings_dict(self):
        return {
            'focus': self.focus,
            'short': self.short_break,
            'long': self.long_break,
            'every': self.long_every,
        }


class Phase(models.TextChoices):
    FOCUS = 'focus', 'Focus'
    SHORT = 'short', 'Short break'
    LONG = 'long', 'Long break'


class PomodoroState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pomodoro_state',
    )
    phase = models.CharField(max_length=5, choices=Phase.choices, default=Phase.FOCUS)
    running = models.BooleanField(default=False)
    ends_at_ms = models.BigIntegerField(null=True, blank=True, default=None)
    remaining = models.PositiveIntegerField(null=True, blank=True, default=None)
    completed = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Pomodoro state for {self.user}'

    @classmethod
    def for_user(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def state_dict(self):
        return {
            'phase': self.phase,
            'running': self.running,
            'endsAt': self.ends_at_ms,
            'remaining': self.remaining,
            'completed': self.completed,
            'updatedAt': int(self.updated_at.timestamp() * 1000),
        }
