from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import UserFactory
from notifications.email_previews import (
    PREVIEW_USERNAME,
    PREVIEWS,
    BaseEmailPreview,
    get_preview,
)
from notifications.email_previews.task_due_reminder_preview import (
    TaskDueReminderPreview,
)
from notifications.exceptions import MissingPreview
from notifications.models import NotificationLog
from notifications.tests.factories import NotificationLogFactory
from tasks.models import Group, Task
from tasks.tests.factories import TaskFactory

EVENT = 'task_due_reminder'
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


class GetPreviewTests(TestCase):
    def test_resolves_the_registered_preview(self):
        self.assertIsInstance(get_preview(EVENT), TaskDueReminderPreview)

    def test_returns_a_fresh_instance_each_call(self):
        self.assertIsNot(get_preview(EVENT), get_preview(EVENT))

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
        self.assertIn(EVENT, message)


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
        StubPreview().send('me@example.com')

        self.get_connection.assert_called_once_with(settings.LIVE_EMAIL_BACKEND)
        self.assertEqual(mail.outbox[0].to, ['me@example.com'])

    def test_returns_what_it_rendered(self):
        subject, body, html = StubPreview().send('me@example.com')

        message = mail.outbox[0]
        self.assertEqual(message.subject, subject)
        self.assertEqual(message.body, body)
        self.assertEqual(message.alternatives[0][0], html)

    def test_leaves_no_rows_behind(self):
        StubPreview().send('me@example.com')

        self.assertEqual(NotificationLog.objects.count(), 0)


class TaskDueReminderPreviewTests(TestCase):
    def test_renders_the_seeded_overdue_and_due_today_sections(self):
        _, body, _ = TaskDueReminderPreview().render()

        self.assertIn(f'Hi {PREVIEW_USERNAME}', body)
        self.assertIn('OVERDUE (1)', body)
        self.assertIn('DUE TODAY (1)', body)

    def test_renders_subtask_progress_from_saved_rows(self):
        _, body, _ = TaskDueReminderPreview().render()

        self.assertIn('1/2 subtasks done', body)

    def test_ignores_existing_users_and_their_tasks(self):
        today = timezone.localdate()
        existing = UserFactory(email='existing@example.com')
        TaskFactory(
            user=existing, name='Real overdue', due_date=today - timedelta(days=1)
        )
        TaskFactory(user=existing, name='Real due today', due_date=today)

        _, body, _ = TaskDueReminderPreview().render()

        self.assertNotIn('Real overdue', body)
        self.assertNotIn('Real due today', body)

    def test_rolls_back_the_seeded_rows(self):
        TaskDueReminderPreview().render()

        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)
