from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from notifications.email_previews import (
    PREVIEWS,
    BaseEmailPreview,
    get_preview,
    register,
)
from notifications.exceptions import MissingPreview
from notifications.models import NotificationLog
from notifications.tests.factories import NotificationLogFactory

EVENT = 'task_due_reminder'
STUB_EVENT = 'stub_event'
LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'


class StubPreview(BaseEmailPreview):
    event = EVENT

    def _seed(self):
        self.log = NotificationLogFactory()
        self.user = self.log.user

    def _get_notification_context(self):
        return {
            'user': self.user,
            'date': timezone.localdate(),
            'overdue': [],
            'due_today': [],
        }


class RegistryStub(StubPreview):
    event = STUB_EVENT


class GetPreviewTests(TestCase):
    def setUp(self):
        register(RegistryStub)
        self.addCleanup(PREVIEWS.pop, STUB_EVENT, None)

    def test_resolves_the_registered_preview(self):
        self.assertIsInstance(get_preview(STUB_EVENT), RegistryStub)

    def test_returns_a_fresh_instance_each_call(self):
        self.assertIsNot(get_preview(STUB_EVENT), get_preview(STUB_EVENT))

    def test_register_returns_the_class_untouched(self):
        self.assertIs(register(RegistryStub), RegistryStub)

    def test_a_preview_without_an_event_is_rejected(self):
        class Eventless(RegistryStub):
            event = None

        with self.assertRaises(ValueError):
            register(Eventless)

    def test_every_registry_key_matches_its_preview_event(self):
        for event in PREVIEWS:
            self.assertEqual(get_preview(event).event, event)

    def test_raises_when_no_preview_is_registered(self):
        with self.assertRaises(MissingPreview):
            get_preview('nope')

    def test_error_names_the_event_and_the_alternatives(self):
        with self.assertRaises(MissingPreview) as caught:
            get_preview('nope')

        message = str(caught.exception)
        self.assertIn('nope', message)
        self.assertIn(STUB_EVENT, message)


class PreviewRenderTests(TestCase):
    def test_renders_subject_body_and_html_from_seeded_rows(self):
        preview = StubPreview()

        subject, body, html = preview.render()

        self.assertIn('WupNext', subject)
        self.assertIn(preview.user.username, body)
        self.assertIn('<!doctype html>', html)

    def test_sends_nothing_and_leaves_no_rows(self):
        StubPreview().render()

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_rolls_back_when_rendering_raises(self):
        class Exploding(StubPreview):
            def _get_notification_context(self):
                raise RuntimeError('boom')

        with self.assertRaises(RuntimeError):
            Exploding().render()

        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_cannot_instantiate_a_preview_without_its_hooks(self):
        class Hookless(BaseEmailPreview):
            pass

        with self.assertRaises(TypeError):
            Hookless()


class PreviewSendTests(TestCase):
    def setUp(self):
        patcher = patch(
            'notifications.email_previews.base.get_connection',
            return_value=mail.get_connection(LOCMEM),
        )
        self.get_connection = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delivers_through_the_live_backend(self):
        StubPreview().send_preview('me@example.com')

        self.get_connection.assert_called_once_with(settings.LIVE_EMAIL_BACKEND)
        self.assertEqual(mail.outbox[0].to, ['me@example.com'])

    def test_returns_what_it_rendered(self):
        subject, body, html = StubPreview().send_preview('me@example.com')

        message = mail.outbox[0]
        self.assertEqual(message.subject, subject)
        self.assertEqual(message.body, body)
        self.assertEqual(message.alternatives[0][0], html)

    def test_leaves_no_rows_behind(self):
        StubPreview().send_preview('me@example.com')

        self.assertEqual(NotificationLog.objects.count(), 0)
