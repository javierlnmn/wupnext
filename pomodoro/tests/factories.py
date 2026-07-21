import factory

from accounts.tests.factories import UserFactory
from pomodoro.models import PomodoroState


class PomodoroStateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PomodoroState

    user = factory.SubFactory(UserFactory)
