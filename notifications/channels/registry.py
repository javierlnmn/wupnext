from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from ..exceptions import UnknownChannel
from .base import BaseNotificationChannel


def get_channels():
    channels = {}

    for found in iter_modules([str(Path(__file__).parent)]):
        module = import_module(f'.{found.name}', package=__package__)

        for member in vars(module).values():
            if (
                isinstance(member, type)
                and issubclass(member, BaseNotificationChannel)
                and member.key
            ):
                channels[member.key] = member()

    return channels


CHANNELS = get_channels()


def get_channel(key):
    channel = CHANNELS.get(key)

    if channel is None:
        raise UnknownChannel(
            f"No channel registered for '{key}'. "
            f'Available: {", ".join(sorted(CHANNELS)) or "none"}.'
        )

    return channel
