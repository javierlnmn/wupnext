from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.tag("modal")
def do_modal(parser, token):
    kwargs = {}
    for bit in token.split_contents()[1:]:
        if "=" not in bit:
            raise template.TemplateSyntaxError("modal arguments must be key=value")
        name, value = bit.split("=", 1)
        kwargs[name] = parser.compile_filter(value)
    nodelist = parser.parse(("endmodal",))
    parser.delete_first_token()
    return ModalNode(nodelist, kwargs)


class ModalNode(template.Node):
    def __init__(self, nodelist, kwargs):
        self.nodelist = nodelist
        self.kwargs = kwargs

    def render(self, context):
        values = {name: expr.resolve(context) for name, expr in self.kwargs.items()}
        return render_to_string(
            "common/modal_shell.html",
            {
                "content": mark_safe(self.nodelist.render(context)),
                "openStateKey": values["openStateKey"],
                "width": values.get("width", "max-w-sm"),
            },
        )
