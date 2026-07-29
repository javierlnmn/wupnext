from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    EMAIL = 'email', 'Email'


class NotificationChannelSwitch(models.Model):
    channel = models.CharField(max_length=32, choices=Channel.choices, unique=True)
    enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ['channel']

    def __str__(self):
        return f'{self.channel}: {"on" if self.enabled else "off"}'

    @classmethod
    def is_enabled(cls, channel):
        return cls.objects.filter(channel=channel, enabled=True).exists()


class NotificationEventSwitch(models.Model):
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    enabled = models.BooleanField(default=False)
    on_by_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['event', 'channel']
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'channel'],
                name='unique_notification_event_switch',
            )
        ]

    def __str__(self):
        return f'{self.event} → {self.channel}: {"on" if self.enabled else "off"}'

    @classmethod
    def is_enabled_for_channel(cls, event, channel):
        return cls.objects.filter(event=event, channel=channel, enabled=True).exists()

    @classmethod
    def is_enabled_anywhere(cls, event):
        return cls.objects.filter(event=event, enabled=True).exists()

    @classmethod
    def default_for(cls, event, channel):
        return cls.objects.filter(
            event=event, channel=channel, enabled=True, on_by_default=True
        ).exists()


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
    def is_enabled_for_channel(cls, user, event, channel):
        chosen = cls.objects.filter(user=user, event=event, channel=channel).first()

        if chosen is None:
            return NotificationEventSwitch.default_for(event, channel)

        return chosen.enabled

    @classmethod
    def is_enabled_for_any_channel(cls, user, event, channels):
        return any(
            cls.is_enabled_for_channel(user, event, channel) for channel in channels
        )


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
