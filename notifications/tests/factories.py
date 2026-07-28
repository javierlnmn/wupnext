import factory

from accounts.tests.factories import UserFactory
from notifications.models import Channel, NotificationLog


class NotificationLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationLog

    user = factory.SubFactory(UserFactory)
    event = "task_due_reminder"
    channel = Channel.EMAIL
    dedup_key = factory.Sequence(lambda n: f"key-{n}")
