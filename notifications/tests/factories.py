import factory

from accounts.tests.factories import UserFactory
from notifications.models import (
    Channel,
    NotificationChannelSwitch,
    NotificationEventSwitch,
    NotificationLog,
    NotificationUserPreference,
)


class NotificationLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationLog

    user = factory.SubFactory(UserFactory)
    event = 'task_due_reminder'
    channel = Channel.EMAIL
    dedup_key = factory.Sequence(lambda n: f'key-{n}')


class NotificationChannelSwitchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationChannelSwitch

    channel = Channel.EMAIL
    enabled = True


class NotificationEventSwitchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationEventSwitch

    event = 'task_due_reminder'
    channel = Channel.EMAIL
    enabled = True
    on_by_default = True


class NotificationUserPreferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationUserPreference

    user = factory.SubFactory(UserFactory)
    event = 'task_due_reminder'
    channel = Channel.EMAIL
    enabled = True


def enable_notification(
    event='task_due_reminder', channel=Channel.EMAIL, on_by_default=True
):
    return (
        NotificationChannelSwitchFactory(channel=channel),
        NotificationEventSwitchFactory(
            event=event, channel=channel, on_by_default=on_by_default
        ),
    )
