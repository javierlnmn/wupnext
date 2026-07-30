from django import forms

from .models import (
    Channel,
    NotificationChannelSwitch,
    NotificationEventSwitch,
    NotificationUserPreference,
)
from .registry import NOTIFICATIONS

FIELD_PREFIX = 'notify'


class NotificationPreferencesForm(forms.Form):
    """A checkbox per event and channel the site currently has switched on.

    Renders through ``channels`` (the columns) and ``rows`` (one per event),
    and saves an explicit preference for every cell the user was shown.
    """

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.cells = {}
        self.channels = self._get_channels()
        self.rows = self._get_rows()

    def _get_channels(self):
        """
        Columns: the channels switched on site-wide.
        Returns:
            [ { key, label } ]
        """
        enabled = NotificationChannelSwitch.objects.filter(
            enabled=True, channel__in=Channel.values
        ).values_list('channel', flat=True)

        return [{'key': key, 'label': Channel(key).label} for key in enabled]

    def _get_site_defaults(self, channel_keys):
        """
        Cells the site allows, for every registered event.
        Returns:
            { ( event, channel ): on_by_default }
        """
        return {
            (event, channel): on_by_default
            for event, channel, on_by_default in NotificationEventSwitch.objects.filter(
                enabled=True, event__in=NOTIFICATIONS, channel__in=channel_keys
            ).values_list('event', 'channel', 'on_by_default')
        }

    def _get_stored_preferences(self, channel_keys):
        """
        What this user already chose, across every event.
        Returns:
            { ( event, channel ): enabled }
        """
        return {
            (event, channel): enabled
            for event, channel, enabled in NotificationUserPreference.objects.filter(
                user=self.user, event__in=NOTIFICATIONS, channel__in=channel_keys
            ).values_list('event', 'channel', 'enabled')
        }

    def _get_rows(self):
        """
        One row per event that has at least one cell the site allows.
        Returns:
            [ { label, description, cells: [ { available, name, enabled } ] } ]
        """
        channel_keys = [channel['key'] for channel in self.channels]
        site_defaults = self._get_site_defaults(channel_keys)
        stored = self._get_stored_preferences(channel_keys)
        rows = []

        for event, notification in NOTIFICATIONS.items():
            cells = [
                self._build_cell(event, key, site_defaults, stored)
                for key in channel_keys
            ]

            if any(cell['available'] for cell in cells):
                rows.append(
                    {
                        'label': notification.label or event,
                        'description': notification.description,
                        'cells': cells,
                    }
                )

        return rows

    def _build_cell(self, event, channel, site_defaults, stored):
        """
        One cell, adding a form field when the site allows this pair.
        Returns:
            { available, name, enabled }
        """
        pair = (event, channel)

        if pair not in site_defaults:
            return {'available': False}

        name = f'{FIELD_PREFIX}-{event}-{channel}'
        self.cells[name] = pair
        self.fields[name] = forms.BooleanField(required=False)

        return {
            'available': True,
            'name': name,
            'enabled': stored.get(pair, site_defaults[pair]),
        }

    def save(self):
        for name, (event, channel) in self.cells.items():
            NotificationUserPreference.objects.update_or_create(
                user=self.user,
                event=event,
                channel=channel,
                defaults={'enabled': self.cleaned_data[name]},
            )
