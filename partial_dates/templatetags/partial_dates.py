"""The template filter that shows a partial date to a reader."""

from django import template

from partial_dates.partial_date import PartialDate

register = template.Library()


@register.filter
def partial_date(value: object) -> str:
    """Show a partial date as the active language writes it.

    Args:
        value: The value to show.

    Returns:
        The display form of a partial date, or empty text for anything else. The text
        is not marked safe, so the template layer escapes it.
    """
    return value.display_form() if isinstance(value, PartialDate) else ""
