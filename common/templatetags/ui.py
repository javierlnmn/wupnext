from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.simple_block_tag
def modal(content, openStateKey, width="24rem"):
    return render_to_string(
        "common/modal_shell.html",
        {"content": content, "openStateKey": openStateKey, "width": width},
    )


@register.simple_block_tag
def drawer(content, openStateKey, width="24rem"):
    return render_to_string(
        "common/drawer_shell.html",
        {"content": content, "openStateKey": openStateKey, "width": width},
    )
