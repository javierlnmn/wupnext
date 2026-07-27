from django.core.exceptions import ValidationError
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.template import TemplateDoesNotExist

from notifications.channels.email import EmailChannel
from notifications.exceptions import MissingPreview
from notifications.previews import PREVIEWS, preview_context

LIVE_EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"


class Command(BaseCommand):
    help = "Render a notification email from its template folder, for previewing."

    def add_arguments(self, parser):
        parser.add_argument(
            "event",
            nargs="?",
            help="Template folder name, e.g. task_due_reminder.",
        )
        parser.add_argument(
            "--send",
            metavar="EMAIL",
            help="Also deliver the rendered email to this address.",
        )

    def handle(self, *args, **options):
        event = options["event"]
        recipient = options["send"]

        if not event:
            self.stdout.write(self.style.MIGRATE_HEADING("Available emails"))
            for name in sorted(PREVIEWS):
                self.stdout.write(f"  {name}")
            return

        if recipient:
            try:
                validate_email(recipient)
            except ValidationError as exc:
                raise CommandError(
                    f"'{recipient}' is not a valid email address."
                ) from exc

        channel = EmailChannel()

        try:
            with preview_context(event) as context:
                subject, body, html = channel.render(event, context)
        except MissingPreview as exc:
            raise CommandError(str(exc)) from exc
        except TemplateDoesNotExist as exc:
            raise CommandError(f"Missing template '{exc}' for '{event}'.") from exc

        self.stdout.write(self.style.MIGRATE_HEADING("Subject"))
        self.stdout.write(f"{subject}\n")
        self.stdout.write(self.style.MIGRATE_HEADING("Plain text"))
        self.stdout.write(body)

        if html:
            self.stdout.write(self.style.MIGRATE_HEADING("HTML"))
            self.stdout.write(html)
        else:
            self.stdout.write(self.style.WARNING("No HTML template for this event."))

        if recipient:
            message = channel.build_message(subject, body, html, [recipient])
            message.connection = get_connection(LIVE_EMAIL_BACKEND)
            message.send()
            self.stdout.write(
                self.style.SUCCESS(f"Sent to {recipient} using {LIVE_EMAIL_BACKEND}")
            )
