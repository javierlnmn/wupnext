from django.core import mail, signing
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.notifications.notifications.password_reset import (
    PasswordResetNotification,
)
from accounts.tests.factories import UserFactory
from notifications.channels.email import UNSUBSCRIBE_SALT
from notifications.models import Channel, NotificationUserPreference
from notifications.service import NotificationService
from notifications.tests.factories import (
    NotificationUserPreferenceFactory,
    enable_notification,
)
from tasks.notifications.notifications.due_reminders import DueReminderNotification

EVENT = 'task_due_reminder'
SITE_URL = 'https://wupnext.test'
PLAIN_STATIC = {
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class UnsubscribeViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.url = self.url_for(self.user, EVENT)

    def url_for(self, user, event, channel=Channel.EMAIL):
        token = signing.dumps(
            {'user': user.pk, 'event': event, 'channel': channel},
            salt=UNSUBSCRIBE_SALT,
        )

        return reverse('notifications:unsubscribe', kwargs={'token': token})

    def preference(self):
        return NotificationUserPreference.objects.filter(
            user=self.user, event=EVENT, channel=Channel.EMAIL
        ).first()

    def test_needs_no_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_get_offers_the_choice_without_taking_it(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'Stop receiving')
        self.assertIsNone(self.preference())

    def test_post_disables_the_preference(self):
        self.client.post(self.url)

        self.assertFalse(self.preference().enabled)

    def test_post_confirms_it_is_done(self):
        response = self.client.post(self.url)

        self.assertContains(response, "You're unsubscribed")

    def test_post_overwrites_an_existing_opt_in(self):
        NotificationUserPreferenceFactory(user=self.user, enabled=True)

        self.client.post(self.url)

        self.assertFalse(self.preference().enabled)
        self.assertEqual(NotificationUserPreference.objects.count(), 1)

    def test_unsubscribing_twice_is_harmless(self):
        self.client.post(self.url)
        self.client.post(self.url)

        self.assertFalse(self.preference().enabled)
        self.assertEqual(NotificationUserPreference.objects.count(), 1)

    def test_touches_only_the_event_in_the_token(self):
        self.client.post(self.url)

        self.assertFalse(
            NotificationUserPreference.objects.filter(
                event='task_monthly_summary'
            ).exists()
        )

    def test_touches_only_the_user_in_the_token(self):
        other = UserFactory()

        self.client.post(self.url)

        self.assertFalse(NotificationUserPreference.objects.filter(user=other).exists())

    def test_a_tampered_token_is_refused(self):
        url = reverse('notifications:unsubscribe', kwargs={'token': 'not-a-token'})

        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertIsNone(self.preference())

    def test_a_token_signed_with_another_salt_is_refused(self):
        forged = signing.dumps(
            {'user': self.user.pk, 'event': EVENT, 'channel': Channel.EMAIL},
            salt='some.other.purpose',
        )
        url = reverse('notifications:unsubscribe', kwargs={'token': forged})

        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertIsNone(self.preference())

    def test_a_notification_that_is_not_optional_sends_you_home(self):
        url = self.url_for(self.user, PasswordResetNotification.event)

        self.assertRedirects(
            self.client.get(url), reverse('tasks:board'), target_status_code=302
        )
        self.assertRedirects(
            self.client.post(url), reverse('tasks:board'), target_status_code=302
        )

    def test_a_notification_that_is_not_optional_stores_no_opt_out(self):
        self.client.post(self.url_for(self.user, PasswordResetNotification.event))

        self.assertFalse(
            NotificationUserPreference.objects.filter(
                event=PasswordResetNotification.event
            ).exists()
        )

    def test_an_unregistered_event_sends_you_home(self):
        url = self.url_for(self.user, 'retired_event')

        self.assertRedirects(
            self.client.post(url), reverse('tasks:board'), target_status_code=302
        )

    def test_a_deleted_user_is_refused(self):
        url = self.url_for(self.user, EVENT)
        self.user.delete()

        self.assertEqual(self.client.post(url).status_code, 404)

    def test_names_the_notification_being_declined(self):
        response = self.client.get(self.url)

        self.assertContains(response, DueReminderNotification.label.lower())


@override_settings(SITE_URL=SITE_URL, STORAGES=PLAIN_STATIC)
class UnsubscribeLinkTests(TestCase):
    """The link has to reach the reader, and only in mail they may decline."""

    def setUp(self):
        self.user = UserFactory()
        enable_notification()

    def send_reminder(self):
        NotificationService(DueReminderNotification()).notify(
            self.user,
            channels=[Channel.EMAIL],
            context=DueReminderNotification().context(self.user),
        )
        return mail.outbox[0]

    def test_the_digest_carries_an_absolute_link(self):
        message = self.send_reminder()

        self.assertIn(f'{SITE_URL}/notifications/unsubscribe/', message.body)

    def test_the_html_part_carries_it_too(self):
        html, _ = self.send_reminder().alternatives[0]

        self.assertIn(f'{SITE_URL}/notifications/unsubscribe/', html)

    def test_the_link_in_the_email_actually_works(self):
        body = self.send_reminder().body
        start = body.index(f'{SITE_URL}/notifications/unsubscribe/') + len(SITE_URL)
        path = body[start:].split()[0]

        self.client.post(path)

        self.assertFalse(
            NotificationUserPreference.objects.get(user=self.user, event=EVENT).enabled
        )

    def test_the_password_reset_email_carries_none(self):
        NotificationService(PasswordResetNotification()).send(self.user)

        message = mail.outbox[0]
        self.assertNotIn('unsubscribe', message.body.lower())
        self.assertNotIn('/notifications/unsubscribe/', message.alternatives[0][0])

    @override_settings(SITE_URL='')
    def test_no_link_without_a_site_url_to_hang_it_on(self):
        message = self.send_reminder()

        self.assertNotIn('/notifications/unsubscribe/', message.body)
