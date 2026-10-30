"""A serializer field for a partial date, for Django REST framework."""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from partial_dates.partial_date import PartialDate


class PartialDateField(serializers.Field):
    """A serializer field whose value is a `PartialDate`, written as its ISO form.

    Options such as `required`, `read_only`, `source`, `allow_null` and `validators`
    behave as they do on any Django REST framework field.

    Attributes:
        default_error_messages: The `invalid` message.
    """

    default_error_messages = {
        "invalid": _("Enter a date as YYYY, YYYY-MM or YYYY-MM-DD."),
    }

    def to_representation(self, value: PartialDate | str) -> str:
        """Write a partial date as its ISO form.

        Args:
            value: A `PartialDate`, or the ISO text an instance holds before it is
                read back from the database.

        Returns:
            The ISO form: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.
        """
        if isinstance(value, PartialDate):
            return value.isoformat()
        return PartialDate.fromisoformat(value).isoformat()
