from django.contrib.auth import get_user_model

from accounts.notifications.notifications.password_reset import (
    PasswordResetNotification,
)
from notifications.email_previews import (
    PREVIEW_EMAIL,
    PREVIEW_USERNAME,
    BaseEmailPreview,
    register,
)


@register
class AccountPasswordResetPreview(BaseEmailPreview):
    event = PasswordResetNotification.event
    user = None

    def _seed(self):
        self.user = get_user_model()(
            username=PREVIEW_USERNAME,
            email=PREVIEW_EMAIL,
        )
        self.user.set_password('preview-only')
        self.user.save()

    def _get_notification_context(self):
        return {**PasswordResetNotification().context(self.user), 'user': self.user}
