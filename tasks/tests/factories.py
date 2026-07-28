import factory
from django.utils import timezone

from accounts.tests.factories import UserFactory
from tasks.models import Group, Task


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Group {n}')


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Task {n}')

    class Params:
        completed = factory.Trait(completed_at=factory.LazyFunction(timezone.now))
        archived = factory.Trait(archived_at=factory.LazyFunction(timezone.now))
