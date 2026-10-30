"""A serializer field for a partial date, for Django REST framework."""

from typing import Any

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

    def to_representation(self, value: PartialDate | str) -> str | None:
        """Write a partial date as its ISO form.

        Args:
            value: A `PartialDate`, or the text an instance holds before it is read
                back from the database, where `""` stands for no date, as it does on
                the model field.

        Returns:
            The ISO form, `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, or `None` for `""`.
        """
        if value == "":
            return None
        if isinstance(value, PartialDate):
            return value.isoformat()
        return PartialDate.fromisoformat(value).isoformat()

    def to_internal_value(self, data: Any) -> PartialDate:
        """Read a partial date from incoming data.

        Args:
            data: A `PartialDate`, or text in the ISO form.

        Returns:
            The partial date the data names.

        Raises:
            serializers.ValidationError: With code `invalid` for anything else,
                including an empty string.
        """
        if isinstance(data, PartialDate):
            return data
        try:
            return PartialDate.fromisoformat(data)
        except ValueError:
            raise serializers.ValidationError(
                self.error_messages["invalid"], code="invalid"
            ) from None
