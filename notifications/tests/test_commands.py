from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.management import CommandError, call_command
from django.test import TestCase

from notifications.management.commands.preview_email import LIVE_EMAIL_BACKEND
from notifications.models import NotificationLog
from tasks.models import Group, Task

EVENT = "task_due_reminder"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


class PreviewCommandTestCase(TestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command("preview_email", *args, stdout=out)
        return out.getvalue()


class PreviewEmailTests(PreviewCommandTestCase):
    def test_lists_available_emails_without_an_event(self):
        output = self.run_command()

        self.assertIn(EVENT, output)

    def test_unknown_event_raises(self):
        with self.assertRaises(CommandError):
            self.run_command("nope")

    def test_prints_subject_plain_text_and_html(self):
        output = self.run_command(EVENT)

        self.assertIn("WupNext", output)
        self.assertIn("OVERDUE (1)", output)
        self.assertIn("DUE TODAY (1)", output)
        self.assertIn("<!doctype html>", output)

    def test_sends_no_email(self):
        self.run_command(EVENT)

        self.assertEqual(len(mail.outbox), 0)

    def test_leaves_no_trace_in_the_database(self):
        self.run_command(EVENT)

        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)


class PreviewEmailSendTests(PreviewCommandTestCase):
    def setUp(self):
        patcher = patch(
            "notifications.management.commands.preview_email.get_connection",
            return_value=mail.get_connection(LOCMEM),
        )
        self.get_connection = patcher.start()
        self.addCleanup(patcher.stop)

    def test_uses_the_live_backend_not_the_configured_one(self):
        self.run_command(EVENT, "--send", "me@example.com")

        self.get_connection.assert_called_once_with(LIVE_EMAIL_BACKEND)

    def test_delivers_to_the_given_address(self):
        output = self.run_command(EVENT, "--send", "me@example.com")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["me@example.com"])
        self.assertIn("WupNext", message.subject)
        self.assertIn("me@example.com", output)

    def test_attaches_the_html_alternative(self):
        self.run_command(EVENT, "--send", "me@example.com")

        message = mail.outbox[0]
        self.assertIn("OVERDUE (1)", message.body)
        content, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn("<!doctype html>", content)

    def test_writes_no_notification_log(self):
        self.run_command(EVENT, "--send", "me@example.com")

        self.assertEqual(NotificationLog.objects.count(), 0)

    def test_rejects_an_invalid_address(self):
        with self.assertRaises(CommandError):
            self.run_command(EVENT, "--send", "not-an-email")

        self.assertEqual(len(mail.outbox), 0)
        self.get_connection.assert_not_called()
