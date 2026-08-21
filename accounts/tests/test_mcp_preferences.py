from django.test import TestCase, override_settings
from django.urls import reverse
from oauth2_provider.models import (
    get_access_token_model,
    get_grant_model,
    get_refresh_token_model,
)

from accounts.tests.factories import (
    AccessTokenFactory,
    GrantFactory,
    OAuthApplicationFactory,
    RefreshTokenFactory,
    UserFactory,
)


class MCPPreferencesViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.url = reverse('accounts:mcp_preferences')

    def html(self):
        return self.client.get(self.url).content.decode()

    def test_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 302)

    @override_settings(MCP_BASE_URL='https://wupnext.test')
    def test_shows_the_endpoint_to_paste_into_a_client(self):
        self.assertIn('https://wupnext.test/mcp', self.html())

    def test_lists_the_tools_the_server_publishes(self):
        self.assertIn('get_user_unarchived_tasks', self.html())

    def test_lists_a_client_that_holds_a_token(self):
        application = OAuthApplicationFactory(name='Claude')
        AccessTokenFactory(user=self.user, application=application)

        self.assertIn('Claude', self.html())

    def test_hides_a_client_that_belongs_to_another_user(self):
        application = OAuthApplicationFactory(name='Somebody else')
        AccessTokenFactory(user=UserFactory(), application=application)

        self.assertIn('No client holds access', self.html())


class MCPClientRevokeViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.application = OAuthApplicationFactory(name='Claude')
        AccessTokenFactory(user=self.user, application=self.application)
        self.url = reverse('accounts:mcp_client_revoke', args=[self.application.pk])

    def test_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.post(self.url).status_code, 302)

    def test_drops_every_token_kind_the_client_holds(self):
        RefreshTokenFactory(user=self.user, application=self.application)
        GrantFactory(user=self.user, application=self.application)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_access_token_model().objects.exists())
        self.assertFalse(get_refresh_token_model().objects.exists())
        self.assertFalse(get_grant_model().objects.exists())
        self.assertIn('No client holds access', response.content.decode())

    def test_keeps_the_same_client_connected_for_another_user(self):
        other_token = AccessTokenFactory(
            user=UserFactory(), application=self.application
        )

        self.client.post(self.url)

        self.assertTrue(
            get_access_token_model().objects.filter(pk=other_token.pk).exists()
        )

    def test_cannot_revoke_a_client_it_never_connected_to(self):
        unrelated = OAuthApplicationFactory(name='Unrelated')
        AccessTokenFactory(user=UserFactory(), application=unrelated)

        url = reverse('accounts:mcp_client_revoke', args=[unrelated.pk])

        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(get_access_token_model().objects.count(), 2)
