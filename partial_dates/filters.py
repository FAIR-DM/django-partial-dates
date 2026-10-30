"""Filters for a partial date column, for a django-filter `FilterSet`."""

from collections.abc import Iterable, Mapping
from typing import Any, cast

import django_filters
from django import forms
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models.constants import LOOKUP_SEP

from partial_dates.forms import PartialDateField, PartialDateWidget
from partial_dates.partial_date import PartialDate

COMPARISONS = ("exact", "gt", "gte", "lt", "lte")
PARTS = ("year", "month", "day")


class PartialDateFilterWidget(PartialDateWidget):
    """The three selects of a form, with the ISO form read from the filter's own name.

    A query string holding `?collected=1990-06` has no selects to fill in, so the text
    under the name itself is read first.
    """

    def value_from_datadict(
        self, data: Mapping[str, Any], files: Any, name: str
    ) -> Any:
        """Read the ISO text under the name, or else the three selects.

        Args:
            data: The query string or form data.
            files: The uploaded files, which a filter does not use.
            name: The name of the filter.

        Returns:
            The text under `name` when it is not empty, otherwise the year, month and
            day entered in the selects.
        """
        text = data.get(name)
        if text:
            return text
        return super().value_from_datadict(data, files, name)


class PartialDateFilterField(PartialDateField):
    """A form field that also reads the ISO form of a partial date.

    Args:
        years: The years the selects offer, as for `PartialDateWidget`.
        **kwargs: Keyword arguments of `partial_dates.forms.PartialDateField`.
    """

    def __init__(self, *, years: Iterable[int] | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("widget", PartialDateFilterWidget(years=years))
        super().__init__(**kwargs)

    def clean(self, value: Any) -> PartialDate | None:
        """Turn ISO text into a partial date, and leave the selects to the parent.

        Args:
            value: ISO text, or the year, month and day entered in the selects.

        Returns:
            The partial date entered, or `None` for no entry.

        Raises:
            ValidationError: With code `invalid` for text that is not a partial date,
                and with the codes of the parent for the selects.
        """
        if isinstance(value, str):
            try:
                return PartialDate.fromisoformat(value)
            except ValueError:
                raise ValidationError(
                    self.error_messages["invalid"], code="invalid"
                ) from None
        return cast(PartialDate | None, super().clean(value))


class PartialDateFilter(django_filters.Filter):
    """Filter a partial date column by a lookup, validating the entry as a date.

    The lookups are `exact`, `gt`, `gte`, `lt` and `lte`, which take a partial date,
    and `year`, `month` and `day`, alone or followed by one of those five, which take
    a whole number. The keyword arguments are those of `django_filters.Filter`, and
    `years` is passed to the form field.

    Args:
        *args: Positional arguments of `django_filters.Filter`.
        **kwargs: Keyword arguments of `django_filters.Filter`.

    Attributes:
        field_class: The form field that validates the entry.

    Raises:
        ImproperlyConfigured: For a lookup outside the lists above.
    """

    field_class: type[forms.Field] = PartialDateFilterField

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        name, _separator, comparison = self.lookup_expr.partition(LOOKUP_SEP)
        if name in PARTS and comparison in ("", *COMPARISONS):
            self.field_class = forms.IntegerField
        elif self.lookup_expr not in COMPARISONS:
            raise ImproperlyConfigured(
                f"PartialDateFilter does not support the lookup "
                f"{self.lookup_expr!r}. Use one of {', '.join(COMPARISONS)}, or a "
                f"part ({', '.join(PARTS)}) alone or followed by one of them."
            )
