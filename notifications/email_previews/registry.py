from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from ..exceptions import MissingPreview
from .base import BaseEmailPreview


def get_previews():
    previews = {}

    for found in iter_modules([str(Path(__file__).parent)]):
        if not found.name.endswith('_preview'):
            continue

        module = import_module(f'.{found.name}', package=__package__)

        for member in vars(module).values():
            if (
                isinstance(member, type)
                and issubclass(member, BaseEmailPreview)
                and member.event
            ):
                previews[member.event] = member

    return previews


PREVIEWS = get_previews()


def get_preview(event):
    preview_class = PREVIEWS.get(event)

    if preview_class is None:
        raise MissingPreview(
            f"No preview registered for '{event}'. "
            f'Available: {", ".join(sorted(PREVIEWS)) or "none"}.'
        )

    return preview_class()
