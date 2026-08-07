from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.template import TemplateDoesNotExist

from notifications.channels.email import has_resend_api_key
from notifications.email_previews import PREVIEWS, get_preview
from notifications.exceptions import MissingPreview


class Command(BaseCommand):
    help = 'Render a notification email from its template folder, for previewing.'

    def add_arguments(self, parser):
        parser.add_argument(
            'event',
            nargs='?',
            help='Template folder name, e.g. task_due_reminder.',
        )
        parser.add_argument(
            '--send',
            metavar='EMAIL',
            help='Also deliver the rendered email to this address.',
        )

    def handle(self, *args, **options):
        event = options['event']
        recipient = options['send']

        if not event:
            self.stdout.write(self.style.MIGRATE_HEADING('Available emails'))
            for name in sorted(PREVIEWS):
                self.stdout.write(f'  {name}')
            return

        if recipient:
            try:
                validate_email(recipient)
            except ValidationError as exc:
                raise CommandError(
                    f"'{recipient}' is not a valid email address."
                ) from exc

            if not has_resend_api_key():
                raise CommandError(
                    'RESEND_API_KEY is not set, and previews always send through '
                    f'{settings.LIVE_EMAIL_BACKEND}. Drop --send to only render.'
                )

        try:
            preview = get_preview(event)
        except MissingPreview as exc:
            raise CommandError(str(exc)) from exc

        try:
            if recipient:
                subject, body, html = preview.send_preview(recipient)
            else:
                subject, body, html = preview.render()
        except TemplateDoesNotExist as exc:
            raise CommandError(f"Missing template '{exc}' for '{event}'.") from exc

        self.stdout.write(self.style.MIGRATE_HEADING('Subject'))
        self.stdout.write(f'{subject}\n')
        self.stdout.write(self.style.MIGRATE_HEADING('Plain text'))
        self.stdout.write(body)

        if html:
            self.stdout.write(self.style.MIGRATE_HEADING('HTML'))
            self.stdout.write(html)
        else:
            self.stdout.write(self.style.WARNING('No HTML template for this event.'))

        if recipient:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sent to {recipient} using {settings.LIVE_EMAIL_BACKEND}'
                )
            )
