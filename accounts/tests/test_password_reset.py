from unittest import mock

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.notifications.notifications.password_reset import (
    PasswordResetNotification,
)
from accounts.tests.factories import UserFactory
from notifications.models import Channel, NotificationLog
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)

EVENT = 'account_password_reset'
SITE_URL = 'https://wupnext.test'

# These pages render the real templates, which reach for hashed static files
# that only exist after collectstatic.
PLAIN_STATIC = {
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


class NotificationTests(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_declares_itself_as_not_optional(self):
        self.assertFalse(PasswordResetNotification.optional)

    def test_never_deduplicates(self):
        notification = PasswordResetNotification()
        context = notification.context(self.user)

        self.assertEqual(notification.dedup_key(self.user, context), '')

    def test_builds_a_path_the_confirm_view_accepts(self):
        context = PasswordResetNotification().context(self.user)

        self.assertEqual(
            context['reset_path'],
            reverse(
                'accounts:password_reset_confirm',
                kwargs={
                    'uidb64': urlsafe_base64_encode(force_bytes(self.user.pk)),
                    'token': context['reset_path'].rstrip('/').rsplit('/', 1)[1],
                },
            ),
        )

    def test_the_token_it_builds_validates_for_that_user(self):
        token = PasswordResetNotification().context(self.user)['reset_path']
        token = token.rstrip('/').rsplit('/', 1)[1]

        self.assertTrue(default_token_generator.check_token(self.user, token))

    @override_settings(PASSWORD_RESET_TIMEOUT=7200)
    def test_reports_how_long_the_link_lasts(self):
        context = PasswordResetNotification().context(self.user)

        self.assertEqual(context['valid_hours'], 2)


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class ResetRequestTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email='user@example.com')
        self.url = reverse('accounts:password_reset')

    def request_reset(self, email='user@example.com'):
        return self.client.post(self.url, {'email': email})

    def test_redirects_to_the_done_page(self):
        response = self.request_reset()

        self.assertRedirects(response, reverse('accounts:password_reset_done'))

    def test_emails_the_account_holder(self):
        self.request_reset()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['user@example.com'])

    def test_uses_the_notification_templates_not_django_defaults(self):
        self.request_reset()

        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Reset your WupNext password')
        self.assertIn('<!doctype html>', message.alternatives[0][0])

    def test_the_link_it_sends_is_absolute_and_works(self):
        self.request_reset()

        path = PasswordResetNotification().context(self.user)['reset_path']
        prefix = f'{SITE_URL}{path.rsplit("/", 2)[0]}/'
        self.assertIn(prefix, mail.outbox[0].body)

    def test_sends_nothing_for_an_unknown_address(self):
        self.request_reset(email='nobody@example.com')

        self.assertEqual(len(mail.outbox), 0)

    def test_says_nothing_either_way_about_an_unknown_address(self):
        known = self.request_reset()
        unknown = self.request_reset(email='nobody@example.com')

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)

    def test_sends_nothing_for_an_inactive_account(self):
        self.user.is_active = False
        self.user.save()

        self.request_reset()

        self.assertEqual(len(mail.outbox), 0)

    def test_a_failed_send_does_not_leak_as_an_error(self):
        with mock.patch(
            'accounts.forms.NotificationService.send', side_effect=Exception('boom')
        ):
            with self.assertLogs('accounts.forms', level='ERROR'):
                response = self.request_reset()

        self.assertRedirects(response, reverse('accounts:password_reset_done'))


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class ConsentBypassTests(TestCase):
    """The reset email is not something a switch or a preference can stop."""

    def setUp(self):
        self.user = UserFactory(email='user@example.com')
        self.url = reverse('accounts:password_reset')

    def request_reset(self):
        return self.client.post(self.url, {'email': 'user@example.com'})

    def test_sends_with_no_switch_rows_at_all(self):
        self.request_reset()

        self.assertEqual(len(mail.outbox), 1)

    def test_sends_although_the_email_channel_is_switched_off(self):
        channel_switch, _ = enable_notification(event=EVENT)
        channel_switch.enabled = False
        channel_switch.save()

        self.request_reset()

        self.assertEqual(len(mail.outbox), 1)

    def test_sends_although_the_user_opted_out(self):
        enable_notification(event=EVENT)
        NotificationUserPreferenceFactory(
            user=self.user, event=EVENT, channel=Channel.EMAIL, enabled=False
        )

        self.request_reset()

        self.assertEqual(len(mail.outbox), 1)

    def test_a_second_request_sends_a_second_email(self):
        self.request_reset()
        self.request_reset()

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.count(), 0)


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class ResetConfirmTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email='user@example.com')
        self.client.post(reverse('accounts:password_reset'), {'email': self.user.email})
        self.path = self.reset_path()

    def reset_path(self):
        body = mail.outbox[0].body
        start = body.index(SITE_URL) + len(SITE_URL)
        return body[start:].split()[0]

    def follow(self):
        # The confirm view swaps the token for a session-held one and redirects
        # to a 'set-password' URL, which is what actually renders the form.
        return self.client.get(self.path, follow=True)

    def test_the_emailed_link_opens_the_form(self):
        response = self.follow()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])

    def test_a_new_password_replaces_the_old_one(self):
        response = self.follow()

        self.client.post(
            response.redirect_chain[-1][0],
            {'new_password1': 'a-fresh-pass-42', 'new_password2': 'a-fresh-pass-42'},
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('a-fresh-pass-42'))

    def test_finishing_lands_on_the_complete_page(self):
        response = self.follow()

        done = self.client.post(
            response.redirect_chain[-1][0],
            {'new_password1': 'a-fresh-pass-42', 'new_password2': 'a-fresh-pass-42'},
        )

        self.assertRedirects(done, reverse('accounts:password_reset_complete'))

    def test_mismatched_passwords_change_nothing(self):
        response = self.follow()

        self.client.post(
            response.redirect_chain[-1][0],
            {'new_password1': 'a-fresh-pass-42', 'new_password2': 'something-else-42'},
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('pass1234'))

    def test_the_link_stops_working_once_used(self):
        response = self.follow()
        self.client.post(
            response.redirect_chain[-1][0],
            {'new_password1': 'a-fresh-pass-42', 'new_password2': 'a-fresh-pass-42'},
        )

        self.assertFalse(self.follow().context['validlink'])

    def test_a_tampered_token_is_refused(self):
        head, _ = self.path.rstrip('/').rsplit('/', 1)

        response = self.client.get(f'{head}/not-a-real-token/', follow=True)

        self.assertFalse(response.context['validlink'])


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class PageTemplateTests(TestCase):
    """django.contrib.admin ships these template names too, and wins the
    app-directory lookup, so each page has to prove it rendered ours."""

    def setUp(self):
        self.user = UserFactory(email='user@example.com')

    def test_the_request_page_is_ours(self):
        response = self.client.get(reverse('accounts:password_reset'))

        self.assertTemplateUsed(response, 'accounts/password_reset_form.html')

    def test_the_sent_page_is_ours(self):
        response = self.client.get(reverse('accounts:password_reset_done'))

        self.assertTemplateUsed(response, 'accounts/password_reset_done.html')

    def test_the_confirm_page_is_ours(self):
        self.client.post(reverse('accounts:password_reset'), {'email': self.user.email})
        body = mail.outbox[0].body
        path = body[body.index(SITE_URL) + len(SITE_URL) :].split()[0]

        response = self.client.get(path, follow=True)

        self.assertTemplateUsed(response, 'accounts/password_reset_confirm.html')

    def test_the_complete_page_is_ours(self):
        response = self.client.get(reverse('accounts:password_reset_complete'))

        self.assertTemplateUsed(response, 'accounts/password_reset_complete.html')

    def test_every_page_wears_the_shared_shell(self):
        for name in (
            'accounts:password_reset',
            'accounts:password_reset_done',
            'accounts:password_reset_complete',
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))

                self.assertTemplateUsed(response, 'accounts/_auth_page.html')
