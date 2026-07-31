from ..exceptions import MissingPreview

PREVIEWS = {}


def register(preview_class):
    event = preview_class.event

    if not event:
        raise ValueError(f'{preview_class.__name__} declares no event.')

    PREVIEWS[event] = preview_class
    return preview_class


def get_preview(event):
    preview_class = PREVIEWS.get(event)

    if preview_class is None:
        raise MissingPreview(
            f"No preview registered for '{event}'. "
            f'Available: {", ".join(sorted(PREVIEWS)) or "none"}.'
        )

    return preview_class()
