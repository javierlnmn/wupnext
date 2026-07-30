from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    EMAIL = 'email', 'Email'


class NotificationChannelSwitch(models.Model):
    channel = models.CharField(max_length=32, choices=Channel.choices, unique=True)
    enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ['channel']
        verbose_name = 'channel switch'
        verbose_name_plural = 'channel switches'

    def __str__(self):
        return f'{self.channel}: {"on" if self.enabled else "off"}'


class NotificationEventSwitch(models.Model):
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    enabled = models.BooleanField(default=False)
    on_by_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['event', 'channel']
        verbose_name = 'event switch'
        verbose_name_plural = 'event switches'
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'channel'],
                name='unique_notification_event_switch',
            )
        ]

    def __str__(self):
        return f'{self.event} → {self.channel}: {"on" if self.enabled else "off"}'

    @classmethod
    def get_enabled_channels_defaults_for_event(cls, event):
        return dict(
            cls.objects.filter(
                event=event,
                enabled=True,
                channel__in=NotificationChannelSwitch.objects.filter(
                    enabled=True
                ).values('channel'),
            ).values_list('channel', 'on_by_default')
        )


class NotificationUserPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    enabled = models.BooleanField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event', 'channel']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'event', 'channel'],
                name='unique_notification_user_preference',
            )
        ]

    def __str__(self):
        return f'{self.event} → {self.channel}: {"on" if self.enabled else "off"}'

    @classmethod
    def get_user_stored_preferences_for_event(cls, user, event, available_channels):
        return dict(
            cls.objects.filter(
                user=user, event=event, channel__in=available_channels
            ).values_list('channel', 'enabled')
        )

    @classmethod
    def get_bulk_user_stored_preferences_for_event(
        cls, users, event, available_channels
    ):
        preferences = {}

        for user_id, channel, enabled in cls.objects.filter(
            user__in=users, event=event, channel__in=available_channels
        ).values_list('user_id', 'channel', 'enabled'):
            preferences.setdefault(user_id, {})[channel] = enabled

        return preferences


class NotificationLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_logs',
    )
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    dedup_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'event', 'channel', 'dedup_key'],
                name='unique_notification_dispatch',
            )
        ]

    def __str__(self):
        return f'{self.event} → {self.channel} ({self.dedup_key})'
