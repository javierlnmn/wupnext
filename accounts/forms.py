import logging

from django.contrib.auth.forms import PasswordResetForm

from notifications.service import NotificationService

from .notifications.notifications.password_reset import PasswordResetNotification

logger = logging.getLogger(__name__)


class PasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        user = context['user']

        try:
            NotificationService(PasswordResetNotification()).send(user)
        except Exception:
            logger.exception('Failed to send password reset email to %s', user.pk)
