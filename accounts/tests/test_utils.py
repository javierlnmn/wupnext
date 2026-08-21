from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from oauth2_provider.models import get_access_token_model

from accounts.utils import get_oauth2_clients_for_user

from .factories import AccessTokenFactory, OAuthApplicationFactory, UserFactory


class GetOAuthClientsForUserTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_returns_empty_queryset(self):
        apps = get_oauth2_clients_for_user(self.user)

        self.assertEqual(apps.count(), 0)

    def test_gets_all_user_applications(self):
        claude = OAuthApplicationFactory(name='Claude')
        AccessTokenFactory(user=self.user, application=claude)
        codex = OAuthApplicationFactory(name='Codex')
        AccessTokenFactory(user=self.user, application=codex)

        apps = get_oauth2_clients_for_user(self.user)

        self.assertEqual(apps.count(), 2)
        self.assertIn(claude, apps)
        self.assertIn(codex, apps)

    def test_does_not_retrieve_other_user_apps(self):
        cursor = OAuthApplicationFactory(name='Cursor')
        AccessTokenFactory(user=UserFactory(), application=cursor)

        apps = get_oauth2_clients_for_user(self.user)

        self.assertEqual(apps.count(), 0)

    def test_lists_a_client_once_when_it_holds_several_tokens(self):
        claude = OAuthApplicationFactory(name='Claude')
        AccessTokenFactory(user=self.user, application=claude)
        AccessTokenFactory(user=self.user, application=claude)

        apps = get_oauth2_clients_for_user(self.user)

        self.assertEqual(apps.count(), 1)

    def test_orders_the_most_recently_used_client_first(self):
        old = AccessTokenFactory(user=self.user)
        recent = AccessTokenFactory(user=self.user)
        get_access_token_model().objects.filter(pk=old.pk).update(
            created=timezone.now() - timedelta(days=2)
        )

        apps = get_oauth2_clients_for_user(self.user)

        self.assertEqual(list(apps), [recent.application, old.application])
