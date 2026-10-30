"""The form field and widget a user fills in to enter a partial date."""

import datetime
from collections.abc import Iterable
from typing import Any, cast

from django import forms
from django.core.exceptions import ValidationError
from django.utils.dates import MONTHS
from django.utils.translation import gettext_lazy as _

from partial_dates.partial_date import PartialDate

FIRST_YEAR = 1900
LAST_YEAR = 9999


class PartialDateWidget(forms.MultiWidget):
    """Three selects, for the year, the month and the day, in that order.

    Every select offers an empty choice. The year being shown is always among the
    years offered, so a stored year outside the list survives an edit.

    Args:
        attrs: HTML attributes for the widget, as for any Django widget.
        years: The years to offer, in the order to show them. With none, the widget
            offers the years from the current year down to 1900, worked out each
            time the widget is rendered.
    """

    def __init__(
        self, attrs: dict[str, Any] | None = None, years: Iterable[int] | None = None
    ) -> None:
        self.years = None if years is None else tuple(years)
        widgets: dict[str, forms.Widget | type[forms.Widget]] = {
            "year": forms.Select(
                attrs={"aria-label": _("Year")}, choices=[("", _("Year"))]
            ),
            "month": forms.Select(
                attrs={"aria-label": _("Month")},
                choices=[("", _("Month")), *MONTHS.items()],
            ),
            "day": forms.Select(
                attrs={"aria-label": _("Day")},
                choices=[("", _("Day")), *((day, day) for day in range(1, 32))],
            ),
        }
        super().__init__(widgets, attrs)

    def decompress(self, value: Any) -> list[int | None]:
        """Split a value into its year, month and day.

        Args:
            value: A `PartialDate`, its ISO text, `""` or `None`.

        Returns:
            The year, month and day, with `None` for a part that is not recorded.
            Text that is not an ISO form gives three `None`s.
        """
        if isinstance(value, str) and value:
            try:
                value = PartialDate.fromisoformat(value)
            except ValueError:
                return [None, None, None]
        if isinstance(value, PartialDate):
            return [value.year, value.month, value.day]
        return [None, None, None]

    def get_context(
        self, name: str, value: Any, attrs: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Offer the years, and the year being shown when it is not among them.

        Args:
            name: The name of the field.
            value: The value being shown, or the parts a refused entry holds.
            attrs: HTML attributes for the rendered widget.

        Returns:
            The context to render the three selects with.
        """
        parts = value if isinstance(value, list | tuple) else self.decompress(value)
        years = self.years
        if years is None:
            years = tuple(range(datetime.date.today().year, FIRST_YEAR - 1, -1))
        try:
            shown = int(cast(Any, parts[0]))
        except (TypeError, ValueError, IndexError):
            shown = None
        if shown is not None and 1 <= shown <= LAST_YEAR and shown not in years:
            years = (*years, shown)
        cast(forms.Select, self.widgets[0]).choices = [
            ("", _("Year")),
            *((year, year) for year in years),
        ]
        return super().get_context(name, value, attrs)


class PartialDateField(forms.MultiValueField):
    """A form field whose value is a `PartialDate`, or `None` for no date.

    Required means a year was given. The month and day may always be left empty.

    Args:
        **kwargs: Keyword arguments of `django.forms.Field`.

    Attributes:
        widget: The widget the field renders with.
        default_error_messages: The `incomplete` and `invalid` messages.
    """

    widget = PartialDateWidget
    default_error_messages = {
        "incomplete": _("Enter a year, and a month as well when you enter a day."),
        "invalid": _("Enter a date that exists."),
    }

    def __init__(self, **kwargs: Any) -> None:
        fields = (
            forms.IntegerField(required=False),
            forms.IntegerField(required=False),
            forms.IntegerField(required=False),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: list[int | None]) -> PartialDate | None:
        """Join the year, month and day into a partial date.

        Args:
            data_list: The year, month and day, or an empty list for no entry.

        Returns:
            `None` for no entry, otherwise the partial date at the precision entered.

        Raises:
            ValidationError: With code `incomplete` for a part without the part it
                depends on, and with code `invalid` for a date that does not exist.
        """
        if not data_list:
            return None
        year, month, day = data_list
        if year is None or (month is None and day is not None):
            raise ValidationError(self.error_messages["incomplete"], code="incomplete")
        try:
            return PartialDate(year, month, day)
        except ValueError:
            raise ValidationError(
                self.error_messages["invalid"], code="invalid"
            ) from None
