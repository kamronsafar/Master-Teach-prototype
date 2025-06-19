from django import template

register = template.Library()

@register.filter
def get_range(value):
    """
    Filter - returns a list containing range made from given value
    Usage (in template):
    <ul>{% for i in total_pages|get_range %}
      <li>{{ i }}</li>
    {% endfor %}</ul>
    """
    return range(1, int(value) + 1) 