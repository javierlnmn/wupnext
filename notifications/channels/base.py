from common.models import SiteSettings


class BaseChannel:
    key = None

    def is_enabled(self):
        return self.key not in SiteSettings.load().notifications_disabled_channels

    def deliver(self, *, user, event, context):
        raise NotImplementedError
