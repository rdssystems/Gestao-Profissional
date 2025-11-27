from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown as markdown_lib

register = template.Library()

@register.filter
@stringfilter
def markdown(value):
    return mark_safe(markdown_lib.markdown(value, extensions=['fenced_code']))