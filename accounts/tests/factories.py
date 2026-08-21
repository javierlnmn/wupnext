from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_grant_model,
    get_refresh_token_model,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'pass1234')


class OAuthApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_application_model()

    name = factory.Sequence(lambda n: f'client{n}')
    client_type = get_application_model().CLIENT_PUBLIC
    authorization_grant_type = get_application_model().GRANT_AUTHORIZATION_CODE


class AccessTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_access_token_model()

    user = factory.SubFactory(UserFactory)
    application = factory.SubFactory(OAuthApplicationFactory)
    token = factory.Sequence(lambda n: f'access-{n}')
    scope = 'read'
    expires = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


class RefreshTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_refresh_token_model()

    user = factory.SubFactory(UserFactory)
    application = factory.SubFactory(OAuthApplicationFactory)
    token = factory.Sequence(lambda n: f'refresh-{n}')


class GrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_grant_model()

    user = factory.SubFactory(UserFactory)
    application = factory.SubFactory(OAuthApplicationFactory)
    code = factory.Sequence(lambda n: f'code-{n}')
    redirect_uri = 'https://client.test/callback'
    expires = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=10))
