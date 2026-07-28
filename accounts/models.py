from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)

    def __str__(self):
        return f'{self.username} ({self.first_name} {self.last_name})'


class UserPreferences(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences',
    )

    # Pomodoro
    pomodoro_focus = models.PositiveSmallIntegerField(
        default=25,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    pomodoro_short_break = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    pomodoro_long_break = models.PositiveSmallIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
    )
    pomodoro_long_every = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    # Notifications
    notification_channels_email_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'Preferences for {self.user}'

    @classmethod
    def for_user(cls, user):
        return cls.objects.get_or_create(user=user)[0]

    def pomodoro_dict(self):
        return {
            'focus': self.pomodoro_focus,
            'short': self.pomodoro_short_break,
            'long': self.pomodoro_long_break,
            'every': self.pomodoro_long_every,
        }
