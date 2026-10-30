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


class PartialDateRangeWidget(forms.MultiWidget):
    """Two filter widgets, named `<name>_after` and `<name>_before`.

    Args:
        attrs: HTML attributes for the widget, as for any Django widget.
        years: The years the selects offer, as for `PartialDateWidget`.
    """

    def __init__(
        self, attrs: dict[str, Any] | None = None, years: Iterable[int] | None = None
    ) -> None:
        widgets: dict[str, forms.Widget | type[forms.Widget]] = {
            "after": PartialDateFilterWidget(years=years),
            "before": PartialDateFilterWidget(years=years),
        }
        super().__init__(widgets, attrs)

    def decompress(self, value: Any) -> list[Any]:
        """Split a range into its two bounds.

        Args:
            value: A `slice` of the two bounds, or `None`.

        Returns:
            The first and last bound, or two `None`s when there is no range.
        """
        if isinstance(value, slice):
            return [value.start, value.stop]
        return [None, None]


class PartialDateRangeField(forms.MultiValueField):
    """A form field of two optional partial dates, giving a `slice` of them.

    Args:
        years: The years the selects of both bounds offer.
        **kwargs: Keyword arguments of `django.forms.Field`.
    """

    def __init__(self, *, years: Iterable[int] | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("widget", PartialDateRangeWidget(years=years))
        fields = (
            PartialDateFilterField(required=False, years=years),
            PartialDateFilterField(required=False, years=years),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list: list[PartialDate | None]) -> slice | None:
        """Join the two bounds, in the shape `django_filters.RangeFilter` takes.

        Args:
            data_list: The first and last bound, or an empty list for no entry.

        Returns:
            `None` when neither bound was entered, otherwise a `slice` of them.
        """
        if not data_list or data_list == [None, None]:
            return None
        return slice(*data_list)


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
        name, separator, comparison = self.lookup_expr.partition(LOOKUP_SEP)
        if name in PARTS and (not separator or comparison in COMPARISONS):
            self.field_class = forms.IntegerField
        elif self.lookup_expr not in COMPARISONS:
            raise ImproperlyConfigured(
                f"PartialDateFilter does not support the lookup "
                f"{self.lookup_expr!r}. Use one of {', '.join(COMPARISONS)}, or a "
                f"part ({', '.join(PARTS)}) alone or followed by one of them."
            )


class PartialDateRangeFilter(django_filters.RangeFilter):
    """Filter a partial date column by two optional bounds.

    The query parameters are `<name>_after` and `<name>_before`. A row is found when it
    sorts at or after the first bound and at or before the last day of the period of
    the second. The keyword arguments are those of `django_filters.Filter`, and
    `years` is passed to the form field.

    Attributes:
        field_class: The form field that validates the bounds.
    """

    field_class = PartialDateRangeField

    def filter(self, qs: Any, value: slice | None) -> Any:
        """Take in the whole of the period the second bound names, then filter.

        Args:
            qs: The queryset to filter.
            value: The `slice` of bounds the form field gives, or `None`.

        Returns:
            The queryset narrowed by the bounds entered.
        """
        if value is not None and value.stop is not None:
            last = value.stop.end
            value = slice(value.start, PartialDate(last.year, last.month, last.day))
        return super().filter(qs, value)
